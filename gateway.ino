/* BERCO_GATEWAY.ino
   - recebe CoAP do berço ("alerta")
   - publica via MQTT "berco/sensor/som"
   - recebe MQTT "berco/atuador/comando" e manda CoAP "atuar" para o berço conhecido
*/

#include <WiFi.h>
#include <WiFiUdp.h>
#include "coap-simple.h"
#include <PubSubClient.h>

const char* ssid        = "PROJETO";
const char* password    = "amora123";
const char* mqtt_server = "172.20.10.4"; // IP do PC com mosquitto

// Tópicos
const char* topic_sensor = "berco/sensor/som";
const char* topic_atuador = "berco/atuador/comando";

WiFiUDP udp;
Coap coap(udp);
WiFiClient espClient;
PubSubClient client(espClient);

// Armazena IP do sensor quando ele manda mensagem pela primeira vez
IPAddress sensorIP; 
bool sensorConhecido = false;

// --- RECEBE COAP DO SENSOR ---
void callback_som(CoapPacket &packet, IPAddress ip, int port) {
  sensorIP = ip; // Salva IP para enviar comandos de volta
  sensorConhecido = true;
  
  char p[packet.payloadlen + 1];
  memcpy(p, packet.payload, packet.payloadlen);
  p[packet.payloadlen] = NULL;
  
  // Envia para MQTT
  client.publish(topic_sensor, p);
  // coap.sendResponse(ip, port, packet.messageid); // Opcional: Ack
}

// --- RECEBE MQTT DO SERVIDOR ---
void callback_mqtt(char* topic, byte* payload, unsigned int length) {
  String msg;
  for (int i = 0; i < length; i++) msg += (char)payload[i];
  
  if (String(topic) == topic_atuador && sensorConhecido) {
    // Repassa via CoAP para o sensor
    // Envia PUT para recurso "atuador" com "LIGAR" ou "DESLIGAR"
    coap.put(sensorIP, 5683, "atuador", msg.c_str());
  }
}

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) delay(500);
  Serial.println("Gateway Conectado");

  // Config CoAP Server
  coap.server(callback_som, "som");
  coap.start();

  // Config MQTT
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback_mqtt);
}

void reconnect() {
  while (!client.connected()) {
    if (client.connect("BercoGateway")) {
      client.subscribe(topic_atuador);
    } else {
      delay(5000);
    }
  }
}

void loop() {
  if (!client.connected()) reconnect();
  client.loop();
  coap.loop();
}
