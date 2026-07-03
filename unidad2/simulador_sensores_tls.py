"""
Simulador del nodo de sensores ESP32 sobre MQTT con TLS + autenticacion.

Reemplaza temporalmente a la placa fisica: publica temperatura, humedad,
presion y nivel de audio a los mismos topicos y en el mismo formato JSON
que usaria el ESP32 real, pero conectandose al broker SEGURO (puerto 8883,
TLS, usuario/contrasena). Sirve para avanzar la Unidad 2 sin hardware.

Uso:
    pip install paho-mqtt
    python simulador_sensores_tls.py

Detener con Ctrl+C.
"""
import json
import time
import random
import ssl
import os
import paho.mqtt.client as mqtt

# ----------------- Configuracion -----------------
BROKER = "localhost"          # el broker esta publicado en localhost:8883
PORT = 8883
USER = "admin"                # usuario MQTT (admin = readwrite #). El ESP32 real usara "sensor"
PASSWORD = "admin123"         # la contrasena que fijaste con mosquitto_passwd
EQUIPO = "equipo01"
INTERVALO_S = 3               # cada cuantos segundos publica

# Ruta al certificado de la CA (esta en el repo, junto a mosquitto.conf)
CA_CERT = os.path.join(
    os.path.dirname(__file__), "..", "nodered-debian", "mosquitto", "ca.crt"
)

TOPIC_BASE = f"smarthome/{EQUIPO}"


def conectar():
    # API v2 de paho (>=2.0); si tienes la v1 cae al except
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="SIM-Sensores")
    except AttributeError:
        client = mqtt.Client(client_id="SIM-Sensores")

    client.username_pw_set(USER, PASSWORD)
    # TLS: confiamos en la CA autofirmada y desactivamos la verificacion de
    # hostname (el cert tiene CN=SmartHome, no coincide con "localhost").
    client.tls_set(ca_certs=CA_CERT, tls_version=ssl.PROTOCOL_TLSv1_2)
    client.tls_insecure_set(True)

    client.connect(BROKER, PORT, keepalive=60)
    return client


def main():
    client = conectar()
    client.loop_start()
    print(f"[OK] Conectado a {BROKER}:{PORT} (TLS) como '{USER}'. Publicando cada {INTERVALO_S}s...")

    # valores base que oscilan suavemente
    temp, hum, pres = 23.0, 55.0, 1013.0
    try:
        while True:
            temp = round(max(15, min(35, temp + random.uniform(-0.4, 0.5))), 1)
            hum = round(max(30, min(90, hum + random.uniform(-1, 1))), 1)
            pres = round(pres + random.uniform(-0.3, 0.3), 1)
            audio = random.randint(120, 700)  # nivel pico-a-pico del microfono

            datos = {
                f"{TOPIC_BASE}/temperatura": {"equipo": EQUIPO, "temperatura": temp},
                f"{TOPIC_BASE}/humedad": {"equipo": EQUIPO, "humedad": hum},
                f"{TOPIC_BASE}/presion": {"equipo": EQUIPO, "presion": pres},
                f"{TOPIC_BASE}/sensor_extra": {"equipo": EQUIPO, "sensor_extra": audio},
            }
            for topic, payload in datos.items():
                client.publish(topic, json.dumps(payload))

            print(f"T={temp}C  H={hum}%  P={pres}hPa  audio={audio}")
            time.sleep(INTERVALO_S)
    except KeyboardInterrupt:
        print("\nDetenido.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
