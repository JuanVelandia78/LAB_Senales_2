import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from comun import (CH, FS, SALIDAS, lista_capturas, cargar, psd,
                   banda_senal, piso_ruido)


def main():
    rutas = lista_capturas()
    if not rutas:
        print("No hay CSV en capturas/. Corre adquisicion.py primero.")
        return

    os.makedirs(SALIDAS, exist_ok=True)

    for ruta in rutas:
        df = cargar(ruta)
        nombre = os.path.basename(ruta).replace(".captura.csv", "")

        fig, axes = plt.subplots(4, 2, figsize=(11, 12))
        axes = axes.ravel()
        filas = []
        for i, c in enumerate(CH):
            f, pxx = psd(df[c].to_numpy())
            f95 = banda_senal(f, pxx)
            piso = piso_ruido(f, pxx, min(2 * f95, FS / 2 * 0.6))
            filas.append({"canal": c, "banda_senal_Hz": round(f95, 2),
                          "piso_ruido_PSD": f"{piso:.3e}"})
            ax = axes[i]
            ax.semilogy(f, pxx)
            ax.axvline(f95, color="r", ls="--", lw=1)
            ax.set_title(f"{c}   banda~{f95:.1f} Hz")
            ax.set_xlabel("Hz")
            ax.grid(True, which="both", alpha=0.3)
        axes[-1].axis("off")
        fig.suptitle(f"PSD por canal — {nombre}")
        fig.tight_layout(rect=(0, 0, 1, 0.97))
        png = os.path.join(SALIDAS, f"fft_{nombre}.png")
        fig.savefig(png, dpi=110)
        plt.close(fig)

        tabla = pd.DataFrame(filas)
        print(f"\n=== {nombre} ===")
        print(tabla.to_string(index=False))
        print(f"PNG: {png}")


if __name__ == "__main__":
    main()
