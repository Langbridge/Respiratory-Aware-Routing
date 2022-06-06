/**
 * sd_measure
 *     Long-term monitoring script to record PM2.5 and PM10 concentrations, temp and humidity to an SD card.
 *     Includes interrupt functionality attached to pin 39 for emergency saving.
 * 
 * @author Abi Langbridge
 * @version 2.0 6/2/22
 */

#include <SPI.h>
#include <SD.h>

#include <SDS011.h>
#include <DFRobot_DHT20.h>

#include <Wire.h>
#include "RTClib.h"
#include "time.h"

#include <ArduinoJson.h>

#define AWS_IOT_PUBLISH_TOPIC   "esp32/pub"

// SD CARD BREAKOUT PINS
// CS: D3
// SCK: SCK
// MOSI: MO
// MISO: MI
// VCC: VCC (5V)
// GND: GND

// initialise csv file
File csv;

// initialise sensors + RTC
SDS011 sds;
DFRobot_DHT20 dht20;
RTC_DS3231 rtc;

// initialise interrupt pin and button states
const int INTERRUPT_PIN = 39;
volatile bool buttonState = 0;

// initialise variables
unsigned long interval = 30; // 30000 = 30s
int recordsPerFile = 1024; //2880 30s intervals in a day OR 512 bytes in an SD sub-block (20 full messages)
int count = 0;
int error, idx;
float p10, p25, temp, rh;
unsigned long epochTime, writeTime, startTime;

void setup() {
  // initialise serial connection with serial display and the SDS011
  Serial.begin(115200);
  sds.begin(16, 17);

  // attach the interrupt
  pinMode(INTERRUPT_PIN, INPUT);
  attachInterrupt(INTERRUPT_PIN, buttonPress, RISING);

  // wait for serial to open
  delay(1000);

  // wait for RTC to initialise
  while (!rtc.begin()) {
    delay(500);
    Serial.print(".");
  }

  // wait for SD card to initialise
  while (!SD.begin(26)) {
    delay(100);
  }

  // check that SD card is mounted correctly
  uint8_t cardType = SD.cardType();
  if(cardType == CARD_NONE) {
    return;
  }

  // check what files already exist on the SD card
  idx = 1;
  while(SD.exists("/Record"+String(idx)+".csv")) {
    idx++;
  }

  // open the first non-existent file
  csv = SD.open("/Record"+String(idx)+".csv", FILE_WRITE);
  if(!csv) {
    return;
  }

  Serial.println("File /Record"+String(idx)+".csv opened.");
  csv.println("Time, PM2.5, PM10, Temperature, Relative Humidity");
  startTime = rtc.now().unixtime() - interval;
}

void loop() {
  // set the current time
  DateTime now = rtc.now();
  epochTime = now.unixtime();
  
  // wait until enough time has elapsed to make a recording
  if (epochTime >= startTime + interval) {
    startTime = rtc.now().unixtime();
    dht20.begin();
    
    // wait for valid SDS011 reading
    error = 1;
    while (error) {
      error = sds.read(&p25,&p10);
    }

    // record time, temp, RH
    writeTime = rtc.now().unixtime();
    temp = dht20.getTemperature();
    rh = dht20.getHumidity();

    Serial.println(writeTime);
    // write readings to the SD card
    // each entry is 5 * 5 = 25 bytes
    csv.println(String(writeTime)+","+String(p25)+","+String(p10)+","+String(temp)+","+String(rh));
    count++;

    // if the number of records has been reached, close the file
    if (count >= recordsPerFile or buttonState) { 
      csv.close();
      Serial.println("Closing file "+String(idx));
      
      // reset the count and button state
      count = 0;
      buttonState = 0;
      idx++;
      csv = SD.open("/Record"+String(idx)+".csv", FILE_WRITE);
    }
  }
}

/**
 * ISR for the button press routine
 */
void buttonPress() {
  buttonState = 1;
}
