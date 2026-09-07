import glob
import os

import numpy as np
import pandas as pd
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
CAPTURAS = os.path.join(HERE, "capturas")
SALIDAS = os.path.join(HERE, "salidas")

CH = ["ax", "ay", "az", "gx", "gy", "gz", "encv"]
FS = 200.0


def lista_capturas():
    return sorted(glob.glob(os.path.join(CAPTURAS, "*.captura.csv")))


def cargar(ruta):
    return pd.read_csv(ruta)


def psd(x, fs=FS):
    x = np.asarray(x, dtype=float)
    x = x - np.mean(x)
    nper = min(len(x), 512)
    f, pxx = signal.welch(x, fs=fs, nperseg=nper)
    return f, pxx


def banda_senal(f, pxx, frac=0.95):
    e = np.cumsum(pxx)
    e = e / e[-1]
    return float(f[np.searchsorted(e, frac)])


def piso_ruido(f, pxx, f_desde):
    m = f >= f_desde
    if not m.any():
        return float("nan")
    return float(np.median(pxx[m]))


def referencia(x, fcorte=12.0, fs=FS):
    sos = signal.butter(4, fcorte / (fs / 2), output="sos")
    return signal.sosfiltfilt(sos, np.asarray(x, dtype=float))


def rms(x):
    x = np.asarray(x, dtype=float)
    return float(np.sqrt(np.mean((x - np.mean(x)) ** 2)))


def fir_causal(x, b):
    return signal.lfilter(b, [1.0], np.asarray(x, dtype=float))


def iir_causal(x, sos):
    return signal.sosfilt(sos, np.asarray(x, dtype=float))


def media_movil(x, w):
    return signal.lfilter(np.ones(w) / w, [1.0], np.asarray(x, dtype=float))


def autorregresivo(x, alpha):
    return signal.lfilter([alpha], [1.0, -(1.0 - alpha)], np.asarray(x, dtype=float))


def lms_ale(x, taps, delay, mu):
    x = np.asarray(x, dtype=float)
    w = np.zeros(taps)
    dl = np.zeros(taps + delay)
    y = np.zeros_like(x)
    for n in range(len(x)):
        dl[1:] = dl[:-1]
        dl[0] = x[n]
        r = dl[delay:delay + taps]
        yn = float(w @ r)
        e = x[n] - yn
        p = 1e-6 + float(r @ r)
        w += (mu / p) * e * r
        y[n] = yn
    return y


def retardo_muestras(y, ref):
    y = np.asarray(y, dtype=float) - np.mean(y)
    ref = np.asarray(ref, dtype=float) - np.mean(ref)
    c = signal.correlate(y, ref, mode="full")
    lag = np.argmax(c) - (len(ref) - 1)
    return int(lag)
