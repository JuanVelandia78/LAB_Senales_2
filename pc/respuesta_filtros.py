import os

import numpy as np
from scipy import signal
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
SALIDAS = os.path.join(HERE, "salidas")

LP = dict(fp=100.0, fst=130.0, apass=1.0, astop=50.0)
BP = dict(fst1=60.0, fp1=80.0, fp2=120.0, fst2=140.0, apass=1.0, astop=40.0)


def respuesta(b, a, sos, fs):
    if sos is not None:
        return signal.sosfreqz(sos, worN=16384, fs=fs)
    return signal.freqz(b, a, worN=16384, fs=fs)


def retardo_grupo(b, a, sos, fs):
    if sos is not None:
        b, a = signal.sos2tf(sos)
    return signal.group_delay((b, a), w=16384, fs=fs)


def verificar(w, hdb, banda):
    if banda == "lp":
        pb = hdb[w <= LP["fp"]]
        sb = hdb[w >= LP["fst"]]
        req = LP["astop"]
    else:
        pb = hdb[(w >= BP["fp1"]) & (w <= BP["fp2"])]
        sb = np.concatenate([hdb[w <= BP["fst1"]], hdb[w >= BP["fst2"]]])
        req = BP["astop"]
    rip = pb.max() - pb.min()
    att = sb.max()
    return rip, att, (rip <= 1.0 + 1e-6 and att <= -req + 1e-6)


def figura(nombre, w, h, wg, gd, titulo, rip, att):
    hdb = 20 * np.log10(np.abs(h) + 1e-12)
    fase = np.unwrap(np.angle(h))
    fig, ax = plt.subplots(3, 1, figsize=(9, 9), sharex=True)
    ax[0].plot(w, hdb)
    ax[0].set_ylabel("|H| [dB]")
    ax[0].set_ylim(-90, 5)
    ax[0].set_title(titulo)
    ax[0].grid(True)
    ax[1].plot(w, np.degrees(fase))
    ax[1].set_ylabel("Fase [deg]")
    ax[1].grid(True)
    ax[2].plot(wg, gd)
    ax[2].set_ylabel("Retardo de grupo [muestras]")
    ax[2].set_xlabel("Frecuencia [Hz]")
    ax[2].grid(True)
    fig.text(0.5, 0.005,
             f"rizado banda de paso = {rip:.3f} dB    "
             f"atenuacion banda rechazada = {att:.2f} dB",
             ha="center")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(os.path.join(SALIDAS, nombre), dpi=110)
    plt.close(fig)


def main():
    d = np.load(os.path.join(SALIDAS, "filtros.npz"))
    fs = float(d["fs"])
    filtros = [
        ("respuesta_fir_lp.png", "FIR pasa-bajos", d["fir_lp"], [1.0], None, "lp"),
        ("respuesta_fir_bp.png", "FIR pasa-banda", d["fir_bp"], [1.0], None, "bp"),
        ("respuesta_iir_lp.png", "IIR pasa-bajos", None, None, d["sos_lp"], "lp"),
        ("respuesta_iir_bp.png", "IIR pasa-banda", None, None, d["sos_bp"], "bp"),
    ]

    print(f"{'Filtro':<16}{'Rizado pb (dB)':<18}"
          f"{'Atenuacion sb (dB)':<20}{'Cumple':<8}")
    for nombre, titulo, b, a, sos, banda in filtros:
        w, h = respuesta(b, a, sos, fs)
        wg, gd = retardo_grupo(b, a, sos, fs)
        hdb = 20 * np.log10(np.abs(h) + 1e-12)
        rip, att, ok = verificar(w, hdb, banda)
        figura(nombre, w, h, wg, gd, titulo, rip, att)
        print(f"{titulo:<16}{rip:<18.3f}{att:<20.2f}{'si' if ok else 'NO':<8}")
    print(f"\nPNG en {SALIDAS}")


if __name__ == "__main__":
    main()
