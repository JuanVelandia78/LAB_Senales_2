# FILTRADO DE LAS SEÑALES DE LOS SENSORES

`fs = 200 muestras/s`. Firmware en `../../main` (la Parte 1 quedó en el commit
"FILTRADO DE SEÑALES PERIODICAS").
Sensores: IMU MPU6050 por I2C (GPIO21 SDA / GPIO22 SCL) y encoder en cuadratura
(GPIO32 / GPIO33). 7 canales: `ax ay az gx gy gz encv` (encv = cuentas del encoder por
muestra ≈ velocidad).

## Firmware — `../../main/config.h`

| Macro | Valores | Para qué |
|---|---|---|
| `FILTER` | `FILT_NONE` | sin filtrar (captura cruda, FFT, simulación) |
| | `FILT_CONV` | filtro convencional (FIR o IIR según `CONV_TYPE`) |
| | `FILT_MA` | media móvil, ventana `MA_WINDOW` |
| | `FILT_AR` | autorregresivo de 1.er orden (EMA), `AR_ALPHA` |
| | `FILT_LMS` | adaptativo LMS (line enhancer), `LMS_TAPS/DELAY/MU` |
| `CONV_TYPE` | `CONV_FIR` / `CONV_IIR` | tipo del filtro convencional |

`filtros_conv.h` lo genera `diseno_conv.py`. Cada canal lleva su propio estado de filtro.
Solo compila el filtro seleccionado → `idf.py size` mide cada estrategia por separado.
Pulso de cómputo en GPIO4, pulso de muestreo en GPIO13.

Compilar (desde la raíz del proyecto):
```bash
idf.py set-target esp32
idf.py build flash
```
`menuconfig`: `Console UART baud rate = 921600`, `Default log verbosity = Warning`.

## Cómo correr los scripts (sin terminal)

Igual que en la Parte 1: abrir el `.py` en VS Code y pulsar **▶ / F5**.
`adquisicion.py` pregunta el nombre de la captura. Editar `PORT` arriba de `adquisicion.py`.

| Script | ¿ESP32? | Función |
|---|---|---|
| `diseno_conv.py` | No | Diseña FIR e IIR pasa-bajos (parámetros arriba del archivo, ajustar según la FFT), genera `../../main/filtros_conv.h` y `salidas/filtros_conv.npz`. |
| `adquisicion.py` | Sí (`FILT_NONE`) | Graba `SEGUNDOS` del stream de sensores en `capturas/<nombre>.captura.csv` (crudo + filtrado). Hacer capturas en reposo y con movimiento. |
| `fft.py` | No | PSD de cada canal de cada captura (`salidas/fft_*.png`) y tabla con la banda de la señal y el piso de ruido → sirve para fijar los cortes en `diseno_conv.py`. |
| `filtros_alt.py` | No | Sobre la última captura, barre `MA_WINDOW`, `AR_ALPHA` y `LMS_MU`, mide reducción de ruido y retardo, y recomienda valores. Esos valores van a `config.h`. |
| `evaluacion.py` | No | Aplica los 5 métodos (conv FIR, conv IIR, media móvil, AR, LMS) a todas las capturas y todos los canales. Genera las tablas de caracterización antes/después, `resumen_reduccion.csv` y `tabla_final.csv`. |

`evaluacion.py` combina la reducción de ruido con `recursos.csv`, que tú llenas con el tiempo
de cómputo (osciloscopio en GPIO4) y la memoria (`idf.py size` por cada build).

## Orden de trabajo

1. `FILTER = FILT_NONE`, `idf.py build flash`, cerrar monitor.
2. `adquisicion.py` — varias capturas (reposo, giro, avance).
3. `fft.py` — identificar banda de señal (movimiento) y banda de ruido.
4. `diseno_conv.py` — ajustar `FPASS/FSTOP` con lo visto en la FFT y generar el header.
5. `filtros_alt.py` — elegir `MA_WINDOW`, `AR_ALPHA`, `LMS_MU`; copiarlos a `config.h`.
6. Para cada `FILTER` (y `CONV_TYPE`): `idf.py build flash` + `idf.py size`; osciloscopio
   en GPIO4 para el tiempo de cómputo; capturar en línea con `adquisicion.py`. Llenar
   `recursos.csv`.
7. `evaluacion.py` — tablas finales y comparación de métodos.
