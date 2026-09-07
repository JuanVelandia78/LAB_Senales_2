import os
import time

import serial
import numpy as np
import pandas as pd

PORT = "COM5"
BAUD = 921600
SEGUNDOS = 10.0

HERE = os.path.dirname(os.path.abspath(__file__))
CAPTURAS = os.path.join(HERE, "capturas")

CH = ["ax", "ay", "az", "gx", "gy", "gz", "encv"]


def main():
    os.makedirs(CAPTURAS, exist_ok=True)

    nombre = input("Nombre de la captura (ej. reposo, giro): ").strip()
    if not nombre:
        nombre = time.strftime("captura_%H%M%S")
    if not nombre.endswith(".csv"):
        nombre += ".captura.csv"
    ruta = os.path.join(CAPTURAS, nombre)

    ser = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)
    ser.reset_input_buffer()

    filas = []
    t0 = time.time()
    print(f"Capturando {SEGUNDOS:.0f} s en {PORT} ...")
    while time.time() - t0 < SEGUNDOS:
        line = ser.readline().decode("ascii", errors="ignore").strip()
        parts = line.split(",")
        if len(parts) != 17:
            continue
        try:
            filas.append([int(p) for p in parts])
        except ValueError:
            continue
    ser.close()

    if not filas:
        print("Sin datos. Revisa PORT, la IMU y que el monitor este cerrado.")
        return

    cols = ["n", "t_us"] + CH + [f"f_{c}" for c in CH] + ["overruns"]
    df = pd.DataFrame(filas, columns=cols).drop_duplicates("n").reset_index(drop=True)
    for c in CH:
        df[f"f_{c}"] = df[f"f_{c}"] / 1000.0

    dt = np.diff(df["t_us"].to_numpy())
    fs = 1e6 / np.median(dt)
    df["t_s"] = (df["t_us"] - df["t_us"].iloc[0]) / 1e6

    df.to_csv(ruta, index=False)
    print(f"{len(df)} muestras   fs~{fs:.2f} Hz   "
          f"overruns={int(df['overruns'].iloc[-1])}")
    print(f"Guardado en {ruta}")


if __name__ == "__main__":
    main()
