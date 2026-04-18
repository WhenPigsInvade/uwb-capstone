#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid = "YOUR_HOTSPOT_NAME";
const char* password = "YOUR_PASSWORD";

// Your PC hotspot IP (IMPORTANT)
const char* serverUrl = "http://192.168.137.1:5001/data";

void setup() {
  Serial.begin(115200);
  
  WiFi.begin(ssid, password);
  Serial.print("Connecting");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nConnected!");
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;

    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");

    String json = R"({
      "device_id": "esp32_1",
      "readings": [
        {"sensor_type": "coil_temp", "value": 25.3},
        {"sensor_type": "humidity", "value": 60}
      ]
    })";

    int httpResponseCode = http.POST(json);

    Serial.print("Response: ");
    Serial.println(httpResponseCode);

    http.end();
  }

  delay(5000);
}