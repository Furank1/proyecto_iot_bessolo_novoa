/*
 * Nodo de sensores ESP32 - SmartHome IoT (Unidad 2: MQTT con TLS + autenticacion)
 * Placa: ESP32 Dev Module
 * Sensores: BME280 (I2C 0x76) + microfono MAX4466 (GPIO34) + LED (GPIO25)
 *
 * ANTES DE SUBIR, edita las 4 lineas de CONFIGURACION mas abajo:
 *   ssid, password        -> tu red WiFi
 *   mqtt_server           -> IP del PC (ipconfig -> adaptador Wi-Fi -> IPv4)
 *   mqtt_pass             -> contrasena del usuario "sensor" (la de mosquitto_passwd)
 */
#include <Wire.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <Adafruit_BME280.h>

// ===================== CONFIGURACION =====================
const char* ssid        = "S24 de Franco";      // <-- tu red WiFi
const char* password    = "hola1234";       // <-- clave WiFi
const char* mqtt_server = "10.190.215.2";// <-- IP del PC (ipconfig)
const int   mqtt_port   = 8883;               // TLS
const char* mqtt_user   = "sensor";           // usuario MQTT
const char* mqtt_pass   = "sensor123";  // <-- contrasena del usuario sensor
// ========================================================

const char* TOPIC_TEMP   = "smarthome/equipo01/temperatura";
const char* TOPIC_HUM    = "smarthome/equipo01/humedad";
const char* TOPIC_PRES   = "smarthome/equipo01/presion";
const char* TOPIC_AUDIO  = "smarthome/equipo01/sensor_extra";
const char* TOPIC_ALERTA = "smarthome/equipo01/alerta";
const char* TOPIC_LED    = "smarthome/equipo01/control/led";

const int MIC_PIN = 34;
const int LED_PIN = 25;
const unsigned long SAMPLE_MS  = 50;
const unsigned long PUBLISH_MS = 2000;
const unsigned long LED_MS     = 3000;

Adafruit_BME280   bme;
WiFiClientSecure  espClient;          // <-- cliente con TLS
PubSubClient      mqtt(espClient);
unsigned long     lastPublish = 0;
unsigned long     ledStart    = 0;
bool              ledAlerta   = false;
bool              ledManual   = false;

void aplicarLed() {
  digitalWrite(LED_PIN, (ledManual || ledAlerta) ? HIGH : LOW);
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String t = String(topic);
  String msg = "";
  for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];

  if (t == TOPIC_ALERTA) {
    ledAlerta = true;
    ledStart  = millis();
  } else if (t == TOPIC_LED) {
    ledManual = (msg == "on");
  }
  aplicarLed();
}

void connectWiFi() {
  WiFi.begin(ssid, password);
  Serial.print("WiFi");
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println(" OK -> " + WiFi.localIP().toString());
}

void connectMQTT() {
  while (!mqtt.connected()) {
    Serial.print("MQTT...");
    if (mqtt.connect("ESP32-Sensores", mqtt_user, mqtt_pass)) {
      Serial.println("OK");
      mqtt.subscribe(TOPIC_ALERTA);
      mqtt.subscribe(TOPIC_LED);
    } else {
      Serial.print("error rc="); Serial.println(mqtt.state());
      delay(3000);
    }
  }
}

uint16_t readPeakToPeak() {
  unsigned long t = millis();
  uint16_t vMax = 0, vMin = 4095;
  while (millis() - t < SAMPLE_MS) {
    uint16_t s = analogRead(MIC_PIN);
    if (s > vMax) vMax = s;
    if (s < vMin) vMin = s;
  }
  return vMax - vMin;
}

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  Wire.begin(21, 22);

  if (!bme.begin(0x76)) {
    Serial.println("ERROR BME280 (revisa SDA/SCL/VIN/GND)");
    while (1);
  }

  connectWiFi();
  espClient.setInsecure();               // TLS sin validar el certificado autofirmado
  mqtt.setServer(mqtt_server, mqtt_port);
  mqtt.setCallback(mqttCallback);
  connectMQTT();
}

void loop() {
  if (!mqtt.connected()) connectMQTT();
  mqtt.loop();

  if (ledAlerta && millis() - ledStart >= LED_MS) {
    ledAlerta = false;
    aplicarLed();
  }

  if (millis() - lastPublish >= PUBLISH_MS) {
    lastPublish = millis();

    uint16_t pp = readPeakToPeak();
    char audioPayload[64];
    snprintf(audioPayload, sizeof(audioPayload),
             "{\"equipo\":\"equipo01\",\"sensor_extra\":%d}", pp);
    mqtt.publish(TOPIC_AUDIO, audioPayload);

    float temp = bme.readTemperature();
    float pres = bme.readPressure() / 100.0f;
    float hum  = bme.readHumidity();

    char tPayload[64], hPayload[64], pPayload[64];
    snprintf(tPayload, sizeof(tPayload), "{\"equipo\":\"equipo01\",\"temperatura\":%.1f}", temp);
    snprintf(hPayload, sizeof(hPayload), "{\"equipo\":\"equipo01\",\"humedad\":%.1f}", hum);
    snprintf(pPayload, sizeof(pPayload), "{\"equipo\":\"equipo01\",\"presion\":%.1f}", pres);

    mqtt.publish(TOPIC_TEMP, tPayload);
    mqtt.publish(TOPIC_HUM,  hPayload);
    mqtt.publish(TOPIC_PRES, pPayload);

    Serial.println(tPayload);
  }
}
