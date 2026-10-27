// ESP32-CAM physical button capture sketch (template)
// Configure WIFI_SSID, WIFI_PASSWORD, DJANGO_BASE_URL, DEVICE_TOKEN, BUTTON_PIN before flashing.

#include <WiFi.h>
#include <HTTPClient.h>
#include "esp_camera.h"

const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* DJANGO_BASE_URL = "http://192.168.1.10:8000/api";
const char* DEVICE_TOKEN = "YOUR_DEVICE_TOKEN";

// Set after verifying your exact ESP32-CAM board pinout.
// Avoid camera, flash, boot, and SD-card pins.
const int BUTTON_PIN = 13;

bool lastButtonState = HIGH;
unsigned long lastDebounceTime = 0;
const unsigned long debounceDelay = 250;
const unsigned long longPressMs = 1500;
bool uploadInProgress = false;

void setup() {
  Serial.begin(115200);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  // Camera init omitted: use the standard init for your board.
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println(WiFi.localIP());
}

void loop() {
  bool reading = digitalRead(BUTTON_PIN);
  if (reading != lastButtonState) lastDebounceTime = millis();
  if ((millis() - lastDebounceTime) > debounceDelay) {
    if (reading == LOW && !uploadInProgress) {
      uploadInProgress = true;
      captureAndUpload();
      uploadInProgress = false;
    }
  }
  lastButtonState = reading;
}

void captureAndUpload() {
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) { Serial.println("Capture failed"); return; }

  HTTPClient http;
  String url = String(DJANGO_BASE_URL) + "/device/capture/";
  http.begin(url);
  http.addHeader("Authorization", String("Token ") + DEVICE_TOKEN);

  String boundary = "----ESP32Boundary";
  String head = "--" + boundary + "\r\n";
  head += "Content-Disposition: form-data; name=\"image\"; filename=\"capture.jpg\"\r\n";
  head += "Content-Type: image/jpeg\r\n\r\n";
  String tail = "\r\n--" + boundary + "--\r\n";

  // Build multipart body in memory (suitable for small JPEGs).
  size_t total = head.length() + fb->len + tail.length();
  uint8_t* body = (uint8_t*)malloc(total);
  if (!body) { esp_camera_fb_return(fb); return; }
  memcpy(body, head.c_str(), head.length());
  memcpy(body + head.length(), fb->buf, fb->len);
  memcpy(body + head.length() + fb->len, tail.c_str(), tail.length());

  http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);
  int code = http.POST(body, total);
  Serial.printf("Upload status: %d\n", code);
  if (code > 0) Serial.println(http.getString());

  free(body);
  esp_camera_fb_return(fb);
  http.end();
}
