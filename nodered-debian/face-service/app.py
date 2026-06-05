"""
Servicio de reconocimiento facial con face_recognition (dlib).

Carga las caras conocidas desde la carpeta known_faces/ (cada archivo
es una persona; el nombre del archivo es la etiqueta, ej: franco.jpg -> "franco").

Expone:
  POST /identify  -> recibe una imagen JPEG (body binario), devuelve el nombre
  POST /reload    -> recarga las caras conocidas sin reiniciar
  GET  /health    -> estado y lista de personas cargadas
"""
import os
import io
import face_recognition
import numpy as np
from flask import Flask, request, jsonify
from PIL import Image

app = Flask(__name__)

KNOWN_DIR = "known_faces"
TOLERANCIA = 0.6  # menor = más estricto. 0.6 es el valor recomendado por la librería.

known_encodings = []
known_names = []


def load_known_faces():
    known_encodings.clear()
    known_names.clear()
    if not os.path.isdir(KNOWN_DIR):
        print(f"[WARN] No existe la carpeta {KNOWN_DIR}")
        return
    for fname in sorted(os.listdir(KNOWN_DIR)):
        if fname.lower().endswith((".jpg", ".jpeg", ".png")):
            path = os.path.join(KNOWN_DIR, fname)
            img = face_recognition.load_image_file(path)
            encs = face_recognition.face_encodings(img)
            if encs:
                known_encodings.append(encs[0])
                known_names.append(os.path.splitext(fname)[0])
                print(f"[OK] Cara cargada: {known_names[-1]}")
            else:
                print(f"[WARN] No se detectó cara en {fname}")
    print(f"[INFO] Total caras conocidas: {len(known_names)}")


@app.route("/identify", methods=["POST"])
def identify():
    if not request.data:
        return jsonify({"error": "sin imagen"}), 400

    img = Image.open(io.BytesIO(request.data)).convert("RGB")
    frame = np.array(img)

    locations = face_recognition.face_locations(frame)
    encodings = face_recognition.face_encodings(frame, locations)

    if not encodings:
        return jsonify({"persona": False, "nombre": "sin_cara", "confianza": 0})

    enc = encodings[0]

    if not known_encodings:
        return jsonify({"persona": True, "nombre": "desconocido", "confianza": 0})

    distances = face_recognition.face_distance(known_encodings, enc)
    best = int(np.argmin(distances))

    if distances[best] < TOLERANCIA:
        nombre = known_names[best]
        confianza = round((1 - float(distances[best])) * 100)
    else:
        nombre = "desconocido"
        confianza = 0

    return jsonify({"persona": True, "nombre": nombre, "confianza": confianza})


@app.route("/reload", methods=["POST"])
def reload_faces():
    load_known_faces()
    return jsonify({"cargadas": known_names})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "conocidas": known_names})


if __name__ == "__main__":
    load_known_faces()
    app.run(host="0.0.0.0", port=5000)
