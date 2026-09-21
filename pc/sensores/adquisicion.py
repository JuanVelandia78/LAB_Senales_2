import os
import sys
import time

import serial
import numpy as np
import pandas as pd

sys.stdout.reconfigure(line_buffering=True, write_through=True)

PORT = "COM15"
BAUD = 921600
SEGUNDOS = 10.0

BAUDS_CANDIDATOS = [921600, 460800, 230400, 115200, 74880]

HERE = os.path.dirname(os.path.abspath(__file__))
CAPTURAS = os.path.join(HERE, "capturas")

CH = ["ax", "ay", "az", "gx", "gy", "gz", "encv"]


def probar_baud(puerto, baud):
    try:
        s = serial.Serial(puerto, baud, timeout=0.3)
    except serial.SerialException:
        return None
    time.sleep(0.3)
    s.reset_input_buffer()
    t0 = time.time()
    data = b""
    while time.time() - t0 < 0.7:
        chunk = s.read(4096)
        if chunk:
            data += chunk
        else:
            time.sleep(0.02)
    s.close()
    if not data:
        return None
    imprimibles = sum(1 for byte in data if 32 <= byte < 127 or byte in (9, 10, 13))
    return {
        "baud": baud,
        "bytes": len(data),
        "ratio": imprimibles / len(data),
        "comas": data.count(b","),
        "lineas": data.count(b"\n"),
    }


def detectar_baud(puerto):
    print(f"Detectando el baud real del ESP32 en {puerto} ...")
    resultados = []
    for b in BAUDS_CANDIDATOS:
        r = probar_baud(puerto, b)
        if r is None:
            print(f"  {b:>7} baud: sin datos")
            continue
        resultados.append(r)
        print(f"  {b:>7} baud: {r['bytes']:>6} bytes, "
              f"{r['ratio']*100:5.1f}% imprimible, "
              f"{r['comas']:>5} comas, {r['lineas']:>4} lineas")

    buenos = [r for r in resultados if r["ratio"] > 0.85 and r["comas"] > 5]
    if buenos:
        elegido = max(buenos, key=lambda r: r["comas"])
        print(f"-> Uso {elegido['baud']} baud.\n")
        return elegido["baud"]

    print("\nNingun baud tipico dio texto reconocible (todos con poco % "
          "imprimible o sin comas). Esto ya no es un problema de baud:")
    print("  - Verifica con 'idf.py -p " + puerto + " monitor' que el ESP32 "
          "esta corriendo el firmware (cierra este script antes).")
    print("  - Confirma en el Administrador de dispositivos que " + puerto +
          " es de verdad el ESP32 (CP210x/CH340), no otro dispositivo.")
    print("  - Revisa que el cable sea de datos y el ESP32 tenga alimentacion "
          "estable.")
    return None


def main():
    os.makedirs(CAPTURAS, exist_ok=True)

    nombre = input("Nombre de la captura (ej. reposo, giro): ").strip()
    if not nombre:
        nombre = time.strftime("captura_%H%M%S")
    if not nombre.endswith(".csv"):
        nombre += ".captura.csv"
    ruta = os.path.join(CAPTURAS, nombre)

    baud = detectar_baud(PORT)
    if baud is None:
        return
    if baud != BAUD:
        print(f"(nota: BAUD configurado arriba del archivo es {BAUD}; "
              f"se detecto {baud} y se usa ese para esta captura)")

    print(f"Abriendo {PORT} a {baud} baud ...")
    ser = serial.Serial(PORT, baud, timeout=0)
    print("Puerto abierto, esperando reinicio del ESP32 (2 s) ...")
    time.sleep(2)
    ser.reset_input_buffer()

    filas = []
    buffer = b""
    total_bytes = 0
    muestra = b""
    t0 = time.time()
    ultimo_reporte = t0
    print(f"Capturando {SEGUNDOS:.0f} s en {PORT} ...")
    while time.time() - t0 < SEGUNDOS:
        chunk = ser.read(4096)
        if chunk:
            total_bytes += len(chunk)
            if len(muestra) < 1000:
                muestra += chunk
            buffer += chunk
            while b"\n" in buffer:
                raw_line, buffer = buffer.split(b"\n", 1)
                line = raw_line.decode("ascii", errors="ignore").strip()
                if not line:
                    continue
                parts = line.split(",")
                if len(parts) == 17:
                    try:
                        filas.append([int(p) for p in parts])
                    except ValueError:
                        pass
        else:
            time.sleep(0.02)

        ahora = time.time()
        if ahora - ultimo_reporte >= 1.0:
            print(f"  ... {len(filas)} muestras validas, {total_bytes} bytes "
                  f"recibidos ({ahora - t0:.0f} s)")
            ultimo_reporte = ahora
    ser.close()

    if not filas:
        print(f"Se detecto {baud} baud pero durante la captura no llego "
              "ninguna linea de 17 campos validos.")
        print("----- muestra de lo recibido (primeros 1000 bytes) -----")
        print(muestra.decode("ascii", errors="replace"))
        print("----- fin de la muestra -----")
        return

    cols = ["n", "t_us"] + CH + [f"f_{c}" for c in CH] + ["overruns"]
    df = pd.DataFrame(filas, columns=cols).drop_duplicates("n").reset_index(drop=True)
    for c in CH:
        df[f"f_{c}"] = df[f"f_{c}"] / 1000.0

    dt = np.diff(df["t_us"].to_numpy())
    fs = 1e6 / np.median(dt)
    df["t_s"] = (df["t_us"] - df["t_us"].iloc[0]) / 1e6

    df.to_csv(ruta, index=False)
    print(f"{len(df)} muestras   fs~{fs:.2f} Hz   "
          f"overruns={int(df['overruns'].iloc[-1])}")
    print(f"Guardado en {ruta}")


if __name__ == "__main__":
    main()
