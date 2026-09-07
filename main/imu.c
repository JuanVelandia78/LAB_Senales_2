#include "imu.h"
#include "config.h"
#include "driver/i2c_master.h"

#define MPU_ADDR      0x68
#define REG_PWR_MGMT1 0x6B
#define REG_SMPLRT    0x19
#define REG_CONFIG    0x1A
#define REG_GYRO_CFG  0x1B
#define REG_ACCEL_CFG 0x1C
#define REG_ACCEL_X   0x3B

static i2c_master_dev_handle_t s_dev;

static void wr(uint8_t reg, uint8_t val)
{
    uint8_t b[2] = { reg, val };
    i2c_master_transmit(s_dev, b, 2, -1);
}

void imu_init(void)
{
    i2c_master_bus_config_t bus = {
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .i2c_port = I2C_NUM_0,
        .sda_io_num = IMU_SDA,
        .scl_io_num = IMU_SCL,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = true,
    };
    i2c_master_bus_handle_t bh;
    i2c_new_master_bus(&bus, &bh);

    i2c_device_config_t dev = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = MPU_ADDR,
        .scl_speed_hz = 400000,
    };
    i2c_master_bus_add_device(bh, &dev, &s_dev);

    wr(REG_PWR_MGMT1, 0x00);
    wr(REG_SMPLRT, 0x04);
    wr(REG_CONFIG, 0x03);
    wr(REG_GYRO_CFG, 0x00);
    wr(REG_ACCEL_CFG, 0x00);
}

void imu_read(imu_raw_t *out)
{
    uint8_t reg = REG_ACCEL_X;
    uint8_t buf[14];
    i2c_master_transmit_receive(s_dev, &reg, 1, buf, 14, -1);
    out->ax = (int16_t) (buf[0] << 8 | buf[1]);
    out->ay = (int16_t) (buf[2] << 8 | buf[3]);
    out->az = (int16_t) (buf[4] << 8 | buf[5]);
    out->gx = (int16_t) (buf[8] << 8 | buf[9]);
    out->gy = (int16_t) (buf[10] << 8 | buf[11]);
    out->gz = (int16_t) (buf[12] << 8 | buf[13]);
}
