#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_attr.h"
#include "driver/gptimer.h"
#include "driver/gpio.h"
#include "driver/ledc.h"
#include "driver/dac_oneshot.h"
#include "esp_adc/adc_oneshot.h"
#include "config.h"
#include "filtros.h"

#define FS_HZ     500
#define TS_US     (1000000 / FS_HZ)
#define PIN_SCOPE GPIO_NUM_13
#define PIN_CALC  GPIO_NUM_4
#define PIN_PWM   GPIO_NUM_27
#define ADC_CHAN  ADC_CHANNEL_6
#define DAC_CHAN  DAC_CHAN_0
#define PWM_FREQ  39000

#if !BYPASS && FILTER_BAND == BAND_BANDPASS
#define OUT_BIAS 2048
#else
#define OUT_BIAS 0
#endif

static TaskHandle_t s_task;
static volatile uint32_t s_t_isr;
static volatile uint32_t s_overruns;
static volatile bool s_pending;
static adc_oneshot_unit_handle_t s_adc;
static dac_oneshot_handle_t s_dac;

#if BYPASS
static float filtro(float x)
{
    return x;
}
#elif FILTER_TYPE == FILTER_FIR
static float s_z[FILT_NTAPS];
static int s_head;

static float filtro(float x)
{
    s_z[s_head] = x;
    float acc = 0.0f;
    int k = s_head;
    for (int i = 0; i < FILT_NTAPS; i++) {
        acc += FILT_B[i] * s_z[k];
        k = k ? (k - 1) : (FILT_NTAPS - 1);
    }
    s_head = (s_head + 1) % FILT_NTAPS;
    return acc;
}
#else
static float s_w1[FILT_NSOS];
static float s_w2[FILT_NSOS];

static float filtro(float x)
{
    float y = x;
    for (int s = 0; s < FILT_NSOS; s++) {
        float w0 = y - FILT_SOS[s][4] * s_w1[s] - FILT_SOS[s][5] * s_w2[s];
        y = FILT_SOS[s][0] * w0 + FILT_SOS[s][1] * s_w1[s] + FILT_SOS[s][2] * s_w2[s];
        s_w2[s] = s_w1[s];
        s_w1[s] = w0;
    }
    return y;
}
#endif

static bool IRAM_ATTR on_timer(gptimer_handle_t timer,
                               const gptimer_alarm_event_data_t *ed,
                               void *arg)
{
    gpio_set_level(PIN_SCOPE, 1);
    s_t_isr = (uint32_t) ed->count_value;
    if (s_pending) {
        s_overruns++;
    }
    s_pending = true;

    BaseType_t hp = pdFALSE;
    vTaskNotifyGiveFromISR(s_task, &hp);
    return hp == pdTRUE;
}

static void reconstruir(int value)
{
    if (value < 0) {
        value = 0;
    }
    if (value > 4095) {
        value = 4095;
    }
    uint8_t out8 = value >> 4;
    dac_oneshot_output_voltage(s_dac, out8);
    ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, out8);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
}

static void sampling_task(void *arg)
{
    uint32_t n = 0;
    while (1) {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
        s_pending = false;

        uint32_t t = s_t_isr;
        int raw = 0;
        adc_oneshot_read(s_adc, ADC_CHAN, &raw);

        gpio_set_level(PIN_CALC, 1);
        float yf = filtro((float) raw);
        gpio_set_level(PIN_CALC, 0);

        int y = (int) (yf + (yf >= 0.0f ? 0.5f : -0.5f)) + OUT_BIAS;
        reconstruir(y);
        gpio_set_level(PIN_SCOPE, 0);

        printf("%lu,%lu,%d,%d,%lu\n",
               (unsigned long) n++, (unsigned long) t, raw, y,
               (unsigned long) s_overruns);
    }
}

static void init_gpio(void)
{
    gpio_config_t io = {
        .pin_bit_mask = (1ULL << PIN_SCOPE) | (1ULL << PIN_CALC),
        .mode = GPIO_MODE_OUTPUT,
    };
    gpio_config(&io);
    gpio_set_level(PIN_SCOPE, 0);
    gpio_set_level(PIN_CALC, 0);
}

static void init_adc(void)
{
    adc_oneshot_unit_init_cfg_t unit = {
        .unit_id = ADC_UNIT_1,
    };
    adc_oneshot_new_unit(&unit, &s_adc);

    adc_oneshot_chan_cfg_t ch = {
        .atten = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    adc_oneshot_config_channel(s_adc, ADC_CHAN, &ch);
}

static void init_salida(void)
{
    dac_oneshot_config_t dcfg = {
        .chan_id = DAC_CHAN,
    };
    dac_oneshot_new_channel(&dcfg, &s_dac);

    ledc_timer_config_t tcfg = {
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .duty_resolution = LEDC_TIMER_8_BIT,
        .timer_num = LEDC_TIMER_0,
        .freq_hz = PWM_FREQ,
        .clk_cfg = LEDC_AUTO_CLK,
    };
    ledc_timer_config(&tcfg);

    ledc_channel_config_t ccfg = {
        .gpio_num = PIN_PWM,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .channel = LEDC_CHANNEL_0,
        .timer_sel = LEDC_TIMER_0,
        .duty = 0,
        .hpoint = 0,
    };
    ledc_channel_config(&ccfg);
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
    init_adc();
    init_salida();
    xTaskCreate(sampling_task, "sampling", 4096, NULL, 10, &s_task);
    init_timer();
}
