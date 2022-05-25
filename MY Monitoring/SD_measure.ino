#include <SPI.h>
#include <SD.h>

#include <SDS011.h>
#include <DFRobot_DHT20.h>

#include <Wire.h>
#include "RTClib.h"
#include "time.h"

#include "secrets.h"
#include <WiFiClientSecure.h>
#include "WiFi.h"
#include <MQTTClient.h>
#include <ArduinoJson.h>

#define AWS_IOT_PUBLISH_TOPIC   "esp32/pub"

// SD CARD BREAKOUT PINS
// CS: D3
// SCK: SCK
// MOSI: MO
// MISO: MI
// VCC: VCC (5V)
// GND: GND

File csv;

SDS011 sds;
DFRobot_DHT20 dht20;

RTC_DS3231 rtc;

WiFiClientSecure net = WiFiClientSecure();
MQTTClient client = MQTTClient(256);

const int INTERRUPT_PIN = 39;
volatile bool buttonState = 0;

unsigned long interval = 30; // 30000 = 30s
int recordsPerFile = 1024; //2880 30s intervals in a day OR 512 bytes in an SD sub-block (20 full messages)
int count = 0;
int error, idx;
float p10, p25, temp, rh;
unsigned long epochTime, writeTime, startTime;

void connectAWS(int idx) {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.println("Connecting to Wi-Fi");
  unsigned long initTime = rtc.now().unixtime();
  while ((WiFi.status() != WL_CONNECTED) && (rtc.now().unixtime() < initTime + 20)) {
    delay(100);
    Serial.print(".");
  }
  if (WiFi.status() != WL_CONNECTED) {return;}

  net.setCACert(AWS_CERT_CA);
  net.setCertificate(AWS_CERT_CRT);
  net.setPrivateKey(AWS_CERT_PRIVATE);

  client.begin(AWS_IOT_ENDPOINT, 8883, net);

  Serial.println("Connecting to AWS IOT");
  initTime = rtc.now().unixtime();
  while ((!client.connect(THINGNAME)) && (rtc.now().unixtime() < initTime + 10)) {
    delay(100);
    Serial.print(".");
  }
  if (!client.connected()) {return;}

  StaticJsonDocument<512> doc;
  doc["files"] = idx;
  char jsonBuffer[512];
  serializeJson(doc, jsonBuffer);
  client.publish(AWS_IOT_PUBLISH_TOPIC, jsonBuffer);
}

void setup() {
  Serial.begin(115200);
  sds.begin(16, 17);

  pinMode(INTERRUPT_PIN, INPUT);
  attachInterrupt(INTERRUPT_PIN, buttonPress, RISING);

  delay(1000);

  while (!rtc.begin()) {
    delay(500);
    Serial.print(".");
  }

  while (!SD.begin(26)) {
    delay(100);
  }

  uint8_t cardType = SD.cardType();
  if(cardType == CARD_NONE) {
    return;
  }

  idx = 1;
  while(SD.exists("/Record"+String(idx)+".csv")) {
    idx++;
  }

  csv = SD.open("/Record"+String(idx)+".csv", FILE_WRITE);
  if(!csv) {
    return;
  }

  Serial.println("File /Record"+String(idx)+".csv opened.");
  csv.println("Time, PM2.5, PM10, Temperature, Relative Humidity");
//  connectAWS(0);

  startTime = rtc.now().unixtime() - interval;
}

void loop() {
  DateTime now = rtc.now();
  epochTime = now.unixtime();
  
  if (epochTime >= startTime + interval) {
    startTime = rtc.now().unixtime();
    dht20.begin();
    
    error = 1;
    while (error) {
      error = sds.read(&p25,&p10);
    }

    writeTime = rtc.now().unixtime();
    temp = dht20.getTemperature();
    rh = dht20.getHumidity();

    Serial.println(writeTime);
    // each entry is 5 * 5 = 25 bytes
    csv.println(String(writeTime)+","+String(p25)+","+String(p10)+","+String(temp)+","+String(rh));
    count++;

    if (count >= recordsPerFile or buttonState) { 
      csv.close();
//      connectAWS(idx);
      Serial.println("Closing file "+String(idx));
      
      count = 0;
      buttonState = 0;
      idx++;
      csv = SD.open("/Record"+String(idx)+".csv", FILE_WRITE);
    }
  }
}

void buttonPress() {
  buttonState = 1;
}
