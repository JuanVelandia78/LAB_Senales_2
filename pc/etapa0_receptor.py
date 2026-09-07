import time

import serial
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

PORT = "COM5"
BAUD = 921600
OUT_CSV = "etapa0_captura.csv"
FS_NOM = 500.0


def leer(ser):
    n_list, t_list, raw_list, ovr_list = [], [], [], []
    print("Capturando... Ctrl+C para terminar y analizar.")
    try:
        while True:
            line = ser.readline().decode("ascii", errors="ignore").strip()
            parts = line.split(",")
            if len(parts) not in (4, 5):
                continue
            try:
                n = int(parts[0])
                t_us = int(parts[1])
                raw = int(parts[2])
                ovr = int(parts[-1])
            except ValueError:
                continue
            n_list.append(n)
            t_list.append(t_us)
            raw_list.append(raw)
            ovr_list.append(ovr)
    except KeyboardInterrupt:
        pass
    return n_list, t_list, raw_list, ovr_list


def analizar(n_list, t_list, raw_list, ovr_list):
    df = pd.DataFrame({
        "n": n_list,
        "t_us": t_list,
        "raw": raw_list,
        "overruns": ovr_list,
    })
    df = df.drop_duplicates(subset="n").reset_index(drop=True)
    df["t_s"] = (df["t_us"] - df["t_us"].iloc[0]) / 1e6
    df["v_in"] = df["raw"] * 3.3 / 4095.0

    n_arr = df["n"].to_numpy()
    t_arr = df["t_us"].to_numpy()
    gaps = int(np.count_nonzero(np.diff(n_arr) != 1))
    dt_us = np.diff(t_arr)
    fs_eff = 1e6 / np.median(dt_us)
    jitter_us = float(np.std(dt_us))

    print("\n================ RESUMEN ETAPA 0 ================")
    print(f"Muestras recibidas   : {len(df)}")
    print(f"Huecos en indice n   : {gaps}")
    print(f"Overruns (ESP32)     : {int(df['overruns'].iloc[-1])}")
    print(f"fs efectiva          : {fs_eff:.3f} Hz  (nominal {FS_NOM})")
    print(f"Error de fs          : {100 * (fs_eff - FS_NOM) / FS_NOM:+.3f} %")
    print(f"Ts medio             : {np.mean(dt_us):.1f} us")
    print(f"Jitter (std Ts)      : {jitter_us:.1f} us")
    print(f"dt min / max         : {int(dt_us.min())} / {int(dt_us.max())} us")
    print(f"raw min / max        : {int(df['raw'].min())} / {int(df['raw'].max())}")

    df.to_csv(OUT_CSV, index=False)
    print(f"\nGuardado en {OUT_CSV}")

    fig, ax = plt.subplots(2, 1, figsize=(10, 6))
    ax[0].plot(df["t_s"], df["v_in"], lw=0.8)
    ax[0].set_title("Senal capturada")
    ax[0].set_xlabel("t [s]")
    ax[0].set_ylabel("V")
    ax[1].hist(dt_us, bins=40)
    ax[1].set_title(f"Periodo de muestreo (fs_eff = {fs_eff:.2f} Hz)")
    ax[1].set_xlabel("dt [us]")
    ax[1].set_ylabel("cuentas")
    plt.tight_layout()
    plt.show()


def main():
    ser = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)
    ser.reset_input_buffer()
    n_list, t_list, raw_list, ovr_list = leer(ser)
    ser.close()

    if not n_list:
        print("No se recibieron datos. Revisa PORT y BAUD.")
        return

    analizar(n_list, t_list, raw_list, ovr_list)


if __name__ == "__main__":
    main()
