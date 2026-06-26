/*
 * ESP32-CAM MJPEG Streaming Server
 * Board: AI Thinker ESP32-CAM with OV2640
 * Stream URL: http://<IP>/stream
 * CHANGE WiFi credentials below before uploading.
 */

#include "esp_camera.h"
#include <WiFi.h>
#include "esp_timer.h"
#include "img_converters.h"
#include "fb_gfx.h"
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"
#include "esp_http_server.h"

// WiFi Credentials — CHANGE THESE
const char* WIFI_SSID     = "YOUR_WIFI_SSID";      // <── change
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";   // <── change


#define PWDN_GPIO_NUM    32
#define RESET_GPIO_NUM   -1
#define XCLK_GPIO_NUM     0
#define SIOD_GPIO_NUM    26
#define SIOC_GPIO_NUM    27
#define Y9_GPIO_NUM      35
#define Y8_GPIO_NUM      34
#define Y7_GPIO_NUM      39
#define Y6_GPIO_NUM      36
#define Y5_GPIO_NUM      21
#define Y4_GPIO_NUM      19
#define Y3_GPIO_NUM      18
#define Y2_GPIO_NUM       5
#define VSYNC_GPIO_NUM   25
#define HREF_GPIO_NUM    23
#define PCLK_GPIO_NUM    22


#define PART_BOUNDARY "gc_car_frame_boundary"
static const char* STREAM_CONTENT_TYPE =
  "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* STREAM_BOUNDARY =
  "\r\n--" PART_BOUNDARY "\r\n";
static const char* STREAM_PART =
  "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

httpd_handle_t camera_httpd = NULL;


static esp_err_t stream_handler(httpd_req_t* req) {
  camera_fb_t* fb      = NULL;
  esp_err_t    res     = ESP_OK;
  size_t       jpg_len = 0;
  uint8_t*     jpg_buf = NULL;
  char         part_hdr[64];

  httpd_resp_set_type(req, STREAM_CONTENT_TYPE);
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

  while (true) {
    fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("[WARN] Camera frame capture failed");
      res = ESP_FAIL;
    } else {
      if (fb->format != PIXFORMAT_JPEG) {
        if (!frame2jpg(fb, 80, &jpg_buf, &jpg_len)) {
          Serial.println("[WARN] JPEG conversion failed");
          esp_camera_fb_return(fb);
          fb  = NULL;
          res = ESP_FAIL;
        } else {
          esp_camera_fb_return(fb);
          fb = NULL;
        }
      } else {
        jpg_len = fb->len;
        jpg_buf = fb->buf;
      }
    }

    if (res == ESP_OK) {
      size_t hlen = snprintf(part_hdr, 64, STREAM_PART, jpg_len);
      res = httpd_resp_send_chunk(req, STREAM_BOUNDARY, strlen(STREAM_BOUNDARY));
      if (res == ESP_OK)
        res = httpd_resp_send_chunk(req, part_hdr, hlen);
      if (res == ESP_OK)
        res = httpd_resp_send_chunk(req, (const char*)jpg_buf, jpg_len);
    }

    if (fb)      { esp_camera_fb_return(fb); fb = NULL; jpg_buf = NULL; }
    else if (jpg_buf) { free(jpg_buf); jpg_buf = NULL; }

    if (res != ESP_OK) break;
  }
  return res;
}


void startStreamServer() {
  httpd_config_t config      = HTTPD_DEFAULT_CONFIG();
  config.server_port         = 80;
  config.max_uri_handlers    = 4;

  httpd_uri_t stream_uri = {
    .uri     = "/stream",
    .method  = HTTP_GET,
    .handler = stream_handler,
    .user_ctx = NULL
  };

  if (httpd_start(&camera_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(camera_httpd, &stream_uri);
    Serial.println("[INFO] Stream server started on /stream");
  } else {
    Serial.println("[ERROR] HTTP server start failed");
  }
}


void setup() {
  // Disable brownout detector (prevents resets on peak current)
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);

  Serial.begin(115200);
  Serial.setDebugOutput(false);
  Serial.println("\n[INFO] GC-Car ESP32-CAM booting...");


  camera_config_t cam;
  cam.ledc_channel = LEDC_CHANNEL_0;
  cam.ledc_timer   = LEDC_TIMER_0;
  cam.pin_d0       = Y2_GPIO_NUM;
  cam.pin_d1       = Y3_GPIO_NUM;
  cam.pin_d2       = Y4_GPIO_NUM;
  cam.pin_d3       = Y5_GPIO_NUM;
  cam.pin_d4       = Y6_GPIO_NUM;
  cam.pin_d5       = Y7_GPIO_NUM;
  cam.pin_d6       = Y8_GPIO_NUM;
  cam.pin_d7       = Y9_GPIO_NUM;
  cam.pin_xclk     = XCLK_GPIO_NUM;
  cam.pin_pclk     = PCLK_GPIO_NUM;
  cam.pin_vsync    = VSYNC_GPIO_NUM;
  cam.pin_href     = HREF_GPIO_NUM;
  cam.pin_sscb_sda = SIOD_GPIO_NUM;
  cam.pin_sscb_scl = SIOC_GPIO_NUM;
  cam.pin_pwdn     = PWDN_GPIO_NUM;
  cam.pin_reset    = RESET_GPIO_NUM;
  cam.xclk_freq_hz = 20000000;
  cam.pixel_format = PIXFORMAT_JPEG;

  if (psramFound()) {
    cam.frame_size   = FRAMESIZE_VGA;   // 640×480
    cam.jpeg_quality = 10;
    cam.fb_count     = 2;
    Serial.println("[INFO] PSRAM found — using VGA (640x480)");
  } else {
    cam.frame_size   = FRAMESIZE_QVGA;  // 320×240
    cam.jpeg_quality = 12;
    cam.fb_count     = 1;
    Serial.println("[INFO] No PSRAM — using QVGA (320x240)");
  }

  esp_err_t err = esp_camera_init(&cam);
  if (err != ESP_OK) {
    Serial.printf("[ERROR] Camera init failed: 0x%x\n", err);
    return;
  }
  Serial.println("[INFO] Camera initialized OK");


  sensor_t* s = esp_camera_sensor_get();
  s->set_brightness(s, 1);
  s->set_contrast(s, 1);
  s->set_saturation(s, 0);
  s->set_sharpness(s, 1);
  s->set_whitebal(s, 1);
  s->set_awb_gain(s, 1);
  s->set_exposure_ctrl(s, 1);
  s->set_aec2(s, 1);
  s->set_gain_ctrl(s, 1);
  s->set_agc_gain(s, 0);
  s->set_gainceiling(s, (gainceiling_t)2);


  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("[INFO] Connecting to WiFi");
  int tries = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    if (++tries > 30) {
      Serial.println("\n[ERROR] WiFi failed. Restarting...");
      ESP.restart();
    }
  }
  Serial.println("\n[INFO] WiFi connected!");

  startStreamServer();

  Serial.println("============================================");
  Serial.print("[INFO] STREAM URL: http://");
  Serial.print(WiFi.localIP());
  Serial.println("/stream");
  Serial.println("Open this URL in Python or browser.");
  Serial.println("============================================");
}

void loop() {
  delay(10);  // Let FreeRTOS tasks run
}
