import os
import time

import serial
import numpy as np
import pandas as pd

PORT = "COM5"
BAUD = 921600
SEGUNDOS = 4.0

HERE = os.path.dirname(os.path.abspath(__file__))
CAPTURAS = os.path.join(HERE, "capturas")


def main():
    os.makedirs(CAPTURAS, exist_ok=True)

    nombre = input("Nombre de la captura (ej. f100Hz): ").strip()
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
        if len(parts) not in (4, 5):
            continue
        try:
            filas.append([int(p) for p in parts])
        except ValueError:
            continue
    ser.close()

    if not filas:
        print("Sin datos. Revisa PORT, el cable y que el monitor este cerrado.")
        return

    ancho = max(len(f) for f in filas)
    filas = [f for f in filas if len(f) == ancho]
    cols = (["n", "t_us", "raw", "overruns"] if ancho == 4
            else ["n", "t_us", "raw", "y", "overruns"])
    df = pd.DataFrame(filas, columns=cols).drop_duplicates("n").reset_index(drop=True)

    dt = np.diff(df["t_us"].to_numpy())
    fs = 1e6 / np.median(dt)
    df["t_s"] = (df["t_us"] - df["t_us"].iloc[0]) / 1e6
    df["v_in"] = df["raw"] * 3.3 / 4095.0
    if "y" in df.columns:
        df["v_out"] = df["y"] * 3.3 / 4095.0

    df.to_csv(ruta, index=False)
    print(f"{len(df)} muestras   fs~{fs:.2f} Hz   "
          f"overruns={int(df['overruns'].iloc[-1])}")
    print(f"Guardado en {ruta}")


if __name__ == "__main__":
    main()
