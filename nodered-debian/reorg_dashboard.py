"""
Reorganiza los widgets del dashboard en 3 grupos (columnas) en vez de uno solo.
Uso: python reorg_dashboard.py <ruta_flows.json>
"""
import json
import sys

path = sys.argv[1]

TAB = "9b04c3fa896638e7"   # tab "IoT Dashboard"
AMB = "0502ac853b514fa6"   # grupo existente -> se renombra a "Ambiente"
CAM = "grpCamara"
CTL = "grpControl"

# widget id -> (grupo destino, orden dentro del grupo)
mapping = {
    # Ambiente
    "d3d68a440ce5dcb8": (AMB, 1),   # Temperatura
    "0b85d799066fd1a6": (AMB, 2),   # Humedad
    "ac1d7a83c02d16d1": (AMB, 3),   # Presion
    "6638de5483e796ac": (AMB, 4),   # Nivel de audio
    "dbChart":          (AMB, 5),   # Grafico temperatura
    # Camara
    "58a559c4b59b3dad": (CAM, 1),   # imagen
    "7d80d6aa8b67d42f": (CAM, 2),   # Persona Detectada (coco)
    "f1txt01":          (CAM, 3),   # Persona identificada (facial)
    "dbCapBtn":         (CAM, 4),   # boton Capturar imagen
    # Control y estado
    "dbStTxt":          (CTL, 1),   # Estado del sistema
    "1c6b9304f2752925": (CTL, 2),   # Alerta
    "db57eaab1e9e4a78": (CTL, 3),   # Alerta
    "dbLedSwitch":      (CTL, 4),   # LED manual
    "dbLedTxt":         (CTL, 5),   # Estado LED
}

with open(path, "r", encoding="utf-8") as f:
    flows = json.load(f)

# renombrar grupo existente
for n in flows:
    if n.get("id") == AMB:
        n["name"] = "Ambiente"
        n["order"] = 1
        n["width"] = 6

# quitar grupos nuevos si ya existen (idempotente)
flows = [n for n in flows if n.get("id") not in (CAM, CTL)]


def grupo(gid, name, order):
    return {"id": gid, "type": "ui_group", "name": name, "tab": TAB,
            "order": order, "disp": True, "width": 6, "collapse": False, "className": ""}


flows.append(grupo(CAM, "Cámara", 2))
flows.append(grupo(CTL, "Control y estado", 3))

# reasignar widgets
for n in flows:
    if n.get("id") in mapping:
        g, o = mapping[n["id"]]
        n["group"] = g
        n["order"] = o

with open(path, "w", encoding="utf-8") as f:
    json.dump(flows, f, ensure_ascii=False)

print("Reorganizado: grupos Ambiente / Cámara / Control y estado")