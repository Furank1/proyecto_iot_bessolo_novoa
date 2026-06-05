# Node-RED sobre Debian 12 (bookworm) => glibc, compatible con TensorFlow.js
FROM node:20-bookworm

# Directorios de la app y de datos (userDir)
RUN mkdir -p /usr/src/node-red /data && \
    chown -R node:node /usr/src/node-red /data

WORKDIR /usr/src/node-red

# Instala Node-RED + dashboard + coco-ssd.
# Al ser glibc, @tensorflow/tfjs-node carga libtensorflow.so.2 sin errores.
COPY package.json .
RUN npm install --unsafe-perm --no-update-notifier --no-fund --omit=dev

USER node

EXPOSE 1880

# userDir = /data (volumen con los flows)
CMD ["./node_modules/.bin/node-red", "--userDir", "/data"]
