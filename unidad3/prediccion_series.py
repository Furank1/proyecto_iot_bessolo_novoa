"""
Unidad 3 - Prediccion de series de tiempo (SmartHome IoT).

Cada 10 minutos (modo --loop) o una sola vez (por defecto):
  1. Consulta el historial reciente (hasta 6 h) de temperatura y nivel de
     audio desde InfluxDB con una consulta Flux.
  2. Calcula una proyeccion a 30 minutos con regresion lineal
     (numpy.polyfit de grado 1) sobre los ultimos puntos.
  3. Publica la prediccion en el broker MQTT (TLS 8883):
        smarthome/equipo01/prediccion/temperatura -> {"valor": X, "horizon_min": 30}
        smarthome/equipo01/prediccion/audio       -> {"valor": X, "horizon_min": 30}
  4. Si la proyeccion cruza el umbral dentro de los proximos 30 min,
     publica una alerta preventiva en smarthome/equipo01/alerta
     con {"tipo": "preventiva", ...}.
  5. Escribe la prediccion en InfluxDB con timestamp FUTURO (measurement
     "prediccion"), para poder superponerla con el valor real en Grafana.

Nota: el proyecto no tiene sensor de gas; el equivalente adaptado es el
nivel de audio (sensor_extra), como en las unidades anteriores.

Uso:
    pip install numpy paho-mqtt
    python prediccion_series.py           # una corrida
    python prediccion_series.py --loop    # corre cada 10 minutos
"""
import json
import os
import ssl
import sys
import time
import urllib.request

import numpy as np
import paho.mqtt.client as mqtt

# ----------------- Configuracion -----------------
INFLUX_URL = "http://localhost:8086"
INFLUX_ORG = "smarthome"
INFLUX_BUCKET = "sensores"

MQTT_HOST = "localhost"
MQTT_PORT = 8883
MQTT_USER = "admin"
MQTT_PASS = "admin123"

EQUIPO = "equipo01"
HORIZONTE_MIN = 30          # proyeccion a 30 minutos
VENTANA_HORAS = 6           # historial maximo consultado
MIN_PUNTOS = 5              # minimo de puntos para ajustar la recta
INTERVALO_LOOP_S = 600      # 10 minutos

# variable -> umbral para la alerta preventiva
VARIABLES = {
    "temperatura": 30.0,
    "audio": 500.0,
}

RAIZ = os.path.dirname(os.path.abspath(__file__))
CA_CERT = os.path.join(RAIZ, "..", "nodered-debian", "mosquitto", "ca.crt")


def token_influx():
    """Lee INFLUXDB_TOKEN del entorno o del .env de nodered-debian."""
    tok = os.environ.get("INFLUXDB_TOKEN")
    if tok:
        return tok
    env_path = os.path.join(RAIZ, "..", "nodered-debian", ".env")
    with open(env_path, encoding="utf-8") as f:
        for linea in f:
            if linea.startswith("INFLUXDB_TOKEN="):
                return linea.split("=", 1)[1].strip()
    raise RuntimeError("No se encontro INFLUXDB_TOKEN (entorno o .env)")


def consultar_serie(token, campo):
    """Devuelve la serie [(epoch_s, valor), ...] de las ultimas VENTANA_HORAS."""
    flux = (
        f'from(bucket:"{INFLUX_BUCKET}") '
        f"|> range(start:-{VENTANA_HORAS}h) "
        f'|> filter(fn:(r)=> r._measurement == "sensores" and r._field == "{campo}") '
        "|> aggregateWindow(every: 1m, fn: mean, createEmpty: false)"
    )
    req = urllib.request.Request(
        f"{INFLUX_URL}/api/v2/query?org={INFLUX_ORG}",
        data=flux.encode(),
        headers={
            "Authorization": f"Token {token}",
            "Content-Type": "application/vnd.flux",
            "Accept": "application/csv",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        cuerpo = r.read().decode()

    serie = []
    columnas = None
    for linea in cuerpo.splitlines():
        celdas = linea.split(",")
        if "_time" in celdas:
            columnas = {nombre: i for i, nombre in enumerate(celdas)}
            continue
        if not columnas or len(celdas) < len(columnas) or not linea.startswith(","):
            continue
        try:
            ts = celdas[columnas["_time"]]
            valor = float(celdas[columnas["_value"]])
        except (KeyError, ValueError, IndexError):
            continue
        epoch = time.mktime(time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone
        serie.append((epoch, valor))
    return serie


def proyectar(serie):
    """Regresion lineal sobre los ultimos 20 puntos; devuelve el valor a +30 min."""
    puntos = serie[-20:]
    if len(puntos) < MIN_PUNTOS:
        return None
    xs = np.array([p[0] for p in puntos])
    ys = np.array([p[1] for p in puntos])
    x0 = xs[0]
    pendiente, intercepto = np.polyfit(xs - x0, ys, 1)
    x_futuro = (xs[-1] - x0) + HORIZONTE_MIN * 60
    return float(pendiente * x_futuro + intercepto)


def escribir_prediccion(token, campo, valor, ts_futuro_ms):
    """Guarda la prediccion en InfluxDB con timestamp futuro (para Grafana)."""
    linea = f"prediccion,equipo={EQUIPO} {campo}={valor} {ts_futuro_ms}"
    req = urllib.request.Request(
        f"{INFLUX_URL}/api/v2/write?org={INFLUX_ORG}&bucket={INFLUX_BUCKET}&precision=ms",
        data=linea.encode(),
        headers={"Authorization": f"Token {token}", "Content-Type": "text/plain"},
    )
    urllib.request.urlopen(req, timeout=10).read()


def conectar_mqtt():
    try:
        cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="SIM-Prediccion")
    except AttributeError:
        cliente = mqtt.Client(client_id="SIM-Prediccion")
    cliente.username_pw_set(MQTT_USER, MQTT_PASS)
    cliente.tls_set(ca_certs=CA_CERT, tls_version=ssl.PROTOCOL_TLSv1_2)
    cliente.tls_insecure_set(True)  # cert autofirmado con CN=SmartHome
    cliente.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
    cliente.loop_start()
    return cliente


def ciclo():
    token = token_influx()
    cliente = conectar_mqtt()
    ts_futuro_ms = int((time.time() + HORIZONTE_MIN * 60) * 1000)

    for campo, umbral in VARIABLES.items():
        serie = consultar_serie(token, campo)
        if not serie:
            print(f"[{campo}] sin datos en InfluxDB, se omite")
            continue
        pred = proyectar(serie)
        if pred is None:
            print(f"[{campo}] datos insuficientes ({len(serie)} puntos)")
            continue
        pred = round(pred, 1)
        actual = round(serie[-1][1], 1)

        topico = f"smarthome/{EQUIPO}/prediccion/{campo}"
        cliente.publish(topico, json.dumps({"valor": pred, "horizon_min": HORIZONTE_MIN}))
        escribir_prediccion(token, campo, pred, ts_futuro_ms)
        print(f"[{campo}] actual={actual}  prediccion(+{HORIZONTE_MIN}min)={pred}  umbral={umbral}")

        if pred > umbral >= actual:
            alerta = {
                "tipo": "preventiva",
                "mensaje": (
                    f"Prediccion: {campo} alcanzaria {pred} "
                    f"(umbral {umbral}) en menos de {HORIZONTE_MIN} min"
                ),
            }
            cliente.publish(f"smarthome/{EQUIPO}/alerta", json.dumps(alerta))
            print(f"[{campo}] ALERTA PREVENTIVA publicada: {alerta['mensaje']}")

    cliente.loop_stop()
    cliente.disconnect()


def main():
    if "--loop" in sys.argv:
        print(f"Modo continuo: una prediccion cada {INTERVALO_LOOP_S // 60} min (Ctrl+C para salir)")
        while True:
            try:
                ciclo()
            except Exception as e:  # noqa: BLE001 - no botar el loop por un fallo puntual
                print("Error en el ciclo:", e)
            time.sleep(INTERVALO_LOOP_S)
    else:
        ciclo()


if __name__ == "__main__":
    main()
