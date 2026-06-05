#include "esp_camera.h"
#include <WiFi.h>
#include <PubSubClient.h>

const char* ssid        = "S24 de Franco";
const char* password    = "hola1234";
const char* mqtt_server = "10.108.139.2";
const int   mqtt_port   = 1883;

const char* TOPIC_FOTO    = "cam/foto";
const char* TOPIC_CAPTURA = "smarthome/equipo01/camara/captura";
const unsigned long INTERVALO = 3000;   // foto automatica cada 3s

// Pines AI-Thinker ESP32-CAM
#define PWDN_GPIO_NUM  32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM   0
#define SIOD_GPIO_NUM  26
#define SIOC_GPIO_NUM  27
#define Y9_GPIO_NUM    35
#define Y8_GPIO_NUM    34
#define Y7_GPIO_NUM    39
#define Y6_GPIO_NUM    36
#define Y5_GPIO_NUM    21
#define Y4_GPIO_NUM    19
#define Y3_GPIO_NUM    18
#define Y2_GPIO_NUM     5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM  23
#define PCLK_GPIO_NUM  22

WiFiClient   espClient;
PubSubClient mqtt(espClient);
unsigned long lastCapture = 0;

void capturarYPublicar(const char* motivo) {
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) { Serial.println("Fallo captura"); return; }
  bool ok = mqtt.publish(TOPIC_FOTO, fb->buf, fb->len, false);
  Serial.printf("Foto %s: %u bytes -> %s\n", motivo, fb->len, ok ? "OK" : "ERROR (muy grande?)");
  esp_camera_fb_return(fb);
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  if (String(topic) == TOPIC_CAPTURA) {
    Serial.println("Captura manual solicitada");
    capturarYPublicar("manual");
  }
}

void initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size   = FRAMESIZE_QVGA;   // 320x240, liviano para MQTT
  config.jpeg_quality = 15;
  config.fb_count     = 1;

  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println("Error al iniciar la camara");
    delay(2000);
    ESP.restart();
  }
  Serial.println("Camara OK");
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
    if (mqtt.connect("ESP32CAM-01")) {
      Serial.println("OK");
      mqtt.subscribe(TOPIC_CAPTURA);
    } else {
      Serial.print("error "); Serial.println(mqtt.state());
      delay(3000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  initCamera();
  connectWiFi();
  mqtt.setServer(mqtt_server, mqtt_port);
  mqtt.setCallback(mqttCallback);
  mqtt.setBufferSize(60000);   // imprescindible para enviar imagenes
  connectMQTT();
}

void loop() {
  if (!mqtt.connected()) connectMQTT();
  mqtt.loop();

  if (millis() - lastCapture >= INTERVALO) {
    lastCapture = millis();
    capturarYPublicar("timer");
  }
}