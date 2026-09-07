#include "encoder.h"
#include "config.h"
#include "driver/pulse_cnt.h"

static pcnt_unit_handle_t s_unit;

void encoder_init(void)
{
    pcnt_unit_config_t ucfg = {
        .high_limit = 1000,
        .low_limit = -1000,
    };
    pcnt_new_unit(&ucfg, &s_unit);

    pcnt_glitch_filter_config_t gf = {
        .max_glitch_ns = 1000,
    };
    pcnt_unit_set_glitch_filter(s_unit, &gf);

    pcnt_chan_config_t ccfg = {
        .edge_gpio_num = ENC_PIN_A,
        .level_gpio_num = ENC_PIN_B,
    };
    pcnt_channel_handle_t ch;
    pcnt_new_channel(s_unit, &ccfg, &ch);
    pcnt_channel_set_edge_action(ch, PCNT_CHANNEL_EDGE_ACTION_DECREASE,
                                 PCNT_CHANNEL_EDGE_ACTION_INCREASE);
    pcnt_channel_set_level_action(ch, PCNT_CHANNEL_LEVEL_ACTION_KEEP,
                                  PCNT_CHANNEL_LEVEL_ACTION_INVERSE);

    pcnt_unit_enable(s_unit);
    pcnt_unit_clear_count(s_unit);
    pcnt_unit_start(s_unit);
}

int encoder_read_and_clear(void)
{
    int c = 0;
    pcnt_unit_get_count(s_unit, &c);
    pcnt_unit_clear_count(s_unit);
    return c;
}
