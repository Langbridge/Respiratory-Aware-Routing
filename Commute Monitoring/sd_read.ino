/**
 * sd_read
 *     Outputs the content of an internal SD card to the Serial Monitor.
 *     Allows filtering by file prefix to only display certain file contents.
 * 
 * @author Abi Langbridge
 * @version 1.2 19/5/22
 */

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

  // wait for SD card to mount
  while (!SD.begin(26)) {
    delay(100);
  }

  Serial.print("Printing....");

  root = SD.open("/");
  printDirectory(root, 0, "Journey");
}

void loop() {}

/**
 * Prints the sub-directories in directory dir, and files beginning with prefix.
 * 
 * @param dir directory to print from
 * @param numTabs number of tabs to prefix print with, recursion depth
 * @param prefix string prefix to search files for to print
*/
void printDirectory(File dir, int numTabs, str prefix) {

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
      printDirectory(entry, numTabs+1, prefix);
    }
    else {
      Serial.println();
      // only print the contents of files beginning "Journey"
      if(String(entry.name()).indexOf(prefix) >= 0) {
        while (entry.available()) {
          Serial.write(entry.read());
        }
      }
    }

    entry.close();

  }
}
