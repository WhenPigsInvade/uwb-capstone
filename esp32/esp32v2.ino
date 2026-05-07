#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <HX711_ADC.h>
#include <DFRobot_SHT3x.h>
#include <Adafruit_MLX90614.h>
#include <Keypad.h>
#include <LiquidCrystal_I2C.h>
#if defined(ESP8266) || defined(ESP32) || defined(AVR)
#include <EEPROM.h>
#endif

// ----------------------------
// 🔌 WIFI CONFIG (HOTSPOT)
// ----------------------------
const char* ssid      = "exawater";
const char* password  = "password";
const char* serverUrl = "http://192.168.137.1:5001/data";

// --- Forward declarations ---
void calibrate();
void changeSavedCalFactor();
float readCoilTemp(uint8_t channel, Adafruit_MLX90614 &sensor, uint8_t powerPin);
void tcaSelect(uint8_t channel);
void tcaClose();
void homeScreen(char key);
void inputScreen(char key);
void inputScreen2(char key);
bool lcdDelayDone();
void startLcdDelay(unsigned long duration);
void takeMeasurement();
void printAndSendAverages();

// --- HX711 pins ---
const int HX711_dout = 19;
const int HX711_sck  = 18;

// --- TCA9548A address ---
#define TCA_ADDR 0x70

// --- Sensor objects ---
HX711_ADC         LoadCell(HX711_dout, HX711_sck);
Adafruit_MLX90614 mlx_top;
Adafruit_MLX90614 mlx_mid;
Adafruit_MLX90614 mlx_bot;
DFRobot_SHT3x     sht3x_inside;
DFRobot_SHT3x     sht3x_outside;

const int calVal_eepromAdress = 0;

// --- Timing ---
const unsigned long MEASURE_INTERVAL  = 30000UL;        // 30 seconds
const unsigned long AVERAGE_INTERVAL  = 20UL * 60UL * 1000UL; // 20 minutes
unsigned long lastMeasureTime         = 0;
unsigned long lastAverageTime         = 0;

// --- HX711 background update ---
static boolean newDataReady = false;

// --- MLX power pins ---
#define MLX_TOP_POWER_PIN 25
#define MLX_MID_POWER_PIN 26
#define MLX_BOT_POWER_PIN 27

// --- I2C LCD (CH5 on TCA9548A) ---
LiquidCrystal_I2C lcd(0x27, 16, 2);

// --- Keypad ---
const byte ROWS = 4;
const byte COLS = 3;
char keys[ROWS][COLS] = {
  {'1','2','3'},
  {'4','5','6'},
  {'7','8','9'},
  {'*','0','#'},
};
byte rowPins[ROWS] = {23, 5, 15, 16};
byte colPins[COLS]  = {33, 13, 14};
Keypad kpd = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);

// --- Screen state ---
bool isHome           = true;
bool isInputting      = false;
bool isInputting2     = false;
bool isWelcoming      = true;
bool isPrinted        = false;
bool isPrinted2       = false;
int  fanSpeed         = 0;
int  chillerTemp      = 0;

// --- Non-blocking LCD delay ---
unsigned long lcdDelayStart    = 0;
unsigned long lcdDelayDuration = 0;
bool lcdDelayActive    = false;
bool switchingToInput  = false;
bool switchingToInput2 = false;
bool showingSaved      = false;

// ----------------------------
// Measurement accumulator
// ----------------------------
struct SensorAccumulator {
  float ambientTemp    = 0;
  float humidity       = 0;
  float ambientTempOut = 0;
  float humidityOut    = 0;
  float coilTempTop    = 0;
  float coilTempMid    = 0;
  float coilTempBot    = 0;
  float weight         = 0;
  int   count          = 0;
};

SensorAccumulator acc;

// -------------------------------------------------------
// TCA9548A direct I2C control
// -------------------------------------------------------
void tcaSelect(uint8_t channel) {
  if (channel > 7) return;
  Wire.beginTransmission(TCA_ADDR);
  Wire.write(1 << channel);
  Wire.endTransmission();
}

void tcaClose() {
  Wire.beginTransmission(TCA_ADDR);
  Wire.write(0);
  Wire.endTransmission();
}

// -------------------------------------------------------
float readCoilTemp(uint8_t channel, Adafruit_MLX90614 &sensor, uint8_t powerPin) {
  tcaSelect(channel);
  float temp = sensor.readObjectTempC();
  delay(10);
  if (isnan(temp)) {
    Serial.print("MLX90614 CH");
    Serial.print(channel);
    Serial.println(": power cycling sensor...");

    digitalWrite(powerPin, LOW);
    delay(500);
    digitalWrite(powerPin, HIGH);
    delay(500);

    Wire.end();
    delay(100);
    Wire.begin(21, 22);
    Wire.setClock(50000);
    delay(100);

    tcaSelect(channel);
    sensor.begin();
    delay(200);

    temp = sensor.readObjectTempC();
    delay(10);
  }
  tcaClose();
  return temp;
}

// -------------------------------------------------------
// Take a single measurement and add to accumulator
// -------------------------------------------------------
void takeMeasurement() {
  float coilTempTop = readCoilTemp(0, mlx_top, MLX_TOP_POWER_PIN);
  float coilTempMid = readCoilTemp(1, mlx_mid, MLX_MID_POWER_PIN);
  float coilTempBot = readCoilTemp(2, mlx_bot, MLX_BOT_POWER_PIN);

  tcaSelect(3);
  float ambientTemp = sht3x_inside.getTemperatureC();
  float humidity    = sht3x_inside.getHumidityRH();
  tcaClose();

  tcaSelect(4);
  float ambientTempOut = sht3x_outside.getTemperatureC();
  float humidityOut    = sht3x_outside.getHumidityRH();
  tcaClose();

  float weight = newDataReady ? LoadCell.getData() : 0.0;
  newDataReady = false;

  // --- Add to accumulator ---
  acc.ambientTemp    += ambientTemp;
  acc.humidity       += humidity;
  acc.ambientTempOut += ambientTempOut;
  acc.humidityOut    += humidityOut;
  acc.coilTempTop    += coilTempTop;
  acc.coilTempMid    += coilTempMid;
  acc.coilTempBot    += coilTempBot;
  acc.weight         += weight;
  acc.count++;

  // --- Print individual reading to serial ---
  Serial.println("--- Measurement ---");
  Serial.print("Sample #            : "); Serial.println(acc.count);
  Serial.print("Ambient temp inside : "); Serial.print(ambientTemp);    Serial.println(" C");
  Serial.print("Humidity inside     : "); Serial.print(humidity);       Serial.println(" %");
  Serial.print("Ambient temp outside: "); Serial.print(ambientTempOut); Serial.println(" C");
  Serial.print("Humidity outside    : "); Serial.print(humidityOut);    Serial.println(" %");
  Serial.print("Coil temp top       : "); Serial.print(coilTempTop);    Serial.println(" C");
  Serial.print("Coil temp mid       : "); Serial.print(coilTempMid);    Serial.println(" C");
  Serial.print("Coil temp bot       : "); Serial.print(coilTempBot);    Serial.println(" C");
  Serial.print("Water produced      : "); Serial.print(weight);         Serial.println(" g");
  Serial.print("Fan speed setting   : "); Serial.println(fanSpeed);
  Serial.print("Chiller temp setting: "); Serial.println(chillerTemp);
  Serial.println("-------------------");
}

// -------------------------------------------------------
// Calculate averages, print and send to API
// -------------------------------------------------------
void printAndSendAverages() {
  if (acc.count == 0) {
    Serial.println("No samples to average.");
    return;
  }

  float avgAmbientTemp    = acc.ambientTemp    / acc.count;
  float avgHumidity       = acc.humidity       / acc.count;
  float avgAmbientTempOut = acc.ambientTempOut / acc.count;
  float avgHumidityOut    = acc.humidityOut    / acc.count;
  float avgCoilTempTop    = acc.coilTempTop    / acc.count;
  float avgCoilTempMid    = acc.coilTempMid    / acc.count;
  float avgCoilTempBot    = acc.coilTempBot    / acc.count;
  float avgWeight         = acc.weight         / acc.count;

  // --- Print averages to serial ---
  Serial.println("=== 20-Min Averages ===");
  Serial.print("Samples taken       : "); Serial.println(acc.count);
  Serial.print("Ambient temp inside : "); Serial.print(avgAmbientTemp);    Serial.println(" C");
  Serial.print("Humidity inside     : "); Serial.print(avgHumidity);       Serial.println(" %");
  Serial.print("Ambient temp outside: "); Serial.print(avgAmbientTempOut); Serial.println(" C");
  Serial.print("Humidity outside    : "); Serial.print(avgHumidityOut);    Serial.println(" %");
  Serial.print("Coil temp top       : "); Serial.print(avgCoilTempTop);    Serial.println(" C");
  Serial.print("Coil temp mid       : "); Serial.print(avgCoilTempMid);    Serial.println(" C");
  Serial.print("Coil temp bot       : "); Serial.print(avgCoilTempBot);    Serial.println(" C");
  Serial.print("Water produced      : "); Serial.print(avgWeight);         Serial.println(" g");
  Serial.print("Fan speed setting   : "); Serial.println(fanSpeed);
  Serial.print("Chiller temp setting: "); Serial.println(chillerTemp);
  Serial.println("=======================");

  // --- Build JSON with averages ---
  String json = "{";
  json += "\"device_id\":\"esp32-01\",";
  json += "\"readings\":[";
  json += "{\"sensor_type\":\"ambient_temp\",\"value\":"         + String(avgAmbientTemp)    + "},";
  json += "{\"sensor_type\":\"humidity\",\"value\":"             + String(avgHumidity)       + "},";
  json += "{\"sensor_type\":\"ambient_temp_outside\",\"value\":" + String(avgAmbientTempOut) + "},";
  json += "{\"sensor_type\":\"humidity_outside\",\"value\":"     + String(avgHumidityOut)    + "},";
  json += "{\"sensor_type\":\"coil_temp_top\",\"value\":"        + String(avgCoilTempTop)    + "},";
  json += "{\"sensor_type\":\"coil_temp_mid\",\"value\":"        + String(avgCoilTempMid)    + "},";
  json += "{\"sensor_type\":\"coil_temp_bot\",\"value\":"        + String(avgCoilTempBot)    + "},";
  json += "{\"sensor_type\":\"water_produced\",\"value\":"       + String(avgWeight)         + "},";
  json += "{\"sensor_type\":\"fan_speed\",\"value\":"            + String(fanSpeed)          + "},";
  json += "{\"sensor_type\":\"chiller_temp\",\"value\":"         + String(chillerTemp)       + "}";
  json += "]}";

  // --- Send to API ---
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");
    int code = http.POST(json);
    Serial.print("HTTP Response: ");
    Serial.println(code);
    if (code > 0) {
      Serial.println(http.getString());
    } else {
      Serial.println("POST failed");
    }
    http.end();
  } else {
    Serial.println("WiFi disconnected!");
  }

  // --- Reset accumulator ---
  acc = SensorAccumulator();
}

// -------------------------------------------------------
// Non-blocking LCD delay helpers
// -------------------------------------------------------
bool lcdDelayDone() {
  if (!lcdDelayActive) return true;
  if (millis() - lcdDelayStart >= lcdDelayDuration) {
    lcdDelayActive = false;
    return true;
  }
  return false;
}

void startLcdDelay(unsigned long duration) {
  lcdDelayStart    = millis();
  lcdDelayDuration = duration;
  lcdDelayActive   = true;
}

// -------------------------------------------------------
// LCD screen functions
// -------------------------------------------------------
void homeScreen(char key) {
  if (isHome) {
    if (showingSaved && lcdDelayDone()) {
      showingSaved = false;
      isWelcoming  = true;
    }
    if (switchingToInput && lcdDelayDone()) {
      switchingToInput = false;
      isInputting      = true;
      isHome           = false;
      return;
    }
    if (switchingToInput2 && lcdDelayDone()) {
      switchingToInput2 = false;
      isInputting2      = true;
      isHome            = false;
      return;
    }
    if (isWelcoming && !lcdDelayActive) {
      tcaSelect(5);
      lcd.setCursor(0, 0);
      lcd.print("Set Fn-># Ch->*");
      lcd.setCursor(0, 1);
      lcd.print("Fn-S: ");
      lcd.print(fanSpeed);
      lcd.print(" Ch-T: ");
      lcd.print(chillerTemp);
      lcd.print("    ");
      tcaClose();
      isWelcoming = false;
    }
    if (key == '#' && !lcdDelayActive) {
      tcaSelect(5);
      lcd.clear();
      lcd.print("switching...");
      tcaClose();
      switchingToInput = true;
      startLcdDelay(500);
    }
    if (key == '*' && !lcdDelayActive) {
      tcaSelect(5);
      lcd.clear();
      lcd.print("switching...");
      tcaClose();
      switchingToInput2 = true;
      startLcdDelay(500);
    }
  }
}

void inputScreen(char key) {
  if (isInputting) {
    if (!isPrinted && !lcdDelayActive) {
      tcaSelect(5);
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Set fan speed:");
      tcaClose();
      isPrinted = true;
    }
    if (key == NO_KEY) return;
    if (key >= '0' && key <= '9' && !lcdDelayActive) {
      fanSpeed = key - '0';
      tcaSelect(5);
      lcd.setCursor(0, 1);
      lcd.print(fanSpeed);
      lcd.print("   ");
      tcaClose();
      isHome       = true;
      isWelcoming  = false;
      isInputting  = false;
      isPrinted    = false;
      showingSaved = true;
      tcaSelect(5);
      lcd.clear();
      lcd.print("Saved!");
      tcaClose();
      startLcdDelay(500);
    }
  }
}

void inputScreen2(char key) {
  if (isInputting2) {
    if (!isPrinted2 && !lcdDelayActive) {
      tcaSelect(5);
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Set chiller temp");
      tcaClose();
      isPrinted2 = true;
    }
    if (key == NO_KEY) return;
    if (key >= '0' && key <= '9' && !lcdDelayActive) {
      chillerTemp = key - '0';
      tcaSelect(5);
      lcd.setCursor(0, 1);
      lcd.print(chillerTemp);
      lcd.print("   ");
      tcaClose();
      isHome        = true;
      isWelcoming   = false;
      isInputting2  = false;
      isPrinted2    = false;
      showingSaved  = true;
      tcaSelect(5);
      lcd.clear();
      lcd.print("Saved!");
      tcaClose();
      startLcdDelay(500);
    }
  }
}

// -------------------------------------------------------
void setup() {
  Serial.begin(57600);
  delay(10);
  Serial.println();
  Serial.println("Starting...");

  // --- MLX power pins ---
  pinMode(MLX_TOP_POWER_PIN, OUTPUT);
  pinMode(MLX_MID_POWER_PIN, OUTPUT);
  pinMode(MLX_BOT_POWER_PIN, OUTPUT);
  digitalWrite(MLX_TOP_POWER_PIN, HIGH);
  digitalWrite(MLX_MID_POWER_PIN, HIGH);
  digitalWrite(MLX_BOT_POWER_PIN, HIGH);
  delay(500);

  // --- Keypad debounce ---
  kpd.setDebounceTime(50);

  // --- I2C ---
  Wire.begin(21, 22);
  Wire.setClock(50000);
  delay(100);

  // --- Confirm TCA9548A ---
  Wire.beginTransmission(TCA_ADDR);
  byte tcaError = Wire.endTransmission();
  if (tcaError != 0) {
    Serial.println("TCA9548A: not found, check wiring!");
    while (1);
  }
  Serial.println("TCA9548A ready!");

  // --- LCD init (CH5) ---
  tcaSelect(5);
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("Starting...");
  tcaClose();
  delay(1000);
  tcaSelect(5);
  lcd.clear();
  tcaClose();

  // --- I2C scan (uncomment to check all channels) ---
  // for (uint8_t ch = 0; ch < 8; ch++) {
  //   tcaSelect(ch);
  //   Serial.print("Scanning CH"); Serial.println(ch);
  //   for (byte addr = 1; addr < 127; addr++) {
  //     Wire.beginTransmission(addr);
  //     byte error = Wire.endTransmission();
  //     if (error == 0) {
  //       Serial.print("  Found device at 0x");
  //       Serial.println(addr, HEX);
  //     }
  //   }
  //   tcaClose();
  // }
  // Serial.println("Scan complete");

  // --- MLX90614 top (CH0) ---
  tcaSelect(0);
  if (!mlx_top.begin()) {
    Serial.println("MLX90614 top (CH0): not found, check wiring!");
    while (1);
  }
  Serial.println("MLX90614 top ready!");
  tcaClose();

  // --- MLX90614 middle (CH1) ---
  tcaSelect(1);
  if (!mlx_mid.begin()) {
    Serial.println("MLX90614 middle (CH1): not found, check wiring!");
    while (1);
  }
  Serial.println("MLX90614 middle ready!");
  tcaClose();

  // --- MLX90614 bottom (CH2) ---
  tcaSelect(2);
  if (!mlx_bot.begin()) {
    Serial.println("MLX90614 bottom (CH2): not found, check wiring!");
    while (1);
  }
  Serial.println("MLX90614 bottom ready!");
  tcaClose();

  // --- SHT3x inside (CH3) ---
  tcaSelect(3);
  while (sht3x_inside.begin() != 0) {
    Serial.println("SHT3x inside (CH3): Failed to initialize, check wiring...");
    delay(1000);
  }
  Serial.print("SHT3x inside serial number: ");
  Serial.println(sht3x_inside.readSerialNumber());
  if (!sht3x_inside.softReset()) {
    Serial.println("SHT3x inside: soft reset failed");
  }
  Serial.println("SHT3x inside ready!");
  tcaClose();

  // --- SHT3x outside (CH4) ---
  tcaSelect(4);
  while (sht3x_outside.begin() != 0) {
    Serial.println("SHT3x outside (CH4): Failed to initialize, check wiring...");
    delay(1000);
  }
  Serial.print("SHT3x outside serial number: ");
  Serial.println(sht3x_outside.readSerialNumber());
  if (!sht3x_outside.softReset()) {
    Serial.println("SHT3x outside: soft reset failed");
  }
  Serial.println("SHT3x outside ready!");
  tcaClose();

  // --- HX711 init ---
LoadCell.begin();
unsigned long stabilizingtime = 2000;
boolean _tare = true;
LoadCell.start(stabilizingtime, _tare);
if (LoadCell.getTareTimeoutFlag() || LoadCell.getSignalTimeoutFlag()) {
  Serial.println("HX711: Timeout, check wiring and pin designations");
  while (1);
}

// --- Load calibration from EEPROM if it exists ---
float savedCalFactor;
EEPROM.begin(512);
EEPROM.get(calVal_eepromAdress, savedCalFactor);

if (savedCalFactor != 0 && !isnan(savedCalFactor)) {
  // Valid calibration found — load it and skip calibration
  LoadCell.setCalFactor(savedCalFactor);
  Serial.print("Loaded calibration from EEPROM: ");
  Serial.println(savedCalFactor);
  Serial.println("HX711 ready!");
  while (!LoadCell.update());
  LoadCell.tareNoDelay(); // tare on boot
  Serial.println("Tared.");
} else {
  // No calibration found — run calibration
  Serial.println("No calibration found, running calibration...");
  LoadCell.setCalFactor(1.0);
  while (!LoadCell.update());
  calibrate();
}

  ----------------------------
  WiFi connect (HOTSPOT)
  ----------------------------
  WiFi.begin(ssid, password);
  Serial.print("Connecting to hotspot");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected!");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());
}

// -------------------------------------------------------
void loop() {

  // --- Keep HX711 updating in background ---
  if (LoadCell.update()) newDataReady = true;

  // --- Keypad and LCD ---
  char key = kpd.getKey();
  homeScreen(key);
  inputScreen(key);
  inputScreen2(key);

  unsigned long now = millis();

  // --- Take measurement every 30 seconds ---
  if (now - lastMeasureTime >= MEASURE_INTERVAL) {
    lastMeasureTime = now;
    takeMeasurement();
  }

  // --- Average and send every 20 minutes ---
  if (now - lastAverageTime >= AVERAGE_INTERVAL) {
    lastAverageTime = now;
    printAndSendAverages();
  }

  // --- Serial commands for HX711 calibration ---
  if (Serial.available() > 0) {
    char inByte = Serial.read();
    if (inByte == 't')      LoadCell.tareNoDelay();
    else if (inByte == 'r') calibrate();
    else if (inByte == 'c') changeSavedCalFactor();
  }

  // --- Tare status ---
  if (LoadCell.getTareStatus() == true) {
    Serial.println("Tare complete");
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