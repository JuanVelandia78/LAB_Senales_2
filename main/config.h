#pragma once

#define FILT_NONE 0
#define FILT_CONV 1
#define FILT_MA   2
#define FILT_AR   3
#define FILT_LMS  4

#define CONV_FIR 0
#define CONV_IIR 1

#define FILTER    FILT_NONE
#define CONV_TYPE CONV_IIR

#define MA_WINDOW 8
#define AR_ALPHA  0.15f
#define LMS_TAPS  16
#define LMS_DELAY 1
#define LMS_MU    0.02f

#define IMU_SDA 21
#define IMU_SCL 22
#define ENC_PIN_A 19
#define ENC_PIN_B 18
