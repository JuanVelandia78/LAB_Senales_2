import os

import numpy as np
import pandas as pd

from comun import (CH, FS, HERE, SALIDAS, lista_capturas, cargar, psd,
                   banda_senal, referencia, rms,
                   fir_causal, iir_causal, media_movil, autorregresivo, lms_ale)

MA_WINDOW = 8
AR_ALPHA = 0.15
LMS_TAPS = 16
LMS_DELAY = 1
LMS_MU = 0.02


def cargar_conv():
    d = np.load(os.path.join(SALIDAS, "filtros_conv.npz"))
    return d["fir_b"], d["sos"]


def metodos(fir_b, sos):
    return {
        "conv_fir": lambda x: fir_causal(x, fir_b),
        "conv_iir": lambda x: iir_causal(x, sos),
        "media_movil": lambda x: media_movil(x, MA_WINDOW),
        "autorregresivo": lambda x: autorregresivo(x, AR_ALPHA),
        "lms": lambda x: lms_ale(x, LMS_TAPS, LMS_DELAY, LMS_MU),
    }


def caracterizar(x, y=None):
    ref = referencia(x)
    base = x if y is None else y
    f, pxx = psd(base)
    f95 = banda_senal(f, pxx)
    senal_amp = rms(referencia(base))
    ruido_amp = rms(base - ref)
    return {
        "ancho_banda_Hz": round(f95, 2),
        "senal_banda_Hz": f"0-{f95:.1f}",
        "senal_amp_RMS": round(senal_amp, 3),
        "ruido_banda_Hz": f"{f95:.1f}-{FS/2:.0f}",
        "ruido_amp_RMS": round(ruido_amp, 3),
    }


def main():
    rutas = lista_capturas()
    if not rutas:
        print("No hay CSV en capturas/. Corre adquisicion.py primero.")
        return
    if not os.path.exists(os.path.join(SALIDAS, "filtros_conv.npz")):
        print("Falta salidas/filtros_conv.npz. Corre diseno_conv.py primero.")
        return

    os.makedirs(SALIDAS, exist_ok=True)
    fir_b, sos = cargar_conv()
    funcs = metodos(fir_b, sos)

    antes = []
    despues = {m: [] for m in funcs}
    reduccion = []

    for ruta in rutas:
        df = cargar(ruta)
        arch = os.path.basename(ruta).replace(".captura.csv", "")
        for c in CH:
            x = df[c].to_numpy(dtype=float)
            ref = referencia(x)
            ruido_in = rms(x - ref)

            fila = {"archivo": arch, "canal": c}
            fila.update(caracterizar(x))
            antes.append(fila)

            for m, fn in funcs.items():
                y = fn(x)
                f2 = {"archivo": arch, "canal": c}
                f2.update(caracterizar(x, y))
                despues[m].append(f2)

                err = rms(y - ref)
                reduccion.append({
                    "archivo": arch, "canal": c, "metodo": m,
                    "reduccion_dB": round(20 * np.log10(ruido_in / (err + 1e-12)), 2),
                })

    pd.DataFrame(antes).to_csv(
        os.path.join(SALIDAS, "caracterizacion_antes.csv"), index=False)
    for m, filas in despues.items():
        pd.DataFrame(filas).to_csv(
            os.path.join(SALIDAS, f"caracterizacion_{m}.csv"), index=False)

    red = pd.DataFrame(reduccion)
    red.to_csv(os.path.join(SALIDAS, "resumen_reduccion.csv"), index=False)

    resumen = red.groupby("metodo")["reduccion_dB"].mean().round(2).reset_index()
    resumen = resumen.rename(columns={"reduccion_dB": "reduccion_media_dB"})

    rec_path = os.path.join(HERE, "recursos.csv")
    if os.path.exists(rec_path):
        rec = pd.read_csv(rec_path)
        resumen = resumen.merge(rec, on="metodo", how="left")

    resumen.to_csv(os.path.join(SALIDAS, "tabla_final.csv"), index=False)

    pd.set_option("display.width", 240)
    pd.set_option("display.max_columns", 40)
    print("Reduccion media de ruido por metodo (dB):")
    print(resumen.to_string(index=False))
    print(f"\nTablas en {SALIDAS}")


if __name__ == "__main__":
    main()
