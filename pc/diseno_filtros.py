import os

import numpy as np
from scipy import signal

FS = 500.0

HERE = os.path.dirname(os.path.abspath(__file__))
SALIDAS = os.path.join(HERE, "salidas")
HEADER = os.path.normpath(os.path.join(HERE, "..", "main", "filtros.h"))

LP_FP, LP_FST, LP_APASS, LP_ASTOP = 100.0, 130.0, 1.0, 50.0
BP_FST1, BP_FP1, BP_FP2, BP_FST2 = 60.0, 80.0, 120.0, 140.0
BP_APASS, BP_ASTOP = 1.0, 40.0


def fir_lowpass():
    for n in range(21, 400, 2):
        b = signal.remez(n, [0, LP_FP, LP_FST, FS / 2], [1, 0],
                         weight=[1, 10], fs=FS)
        w, h = signal.freqz(b, worN=8192, fs=FS)
        hdb = 20 * np.log10(np.abs(h) + 1e-12)
        pb, sb = hdb[w <= LP_FP], hdb[w >= LP_FST]
        if pb.max() - pb.min() <= LP_APASS and sb.max() <= -LP_ASTOP:
            return b
    raise RuntimeError("FIR pasa-bajos no converge")


def fir_bandpass():
    for n in range(21, 600, 2):
        b = signal.remez(n, [0, BP_FST1, BP_FP1, BP_FP2, BP_FST2, FS / 2],
                         [0, 1, 0], weight=[10, 1, 10], fs=FS)
        w, h = signal.freqz(b, worN=8192, fs=FS)
        hdb = 20 * np.log10(np.abs(h) + 1e-12)
        pb = hdb[(w >= BP_FP1) & (w <= BP_FP2)]
        sb = np.concatenate([hdb[w <= BP_FST1], hdb[w >= BP_FST2]])
        if pb.max() - pb.min() <= BP_APASS and sb.max() <= -BP_ASTOP:
            return b
    raise RuntimeError("FIR pasa-banda no converge")


def iir_lowpass():
    n, wn = signal.ellipord(LP_FP / (FS / 2), LP_FST / (FS / 2),
                            LP_APASS, LP_ASTOP)
    return signal.ellip(n, LP_APASS, LP_ASTOP, wn, btype="low", output="sos")


def iir_bandpass():
    n, wn = signal.ellipord([BP_FP1 / (FS / 2), BP_FP2 / (FS / 2)],
                            [BP_FST1 / (FS / 2), BP_FST2 / (FS / 2)],
                            BP_APASS, BP_ASTOP)
    return signal.ellip(n, BP_APASS, BP_ASTOP, wn, btype="band", output="sos")


def medir_fir(b, banda):
    w, h = signal.freqz(b, worN=8192, fs=FS)
    hdb = 20 * np.log10(np.abs(h) + 1e-12)
    if banda == "LP":
        pb, sb = hdb[w <= LP_FP], hdb[w >= LP_FST]
    else:
        pb = hdb[(w >= BP_FP1) & (w <= BP_FP2)]
        sb = np.concatenate([hdb[w <= BP_FST1], hdb[w >= BP_FST2]])
    return pb.max() - pb.min(), sb.max()


def medir_iir(sos, banda):
    w, h = signal.sosfreqz(sos, worN=8192, fs=FS)
    hdb = 20 * np.log10(np.abs(h) + 1e-12)
    if banda == "LP":
        pb, sb = hdb[w <= LP_FP], hdb[w >= LP_FST]
    else:
        pb = hdb[(w >= BP_FP1) & (w <= BP_FP2)]
        sb = np.concatenate([hdb[w <= BP_FST1], hdb[w >= BP_FST2]])
    return pb.max() - pb.min(), sb.max()


def c_floats(v):
    return ", ".join(f"{x:.10e}f" for x in v)


def escribir_header(fir_lp, fir_bp, sos_lp, sos_bp):
    L = []
    L.append("#pragma once")
    L.append('#include "config.h"')
    L.append("")
    L.append("#if !BYPASS")
    L.append("")
    L.append("#if FILTER_TYPE == FILTER_FIR && FILTER_BAND == BAND_LOWPASS")
    L.append(f"#define FILT_NTAPS {len(fir_lp)}")
    L.append("static const float FILT_B[FILT_NTAPS] = {")
    L.append("    " + c_floats(fir_lp))
    L.append("};")
    L.append("#endif")
    L.append("")
    L.append("#if FILTER_TYPE == FILTER_FIR && FILTER_BAND == BAND_BANDPASS")
    L.append(f"#define FILT_NTAPS {len(fir_bp)}")
    L.append("static const float FILT_B[FILT_NTAPS] = {")
    L.append("    " + c_floats(fir_bp))
    L.append("};")
    L.append("#endif")
    L.append("")
    L.append("#if FILTER_TYPE == FILTER_IIR && FILTER_BAND == BAND_LOWPASS")
    L.append(f"#define FILT_NSOS {sos_lp.shape[0]}")
    L.append("static const float FILT_SOS[FILT_NSOS][6] = {")
    for row in sos_lp:
        L.append("    {" + c_floats(row) + "},")
    L.append("};")
    L.append("#endif")
    L.append("")
    L.append("#if FILTER_TYPE == FILTER_IIR && FILTER_BAND == BAND_BANDPASS")
    L.append(f"#define FILT_NSOS {sos_bp.shape[0]}")
    L.append("static const float FILT_SOS[FILT_NSOS][6] = {")
    for row in sos_bp:
        L.append("    {" + c_floats(row) + "},")
    L.append("};")
    L.append("#endif")
    L.append("")
    L.append("#endif")
    L.append("")
    with open(HEADER, "w") as f:
        f.write("\n".join(L))


def main():
    os.makedirs(SALIDAS, exist_ok=True)

    fir_lp = fir_lowpass()
    fir_bp = fir_bandpass()
    sos_lp = iir_lowpass()
    sos_bp = iir_bandpass()

    np.savez(os.path.join(SALIDAS, "filtros.npz"),
             fs=FS, fir_lp=fir_lp, fir_bp=fir_bp,
             sos_lp=sos_lp, sos_bp=sos_bp)

    escribir_header(fir_lp, fir_bp, sos_lp, sos_bp)

    r_lp = medir_fir(fir_lp, "LP")
    r_bp = medir_fir(fir_bp, "BP")
    i_lp = medir_iir(sos_lp, "LP")
    i_bp = medir_iir(sos_bp, "BP")

    print("================ DISEÑO DE FILTROS ================")
    print(f"{'Filtro':<16}{'Orden/Taps':<12}{'Mult/muestra':<14}"
          f"{'Rizado pb (dB)':<16}{'Atenuacion sb (dB)':<20}")
    print(f"{'FIR pasa-bajos':<16}{len(fir_lp):<12}{len(fir_lp):<14}"
          f"{r_lp[0]:<16.3f}{r_lp[1]:<20.2f}")
    print(f"{'FIR pasa-banda':<16}{len(fir_bp):<12}{len(fir_bp):<14}"
          f"{r_bp[0]:<16.3f}{r_bp[1]:<20.2f}")
    print(f"{'IIR pasa-bajos':<16}{sos_lp.shape[0] * 2:<12}"
          f"{sos_lp.shape[0] * 5:<14}{i_lp[0]:<16.3f}{i_lp[1]:<20.2f}")
    print(f"{'IIR pasa-banda':<16}{sos_bp.shape[0] * 2:<12}"
          f"{sos_bp.shape[0] * 5:<14}{i_bp[0]:<16.3f}{i_bp[1]:<20.2f}")
    print()
    print(f"Header escrito en {HEADER}")
    print(f"Coeficientes en   {os.path.join(SALIDAS, 'filtros.npz')}")


if __name__ == "__main__":
    main()
