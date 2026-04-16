#include <WiFi.h>
#include <WiFiUdp.h>
#include <coap-simple.h> // Instalar via Library Manager: "CoapSimple"
#include <Adafruit_NeoPixel.h>
#include "DFRobotDFPlayerMini.h"
#include <ESP32Servo.h>

// ============================================================
// 1. CONFIGURAÇÕES DE REDE 
// ============================================================
const char* ssid     = "PROJETO";
const char* password = "amora123";

// !!! IMPORTANTE: Coloque aqui o IP do ESP32 Gateway !!!
IPAddress gatewayIP(172, 20, 10, 5);

// ============================================================
// 2. HARDWARE E PINOS
// ============================================================
const int PINO_SENSOR = 34;
const int PINO_LED    = 19;
const int PINO_SERVO  = 23;
const int NUM_LEDS    = 12;

// ============================================================
// 3. OBJETOS
// ============================================================
WiFiUDP udp;
Coap coap(udp);
Adafruit_NeoPixel pixels(NUM_LEDS, PINO_LED, NEO_GRB + NEO_KHZ800);
HardwareSerial minhaSerial(2);
DFRobotDFPlayerMini meuMP3;
Servo meuServo;

// ============================================================
// 4. VARIÁVEIS GLOBAIS
// ============================================================
bool modoShowAtivo = false;

// Variáveis do Servo
int posServo = 0;
int direcaoServo = 1;
unsigned long ultimaMovimentacaoServo = 0;

// Variáveis dos LEDs
uint16_t j = 0;
unsigned long ultimaAtualizacaoCor = 0;
unsigned long timerFlashBranco = 0;

// Timer para envio de dados
unsigned long ultimoEnvioCoap = 0;

// ============================================================
// 5. FUNÇÕES AUXILIARES (Hardware)
// ============================================================

// Comandos diretos em Hex para garantir funcionamento do MP3
void tocarMusicaSegura() {
  byte comando[10] = {0x7E, 0xFF, 0x06, 0x03, 0x00, 0x00, 0x01, 0xFE, 0xF7, 0xEF};
  minhaSerial.write(comando, 10);
}

void pausarMusicaSegura() {
  byte comando[10] = {0x7E, 0xFF, 0x06, 0x0E, 0x00, 0x00, 0x00, 0xFE, 0xED, 0xEF};
  minhaSerial.write(comando, 10);
}

// Função de Arco-Íris para LED
uint32_t Roda(byte WheelPos) {
  WheelPos = 255 - WheelPos;
  if(WheelPos < 85) return pixels.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  if(WheelPos < 170) { WheelPos -= 85; return pixels.Color(0, WheelPos * 3, 255 - WheelPos * 3); }
  WheelPos -= 170; return pixels.Color(WheelPos * 3, 255 - WheelPos * 3, 0);
}

void arcoIrisGiratorio() {
  if (millis() - ultimaAtualizacaoCor < 30) return;
  ultimaAtualizacaoCor = millis();
  
  j = (j + 1) & 255;
  for(int i=0; i<pixels.numPixels(); i++) {
    pixels.setPixelColor(i, Roda((i * 256 / pixels.numPixels()) + j));
  }
  if (millis() - timerFlashBranco < 150) {
      pixels.setPixelColor(0, pixels.Color(150, 150, 150));
      pixels.setPixelColor(1, pixels.Color(150, 150, 150));
  }
  pixels.show();
}

// ============================================================
// Movimento do servo restrito (6h ↔ 9h)
// ============================================================
void balancarBerco() {
  if (millis() - ultimaMovimentacaoServo < 10) return;
  ultimaMovimentacaoServo = millis();

  posServo += direcaoServo;

  if (posServo >= 115) direcaoServo = -1; // 9h
  if (posServo <= 65)  direcaoServo = 1;  // 6h

  meuServo.write(posServo);
}

// ============================================================
// 6. CALLBACK COAP (Recebe comandos do Gateway)
// ============================================================
void callback_atuador(CoapPacket &packet, IPAddress ip, int port) {
  char p[packet.payloadlen + 1];
  memcpy(p, packet.payload, packet.payloadlen);
  p[packet.payloadlen] = NULL;
  String mensagem(p);

  Serial.print("[COAP] Comando recebido: ");
  Serial.println(mensagem);

  if (mensagem == "LIGAR") {
    if (!modoShowAtivo) {
      Serial.println(">>> ATIVANDO BERÇO <<<");
      modoShowAtivo = true;
      timerFlashBranco = millis();

      tocarMusicaSegura();

      meuServo.attach(PINO_SERVO, 500, 2400);

      // =====================================================
      // 🔧 ALTERAÇÃO IMPORTANTE → começa em 9h (115)
      // =====================================================
      posServo = 115;
      direcaoServo = -1;
    }
  }
  else if (mensagem == "DESLIGAR") {
    if (modoShowAtivo) {
      Serial.println(">>> DESLIGANDO BERÇO <<<");
      modoShowAtivo = false;

      pausarMusicaSegura();

      if (meuServo.attached()) {
         meuServo.detach();
      }

      pixels.clear();
      pixels.show();
    }
  }

  coap.sendResponse(ip, port, packet.messageid);
}

// ============================================================
// 7. SETUP
// ============================================================
void setup() {
  Serial.begin(115200);

  Serial.print("Conectando WiFi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Conectado!");
  Serial.print("IP do Sensor: ");
  Serial.println(WiFi.localIP());

  meuServo.setPeriodHertz(50);

  pixels.begin();
  pixels.setBrightness(20);
  pixels.clear(); pixels.show();

  minhaSerial.begin(9600, SERIAL_8N1, 16, 17);
  if (meuMP3.begin(minhaSerial)) {
    Serial.println(F("MP3 OK. Volume 20."));
    meuMP3.volume(20);
  } else {
    Serial.println(F("MP3: Falha na conexão (cabeamento?)"));
  }

  coap.server(callback_atuador, "atuador");
  coap.start();
  Serial.println("Servidor CoAP iniciado. Aguardando comandos...");
}

// ============================================================
// 8. LOOP PRINCIPAL
// ============================================================
void loop() {
  coap.loop();

  int max_v = 0;
  int min_v = 4095;
  unsigned long inicioLeitura = millis();
  
  while (millis() - inicioLeitura < 50) {
    int v = analogRead(PINO_SENSOR);
    if (v > 0 && v < 4095) {
      if (v > max_v) max_v = v;
      if (v < min_v) min_v = v;
    }
  }
  int amplitude = max_v - min_v;

  if (millis() - ultimoEnvioCoap > 200) {
    ultimoEnvioCoap = millis();
    
    char buff[10];
    itoa(amplitude, buff, 10);
    coap.put(gatewayIP, 5683, "som", buff);
  }

  if (modoShowAtivo) {
    arcoIrisGiratorio();
    balancarBerco();
  }
}

