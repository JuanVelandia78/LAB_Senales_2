idf_component_register(SRCS "main.c" "imu.c" "encoder.c"
                    INCLUDE_DIRS "."
                    REQUIRES driver esp_timer)
