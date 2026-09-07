import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SALIDAS = os.path.join(HERE, "salidas")
ENTRADA = os.path.join(HERE, "fase_mediciones.csv")


def angulo(f_hz, dt_ms):
    return 360.0 * f_hz * dt_ms / 1000.0


def main():
    df = pd.read_csv(ENTRADA)
    f = df["f_Hz"].to_numpy(dtype=float)

    out = pd.DataFrame({"f_Hz": f})
    for tipo in ["fir", "iir"]:
        for rec in ["pwm", "dac"]:
            neto = df[f"dt_{tipo}_{rec}_ms"] - df[f"dt_base_{rec}_ms"]
            out[f"{tipo.upper()}_{rec.upper()}_dt_ms"] = neto.round(3)
            out[f"{tipo.upper()}_{rec.upper()}_ang_deg"] = angulo(f, neto).round(1)

    os.makedirs(SALIDAS, exist_ok=True)
    res = os.path.join(SALIDAS, "tabla_fase.csv")
    out.to_csv(res, index=False)

    pd.set_option("display.width", 240)
    pd.set_option("display.max_columns", 40)
    print(out.to_string(index=False))
    print(f"\nGuardado en {res}")


if __name__ == "__main__":
    main()
