#include <SPI.h>
#include <SD.h>
#include <stdio.h>

#include <SDS011.h>
#include <DFRobot_DHT20.h>

#include <Wire.h>

#include <SoftwareSerial.h>
#include <TinyGPSPlus.h>

int RXPin = 4;
int TXPin = 12;
unsigned long interval = 2500; // 30000 = 30s
int recordsPerFile = 30; //30 corresponds to saving every 1.25 mins
int count = 0;
int idx2 = 0;
int error, idx;
int LEDPin = 13;
float p10, p25, temp, rh;
double lat, lng, alt;
unsigned long epochTime, startTime;
char writeTime[8];
int GPSBaud = 9600;

File csv;

SDS011 sds;
DFRobot_DHT20 dht20;

TinyGPSPlus gps;
SoftwareSerial gpsSerial(RXPin, TXPin);

static void smartDelay(unsigned long ms) {
  unsigned long start = millis();
  do {
    while (gpsSerial.available())
      gps.encode(gpsSerial.read());
  } while (millis() - start < ms);
}

void setup() {
  Serial.begin(115200);
  gpsSerial.begin(GPSBaud);
  sds.begin(16, 17);

  pinMode(LEDPin, OUTPUT);
  digitalWrite(LEDPin, HIGH);

  while (!gps.location.isValid() and count < 90) {
    Serial.println("Error reading GPS.");
    count++;
    smartDelay(1000);
  }
  count = 0;

  while (!SD.begin(26)) {
    Serial.println("Error reading SD.");
    smartDelay(100);
  }

  idx = 1;
  while(SD.exists("/Journey "+String(idx)+"_0.csv")) {
    idx++;
  }
  csv = SD.open("/Journey "+String(idx)+"_0.csv", FILE_WRITE);
  csv.println("WriteTime,1000Lat,1000Lng,Alt,PM2.5,PM10,Temp,RH");
  csv.println(String(gps.date.day())+"/"+String(gps.date.month())+"/"+String(gps.date.year()));

  Serial.println("Successfully opened file. Commencing monitoring.");
  digitalWrite(LEDPin, LOW);
}

void loop() {
  digitalWrite(LEDPin, LOW);
  smartDelay(interval);

  lat = gps.location.lat();
  lng = gps.location.lng();
  alt = gps.altitude.meters();

  sprintf(writeTime, "%02d:%02d:%02d", gps.time.hour(), gps.time.minute(), gps.time.second());
  csv.print(writeTime);
  csv.print(","+String(1000*lat)+","+String(1000*lng)+","+String(alt)+",");

  dht20.begin();
  error = 1;
  while (error) {
    error = sds.read(&p25,&p10);
  }

  temp = dht20.getTemperature();
  rh = dht20.getHumidity();

  csv.println(String(p25)+","+String(p10)+","+String(temp)+","+String(rh));
  count++;

  if (count >= recordsPerFile) { 
    csv.close();
    
    count = 0;
    idx2++;
    csv = SD.open("/Journey "+String(idx)+"_"+String(idx2)+".csv", FILE_WRITE);

  }
}
