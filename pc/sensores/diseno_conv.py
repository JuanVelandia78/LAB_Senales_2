import os

import numpy as np
from scipy import signal

FS = 200.0

FPASS = 12.0
FSTOP = 30.0
APASS = 1.0
ASTOP = 40.0

HERE = os.path.dirname(os.path.abspath(__file__))
SALIDAS = os.path.join(HERE, "salidas")
HEADER = os.path.normpath(os.path.join(HERE, "..", "..", "main",
                                       "filtros_conv.h"))


def fir_lowpass():
    for n in range(15, 400, 2):
        b = signal.remez(n, [0, FPASS, FSTOP, FS / 2], [1, 0],
                         weight=[1, 10], fs=FS)
        w, h = signal.freqz(b, worN=8192, fs=FS)
        hdb = 20 * np.log10(np.abs(h) + 1e-12)
        pb, sb = hdb[w <= FPASS], hdb[w >= FSTOP]
        if pb.max() - pb.min() <= APASS and sb.max() <= -ASTOP:
            return b
    raise RuntimeError("FIR no converge")


def iir_lowpass():
    n, wn = signal.ellipord(FPASS / (FS / 2), FSTOP / (FS / 2), APASS, ASTOP)
    return signal.ellip(n, APASS, ASTOP, wn, btype="low", output="sos")


def c_floats(v):
    return ", ".join(f"{x:.10e}f" for x in v)


def escribir_header(fir_b, sos):
    L = []
    L.append("#pragma once")
    L.append('#include "config.h"')
    L.append("")
    L.append("#if FILTER == FILT_CONV")
    L.append("")
    L.append("#if CONV_TYPE == CONV_FIR")
    L.append(f"#define FILT_NTAPS {len(fir_b)}")
    L.append("static const float FILT_B[FILT_NTAPS] = {")
    L.append("    " + c_floats(fir_b))
    L.append("};")
    L.append("#else")
    L.append(f"#define FILT_NSOS {sos.shape[0]}")
    L.append("static const float FILT_SOS[FILT_NSOS][6] = {")
    for row in sos:
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

    fir_b = fir_lowpass()
    sos = iir_lowpass()

    np.savez(os.path.join(SALIDAS, "filtros_conv.npz"),
             fs=FS, fir_b=fir_b, sos=sos,
             fpass=FPASS, fstop=FSTOP)
    escribir_header(fir_b, sos)

    w, h = signal.freqz(fir_b, worN=8192, fs=FS)
    hdb = 20 * np.log10(np.abs(h) + 1e-12)
    fir_att = hdb[w >= FSTOP].max()
    fir_rip = hdb[w <= FPASS].max() - hdb[w <= FPASS].min()

    w, h = signal.sosfreqz(sos, worN=8192, fs=FS)
    hdb = 20 * np.log10(np.abs(h) + 1e-12)
    iir_att = hdb[w >= FSTOP].max()
    iir_rip = hdb[w <= FPASS].max() - hdb[w <= FPASS].min()

    print("========== FILTROS CONVENCIONALES (sensores) ==========")
    print(f"fs = {FS} Hz   pasa-bajos {FPASS} Hz -> {FSTOP} Hz   "
          f"Apass {APASS} dB   Astop {ASTOP} dB")
    print(f"{'Filtro':<14}{'Orden/Taps':<12}{'Mult/muestra':<14}"
          f"{'Rizado pb':<12}{'Atenuacion sb':<14}")
    print(f"{'FIR':<14}{len(fir_b):<12}{len(fir_b):<14}"
          f"{fir_rip:<12.3f}{fir_att:<14.2f}")
    print(f"{'IIR':<14}{sos.shape[0] * 2:<12}{sos.shape[0] * 5:<14}"
          f"{iir_rip:<12.3f}{iir_att:<14.2f}")
    print()
    print(f"Header:       {HEADER}")
    print(f"Coeficientes: {os.path.join(SALIDAS, 'filtros_conv.npz')}")


if __name__ == "__main__":
    main()
