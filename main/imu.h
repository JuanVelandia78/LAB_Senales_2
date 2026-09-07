#pragma once
#include <stdint.h>

typedef struct {
    int16_t ax, ay, az;
    int16_t gx, gy, gz;
} imu_raw_t;

void imu_init(void);
void imu_read(imu_raw_t *out);
