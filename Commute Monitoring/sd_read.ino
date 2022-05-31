#include <SPI.h>
#include <SD.h>
#include <SDS011.h>

int journey, idx;
File csv;
File root;

bool wipe = 0; // MAKE SURE THIS IS SET TO 0 FOR DATA RETRIEVAL

void setup() {
  Serial.begin(115200);
  delay(1000);

  while (!SD.begin(26)) {
    delay(100);
  }

  Serial.print("Printing....");

  journey = 1;
  idx = 0;
  
//  while(SD.exists("/Journey "+String(journey)+"_0.csv")) {
//    Serial.println("Journey"+String(journey));
//    
//    while(SD.exists("/Journey "+String(journey)+"_"+String(idx)+".csv")) {
//      csv = SD.open("/Journey "+String(journey)+"_"+String(idx)+".csv");
//      
//      if (csv) {
//        while (csv.available()) {
//          Serial.write(csv.read());
//        }
//        
//        csv.close();
//      }
//      
//      if (wipe) {
//        SD.remove("/Journey "+String(journey)+"_"+String(idx)+".csv");
//      }
//      
//      idx++;
//    }
//    Serial.println("");
//    journey++;
//  }

  root = SD.open("/");
  printDirectory(root, 0);
}

void loop() {}

void printDirectory(File dir, int numTabs) {

  while (true) {
    File entry =  dir.openNextFile();
    if (! entry) {
      break;
    }

    for (uint8_t i = 0; i < numTabs; i++) {
      Serial.print('\t');
    }

    Serial.print(entry.name());
    if (entry.isDirectory()) {
      Serial.println("/");
      printDirectory(entry, numTabs + 1);
    }
    else {
      Serial.println();
      if(String(entry.name()).indexOf("Journey") >= 0) {
        while (entry.available()) {
          Serial.write(entry.read());
        }
      }
    }

    entry.close();

  }
}
