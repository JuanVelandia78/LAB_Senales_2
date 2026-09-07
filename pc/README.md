# FILTRADO DE SEÑALES PERIÓDICAS — lado PC

Firmware en `../main` (ESP-IDF). Aquí van el diseño de filtros y el análisis en Python.

## Cómo correr los scripts sin terminal

Ninguno necesita argumentos: se abren y se ejecutan con un clic.

**VS Code** (ya está configurado en `.vscode/`):
1. Abre la carpeta del proyecto en VS Code.
2. Abre el `.py` que quieras.
3. Botón **▶ "Run Python File"** (arriba a la derecha) o tecla **F5**.
4. Si algún script hace una pregunta (`adquisicion.py` pide el nombre), la escribes en el
   panel de abajo y pulsas Enter. `etapa0_receptor.py` se corta con el botón de stop (■).
5. Las gráficas se abren en ventana aparte.

**Alternativa sin VS Code:** abrir el `.py` con **IDLE** y pulsar **F5**.

Config a editar una vez (arriba de cada archivo): `PORT` (p. ej. `COM5`) y `BAUD` (921600).

---

## Para qué sirve cada uno

| Script | ¿Hardware? | Qué hace |
|---|---|---|
| `diseno_filtros.py` | No | Diseña los 4 filtros (FIR/IIR × pasa-bajos/pasa-banda) con las specs de la guía, verifica rizado y atenuación, y **genera `../main/filtros.h`** y `salidas/filtros.npz`. Imprime orden y multiplicaciones por muestra. **Correr primero.** |
| `respuesta_filtros.py` | No | Dibuja magnitud (dB), fase y retardo de grupo de cada filtro en `salidas/respuesta_*.png` y dice si **cumple**. Si dice `NO`, ajustar `diseno_filtros.py` y repetir. |
| `etapa0_receptor.py` | Sí (`BYPASS 1`) | Etapa 0: captura unos segundos y comprueba **fs efectiva ≈ 500 Hz**, huecos en el índice, `overruns`, jitter y saturación del ADC. Guarda `etapa0_captura.csv` y muestra 2 gráficas. |
| `adquisicion.py` | Sí | Graba `SEGUNDOS` de datos del ESP32 en `capturas/<nombre>.captura.csv`. Se usa para guardar cada señal del generador (una corrida por frecuencia) y también las señales filtradas en línea. |
| `simulacion.py` | No | Aplica los 4 filtros a **todos** los CSV de `capturas/`, mide la amplitud del fundamental antes/después con FFT y arma `salidas/tabla_ganancia_simulacion.csv` (columnas "simulación" de la tabla de ganancia). |
| `analisis_fase.py` | No | Lee `fase_mediciones.csv` (Δt en ms medidos con el osciloscopio), resta el desfase base y convierte a ángulo → `salidas/tabla_fase.csv`. |

---

## Orden de trabajo

1. `diseno_filtros.py` → `respuesta_filtros.py` (diseño).
2. `../main/config.h`: `BYPASS 1`, `idf.py build flash`. Cerrar el monitor.
3. `etapa0_receptor.py` (Etapa 0). Desfase base: osciloscopio generador vs DAC/PWM →
   anotar `dt_base_*` en `fase_mediciones.csv`.
4. `adquisicion.py` una vez por frecuencia del generador (50–200 Hz).
5. `simulacion.py` (atenuación en simulación).
6. Para cada filtro: `config.h` con `BYPASS 0`, `FILTER_TYPE`, `FILTER_BAND`;
   `idf.py build flash`; `idf.py size` (memoria); osciloscopio para amplitud, tiempo de
   cómputo (GPIO4) y Δt de fase → `fase_mediciones.csv`.
7. `analisis_fase.py` (tabla de fase).

`capturas/` y `salidas/` están en `.gitignore`.
