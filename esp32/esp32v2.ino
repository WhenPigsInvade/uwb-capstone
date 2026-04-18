#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <HX711_ADC.h>
#include <DFRobot_SHT3x.h>
#include <Adafruit_MLX90614.h>
#if defined(ESP8266) || defined(ESP32) || defined(AVR)
#include <EEPROM.h>
#endif

const char* ssid = "YOUR_HOTSPOT_NAME";
const char* password = "YOUR_HOTSPOT_PASSWORD";

// Replace with YOUR PC hotspot IP
const char* serverUrl = "http://192.168.137.1:5001/data";

// --- Forward declarations ---
void calibrate();
void changeSavedCalFactor();

// --- HX711 pins ---
const int HX711_dout = 19;
const int HX711_sck  = 18;

// --- Sensor objects ---
HX711_ADC         LoadCell(HX711_dout, HX711_sck);
DFRobot_SHT3x     sht3x;
Adafruit_MLX90614 mlx = Adafruit_MLX90614();

const int calVal_eepromAdress = 0;

// --- Timing ---
unsigned long lastPrintTime = 0;
const int printInterval = 2000; // print every 2 seconds
static boolean newDataReady = false;

// -------------------------------------------------------
void setup() {
  Serial.begin(115200);

  // Connect to WiFi (your PC hotspot)
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nConnected!");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());

  // I2C init
  Wire.begin(21, 22);

  // SHT3x init
  while (sht3x.begin() != 0) {
    Serial.println("SHT3x init failed...");
    delay(1000);
  }

  Serial.println("SHT3x ready!");
}

void loop() {
  if (millis() - lastPrintTime >= printInterval) {
    lastPrintTime = millis();

    float ambientTemp = sht3x.getTemperatureC();
    float humidity    = sht3x.getHumidityRH();

    // Build JSON payload
    String json = "{";
    json += "\"device_id\":\"esp32-01\",";
    json += "\"readings\":[";
    json += "{\"sensor_type\":\"ambient_temp\",\"value\":" + String(ambientTemp) + "},";
    json += "{\"sensor_type\":\"humidity\",\"value\":" + String(humidity) + "}";
    json += "]}";

    Serial.println("Sending:");
    Serial.println(json);

    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;

      http.begin(serverUrl);
      http.addHeader("Content-Type", "application/json");

      int httpResponseCode = http.POST(json);

      Serial.print("Response code: ");
      Serial.println(httpResponseCode);

      if (httpResponseCode > 0) {
        String response = http.getString();
        Serial.println(response);
      } else {
        Serial.println("Error sending request");
      }

      http.end();
    } else {
      Serial.println("WiFi disconnected!");
    }
  }
}

// -------------------------------------------------------
void calibrate() {
  Serial.println("***");
  Serial.println("Start calibration:");
  Serial.println("Place the load cell on a level stable surface.");
  Serial.println("Remove any load applied to the load cell.");
  Serial.println("Send 't' from serial monitor to set the tare offset.");

  boolean _resume = false;
  while (_resume == false) {
    LoadCell.update();
    if (Serial.available() > 0) {
      char inByte = Serial.read();
      if (inByte == 't') LoadCell.tareNoDelay();
    }
    if (LoadCell.getTareStatus() == true) {
      Serial.println("Tare complete");
      _resume = true;
    }
  }

  Serial.println("Now, place your known mass on the load cell.");
  Serial.println("Then send the weight of this mass (i.e. 100.0) from serial monitor.");

  float known_mass = 0;
  _resume = false;
  while (_resume == false) {
    LoadCell.update();
    if (Serial.available() > 0) {
      known_mass = Serial.parseFloat();
      if (known_mass != 0) {
        Serial.print("Known mass is: ");
        Serial.println(known_mass);
        _resume = true;
      }
    }
  }

  LoadCell.refreshDataSet();
  float newCalibrationValue = LoadCell.getNewCalibration(known_mass);

  Serial.print("New calibration value: ");
  Serial.print(newCalibrationValue);
  Serial.println(" — save to EEPROM? y/n");

  _resume = false;
  while (_resume == false) {
    if (Serial.available() > 0) {
      char inByte = Serial.read();
      if (inByte == 'y') {
#if defined(ESP8266) || defined(ESP32)
        EEPROM.begin(512);
#endif
        EEPROM.put(calVal_eepromAdress, newCalibrationValue);
#if defined(ESP8266) || defined(ESP32)
        EEPROM.commit();
#endif
        EEPROM.get(calVal_eepromAdress, newCalibrationValue);
        Serial.print("Saved to EEPROM: ");
        Serial.println(newCalibrationValue);
        _resume = true;
      } else if (inByte == 'n') {
        Serial.println("Value not saved to EEPROM");
        _resume = true;
      }
    }
  }
  Serial.println("End calibration");
  Serial.println("***");
  Serial.println("Send 'r' to re-calibrate, 'c' to edit manually.");
  Serial.println("***");
}

// -------------------------------------------------------
void changeSavedCalFactor() {
  float oldCalibrationValue = LoadCell.getCalFactor();
  boolean _resume = false;
  Serial.println("***");
  Serial.print("Current calibration value: ");
  Serial.println(oldCalibrationValue);
  Serial.println("Send new value from serial monitor (i.e. 696.0)");

  float newCalibrationValue;
  while (_resume == false) {
    if (Serial.available() > 0) {
      newCalibrationValue = Serial.parseFloat();
      if (newCalibrationValue != 0) {
        Serial.print("New value: ");
        Serial.println(newCalibrationValue);
        LoadCell.setCalFactor(newCalibrationValue);
        _resume = true;
      }
    }
  }

  _resume = false;
  Serial.println("Save to EEPROM? y/n");
  while (_resume == false) {
    if (Serial.available() > 0) {
      char inByte = Serial.read();
      if (inByte == 'y') {
#if defined(ESP8266) || defined(ESP32)
        EEPROM.begin(512);
#endif
        EEPROM.put(calVal_eepromAdress, newCalibrationValue);
#if defined(ESP8266) || defined(ESP32)
        EEPROM.commit();
#endif
        EEPROM.get(calVal_eepromAdress, newCalibrationValue);
        Serial.print("Saved: ");
        Serial.println(newCalibrationValue);
        _resume = true;
      } else if (inByte == 'n') {
        Serial.println("Value not saved");
        _resume = true;
      }
    }
  }
  Serial.println("End change calibration value");
  Serial.println("***");
}