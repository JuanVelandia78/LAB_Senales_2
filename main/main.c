#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_attr.h"
#include "driver/gptimer.h"
#include "driver/gpio.h"
#include "config.h"
#include "filtros_conv.h"
#include "imu.h"
#include "encoder.h"

#define FS_HZ    200
#define TS_US    (1000000 / FS_HZ)
#define PIN_TICK GPIO_NUM_23
#define PIN_CALC GPIO_NUM_4
#define NCH      7

static TaskHandle_t s_task;
static volatile uint32_t s_t_isr;
static volatile uint32_t s_overruns;
static volatile bool s_pending;

#if FILTER == FILT_CONV && CONV_TYPE == CONV_FIR
static float st_z[NCH][FILT_NTAPS];
static int st_head[NCH];

static float filtro(int c, float x)
{
    st_z[c][st_head[c]] = x;
    float acc = 0.0f;
    int k = st_head[c];
    for (int i = 0; i < FILT_NTAPS; i++) {
        acc += FILT_B[i] * st_z[c][k];
        k = k ? (k - 1) : (FILT_NTAPS - 1);
    }
    st_head[c] = (st_head[c] + 1) % FILT_NTAPS;
    return acc;
}
#elif FILTER == FILT_CONV
static float st_w1[NCH][FILT_NSOS];
static float st_w2[NCH][FILT_NSOS];

static float filtro(int c, float x)
{
    float y = x;
    for (int s = 0; s < FILT_NSOS; s++) {
        float w0 = y - FILT_SOS[s][4] * st_w1[c][s] - FILT_SOS[s][5] * st_w2[c][s];
        y = FILT_SOS[s][0] * w0 + FILT_SOS[s][1] * st_w1[c][s] + FILT_SOS[s][2] * st_w2[c][s];
        st_w2[c][s] = st_w1[c][s];
        st_w1[c][s] = w0;
    }
    return y;
}
#elif FILTER == FILT_MA
static float st_buf[NCH][MA_WINDOW];
static int st_head[NCH];
static float st_acc[NCH];

static float filtro(int c, float x)
{
    st_acc[c] += x - st_buf[c][st_head[c]];
    st_buf[c][st_head[c]] = x;
    st_head[c] = (st_head[c] + 1) % MA_WINDOW;
    return st_acc[c] / MA_WINDOW;
}
#elif FILTER == FILT_AR
static float st_y[NCH];
static bool st_init[NCH];

static float filtro(int c, float x)
{
    if (!st_init[c]) {
        st_y[c] = x;
        st_init[c] = true;
    }
    st_y[c] += AR_ALPHA * (x - st_y[c]);
    return st_y[c];
}
#elif FILTER == FILT_LMS
static float st_w[NCH][LMS_TAPS];
static float st_dl[NCH][LMS_TAPS + LMS_DELAY];

static float filtro(int c, float x)
{
    float *dl = st_dl[c];
    for (int i = LMS_TAPS + LMS_DELAY - 1; i > 0; i--) {
        dl[i] = dl[i - 1];
    }
    dl[0] = x;

    float y = 0.0f;
    float p = 1e-6f;
    for (int i = 0; i < LMS_TAPS; i++) {
        float r = dl[i + LMS_DELAY];
        y += st_w[c][i] * r;
        p += r * r;
    }
    float e = x - y;
    float g = LMS_MU / p;
    for (int i = 0; i < LMS_TAPS; i++) {
        st_w[c][i] += g * e * dl[i + LMS_DELAY];
    }
    return y;
}
#else
static float filtro(int c, float x)
{
    (void) c;
    return x;
}
#endif

static bool IRAM_ATTR on_timer(gptimer_handle_t timer,
                               const gptimer_alarm_event_data_t *ed,
                               void *arg)
{
    gpio_set_level(PIN_TICK, 1);
    s_t_isr = (uint32_t) ed->count_value;
    if (s_pending) {
        s_overruns++;
    }
    s_pending = true;

    BaseType_t hp = pdFALSE;
    vTaskNotifyGiveFromISR(s_task, &hp);
    return hp == pdTRUE;
}

static void sampling_task(void *arg)
{
    uint32_t n = 0;
    while (1) {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
        s_pending = false;
        uint32_t t = s_t_isr;

        imu_raw_t m;
        imu_read(&m);
        int encv = encoder_read_and_clear();

        float raw[NCH] = {
            (float) m.ax, (float) m.ay, (float) m.az,
            (float) m.gx, (float) m.gy, (float) m.gz,
            (float) encv,
        };

        gpio_set_level(PIN_CALC, 1);
        int ym[NCH];
        for (int c = 0; c < NCH; c++) {
            ym[c] = (int) lroundf(filtro(c, raw[c]) * 1000.0f);
        }
        gpio_set_level(PIN_CALC, 0);
        gpio_set_level(PIN_TICK, 0);

        printf("%lu,%lu,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%lu\n",
               (unsigned long) n++, (unsigned long) t,
               (int) raw[0], (int) raw[1], (int) raw[2],
               (int) raw[3], (int) raw[4], (int) raw[5], (int) raw[6],
               ym[0], ym[1], ym[2], ym[3], ym[4], ym[5], ym[6],
               (unsigned long) s_overruns);
    }
}

static void init_gpio(void)
{
    gpio_config_t io = {
        .pin_bit_mask = (1ULL << PIN_TICK) | (1ULL << PIN_CALC),
        .mode = GPIO_MODE_OUTPUT,
    };
    gpio_config(&io);
    gpio_set_level(PIN_TICK, 0);
    gpio_set_level(PIN_CALC, 0);
}

static void init_timer(void)
{
    gptimer_handle_t timer = NULL;
    gptimer_config_t cfg = {
        .clk_src = GPTIMER_CLK_SRC_DEFAULT,
        .direction = GPTIMER_COUNT_UP,
        .resolution_hz = 1000000,
    };
    gptimer_new_timer(&cfg, &timer);

    gptimer_event_callbacks_t cbs = {
        .on_alarm = on_timer,
    };
    gptimer_register_event_callbacks(timer, &cbs, NULL);
    gptimer_enable(timer);

    gptimer_alarm_config_t alarm = {
        .alarm_count = TS_US,
        .reload_count = 0,
        .flags.auto_reload_on_alarm = true,
    };
    gptimer_set_alarm_action(timer, &alarm);
    gptimer_start(timer);
}

void app_main(void)
{
    setvbuf(stdout, NULL, _IOLBF, 0);

    init_gpio();
    imu_init();
    encoder_init();
    xTaskCreate(sampling_task, "sampling", 4096, NULL, 10, &s_task);
    init_timer();
}
