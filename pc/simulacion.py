import glob
import os

import numpy as np
import pandas as pd
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
SALIDAS = os.path.join(HERE, "salidas")
CAPTURAS = os.path.join(HERE, "capturas")
DESCARTAR = 200


def amp_fundamental(x, fs):
    x = np.asarray(x, dtype=float)
    x = x - np.mean(x)
    n = len(x)
    win = np.hanning(n)
    esp = np.fft.rfft(x * win)
    frec = np.fft.rfftfreq(n, 1.0 / fs)
    k = np.argmax(np.abs(esp[1:])) + 1
    amp = 2.0 * np.abs(esp[k]) / np.sum(win)
    return frec[k], amp


def aplicar(x, filt):
    tipo, coef = filt
    if tipo == "fir":
        return signal.lfilter(coef, [1.0], x)
    return signal.sosfilt(coef, x)


def main():
    d = np.load(os.path.join(SALIDAS, "filtros.npz"))
    fs = float(d["fs"])
    filtros = {
        "FIR-LP": ("fir", d["fir_lp"]),
        "IIR-LP": ("iir", d["sos_lp"]),
        "FIR-BP": ("fir", d["fir_bp"]),
        "IIR-BP": ("iir", d["sos_bp"]),
    }

    rutas = sorted(glob.glob(os.path.join(CAPTURAS, "*.captura.csv")))
    if not rutas:
        print("No hay CSV en capturas/. Corre adquisicion.py primero.")
        return

    filas = []
    for ruta in rutas:
        df = pd.read_csv(ruta)
        if "v_in" in df.columns:
            v = df["v_in"].to_numpy()
        else:
            v = df["raw"].to_numpy() * 3.3 / 4095.0
        f0, a_in = amp_fundamental(v[DESCARTAR:], fs)
        fila = {"archivo": os.path.basename(ruta),
                "f_Hz": round(float(f0), 2),
                "A_in_V": round(float(a_in), 4)}
        for nombre, filt in filtros.items():
            y = aplicar(v, filt)
            _, a_out = amp_fundamental(y[DESCARTAR:], fs)
            fila[f"A_out_{nombre}_V"] = round(float(a_out), 4)
            fila[f"G_{nombre}_dB"] = round(
                float(20 * np.log10(a_out / a_in + 1e-12)), 2)
        filas.append(fila)

    tabla = pd.DataFrame(filas).sort_values("f_Hz").reset_index(drop=True)
    os.makedirs(SALIDAS, exist_ok=True)
    out = os.path.join(SALIDAS, "tabla_ganancia_simulacion.csv")
    tabla.to_csv(out, index=False)

    pd.set_option("display.width", 240)
    pd.set_option("display.max_columns", 40)
    print(tabla.to_string(index=False))
    print(f"\nGuardado en {out}")


if __name__ == "__main__":
    main()
