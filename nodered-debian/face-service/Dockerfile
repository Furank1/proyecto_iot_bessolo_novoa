# Servicio de reconocimiento facial (face_recognition / dlib)
FROM python:3.11-slim

# Dependencias de compilación de dlib + librerías de imagen
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libjpeg-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala dependencias Python (compila dlib — tarda varios minutos)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
RUN mkdir -p known_faces

EXPOSE 5000
CMD ["python", "app.py"]
