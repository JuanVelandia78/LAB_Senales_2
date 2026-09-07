import os

import numpy as np
import pandas as pd

from comun import (SALIDAS, lista_capturas, cargar, referencia, rms,
                   media_movil, autorregresivo, lms_ale, retardo_muestras)

CANAL = "gz"
MA_WINDOWS = [2, 4, 8, 16, 32]
AR_ALPHAS = [0.05, 0.1, 0.2, 0.4]
LMS_MUS = [0.005, 0.01, 0.02, 0.05]
LMS_TAPS = 16
LMS_DELAY = 1


def evaluar(x, y, ref):
    ruido_in = rms(x - ref)
    err = rms(y - ref)
    red_db = 20 * np.log10(ruido_in / (err + 1e-12))
    return round(red_db, 2), retardo_muestras(y, ref)


def main():
    rutas = lista_capturas()
    if not rutas:
        print("No hay CSV en capturas/. Corre adquisicion.py primero.")
        return

    df = cargar(rutas[-1])
    x = df[CANAL].to_numpy(dtype=float)
    ref = referencia(x)
    print(f"Archivo: {os.path.basename(rutas[-1])}   canal: {CANAL}")
    print(f"Ruido de entrada (RMS vs referencia): {rms(x - ref):.3f}\n")

    filas = []
    for w in MA_WINDOWS:
        red, lag = evaluar(x, media_movil(x, w), ref)
        filas.append({"metodo": "media_movil", "param": f"W={w}",
                      "reduccion_dB": red, "retardo_muestras": lag})
    for a in AR_ALPHAS:
        red, lag = evaluar(x, autorregresivo(x, a), ref)
        filas.append({"metodo": "autorregresivo", "param": f"alpha={a}",
                      "reduccion_dB": red, "retardo_muestras": lag})
    for mu in LMS_MUS:
        red, lag = evaluar(x, lms_ale(x, LMS_TAPS, LMS_DELAY, mu), ref)
        filas.append({"metodo": "lms", "param": f"mu={mu}",
                      "reduccion_dB": red, "retardo_muestras": lag})

    tabla = pd.DataFrame(filas)
    os.makedirs(SALIDAS, exist_ok=True)
    out = os.path.join(SALIDAS, "ajuste_filtros_alt.csv")
    tabla.to_csv(out, index=False)
    print(tabla.to_string(index=False))

    print("\nRecomendado (mayor reduccion con retardo bajo):")
    for m in ["media_movil", "autorregresivo", "lms"]:
        sub = tabla[tabla["metodo"] == m]
        sub = sub[sub["retardo_muestras"] <= 4]
        if len(sub) == 0:
            sub = tabla[tabla["metodo"] == m]
        best = sub.loc[sub["reduccion_dB"].idxmax()]
        print(f"  {m:<15} {best['param']:<12} "
              f"reduccion {best['reduccion_dB']} dB   retardo {best['retardo_muestras']}")
    print(f"\nGuardado en {out}")


if __name__ == "__main__":
    main()
