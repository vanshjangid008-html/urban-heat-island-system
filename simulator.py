#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>

#define DHTPIN D4
#define DHTTYPE DHT22
#define MQ135_PIN A0

const char* ssid = "MUNICIPAL_IOT_NET";
const char* password = "password123";
const char* mqtt_server = "://hivemq.com";

DHT dht(DHTPIN, DHTTYPE);
WiFiClient espClient;
PubSubClient client(espClient);

void setup() {
  Serial.begin(115200);
  dht.begin();
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { delay(200); }

  client.setServer(mqtt_server, 1883);
  if (client.connect("ESP8266_NODE_01")) {
    float t = dht.readTemperature();
    float h = dht.readHumidity();
    int aqi = analogRead(MQ135_PIN);

    if (!isnan(t) && !isnan(h)) {
      String payload = "{\"node_id\":\"NODE-01\",\"zone\":\"Downtown Core\",\"temperature\":" + String(t) +
                       ",\"humidity\":" + String(h) + ",\"aqi\":" + String(aqi) + "}";
      client.publish("metro/uhi/sensors/NODE-01", payload.c_str(), true);
    }
    client.disconnect();
  }
  ESP.deepSleep(30e6);
}

void loop() {}
