#!/usr/bin/env python3
"""
ESP32-S3 Ducky Web Dashboard & Natural Language Studio
======================================================
A zero-dependency web interface that converts natural human language into
DuckyScript, compiles it directly to Arduino sketches (USB / BLE / Dual),
and allows one-click download/copy for flashing your ESP32-S3.

Run:
    python web_server.py
    (Opens http://localhost:8080)
"""

import http.server
import json
import os
import sys
import urllib.parse
from pathlib import Path

from compiler.duckyscript_parser import DuckyScriptParser
from compiler.arduino_generator import ArduinoGenerator
from compiler.ble_generator import BleGenerator
from compiler.dual_generator import DualModeGenerator
from compiler.nlp_converter import NaturalLanguageToDucky
from compiler.simulator import VirtualSimulator

PORT = 8080
BASE_DIR = Path(__file__).parent
PAYLOADS_DIR = BASE_DIR / "payloads"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ESP32-S3 Ducky Studio | Natural Language to DuckyScript</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #090d16;
      --card-bg: rgba(16, 23, 38, 0.7);
      --border: rgba(255, 255, 255, 0.08);
      --border-accent: rgba(56, 189, 248, 0.4);
      --accent: #38bdf8;
      --accent-hover: #0284c7;
      --accent-glow: rgba(56, 189, 248, 0.2);
      --green: #10b981;
      --purple: #a855f7;
      --text-main: #f1f5f9;
      --text-muted: #94a3b8;
      --code-bg: #060911;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', -apple-system, sans-serif;
      background: radial-gradient(circle at top right, #111e38 0%, var(--bg) 60%);
      color: var(--text-main);
      min-height: 100vh;
      padding: 24px;
    }

    .container {
      max-width: 1400px;
      margin: 0 auto;
    }

    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 24px;
      border-bottom: 1px solid var(--border);
      margin-bottom: 24px;
    }

    .logo-badge {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      background: rgba(56, 189, 248, 0.1);
      border: 1px solid rgba(56, 189, 248, 0.3);
      padding: 6px 14px;
      border-radius: 9999px;
      font-size: 13px;
      color: var(--accent);
      font-weight: 600;
      letter-spacing: 0.5px;
    }

    h1 {
      font-size: 26px;
      font-weight: 700;
      margin-top: 8px;
      background: linear-gradient(135deg, #fff 0%, #cbd5e1 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .subtitle {
      color: var(--text-muted);
      font-size: 14px;
      margin-top: 4px;
    }

    .grid-layout {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
    }

    @media (max-width: 1024px) {
      .grid-layout { grid-template-columns: 1fr; }
    }

    .card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 20px;
      backdrop-filter: blur(12px);
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .card-title {
      font-size: 16px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .pill {
      font-size: 11px;
      padding: 3px 8px;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border);
      color: var(--text-muted);
    }

    .pill.green {
      background: rgba(16, 185, 129, 0.1);
      color: var(--green);
      border-color: rgba(16, 185, 129, 0.3);
    }

    .pill.purple {
      background: rgba(168, 85, 247, 0.1);
      color: var(--purple);
      border-color: rgba(168, 85, 247, 0.3);
    }

    .controls-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }

    label {
      font-size: 13px;
      color: var(--text-muted);
      font-weight: 500;
    }

    select, input[type="text"] {
      background: #0d1322;
      border: 1px solid var(--border);
      color: var(--text-main);
      padding: 8px 12px;
      border-radius: 8px;
      font-size: 13px;
      outline: none;
      transition: all 0.2s ease;
    }

    select:focus, input[type="text"]:focus, textarea:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 2px var(--accent-glow);
    }

    textarea {
      width: 100%;
      background: var(--code-bg);
      border: 1px solid var(--border);
      color: #e2e8f0;
      border-radius: 10px;
      padding: 14px;
      font-family: 'Fira Code', monospace;
      font-size: 13px;
      line-height: 1.5;
      resize: vertical;
      min-height: 180px;
      outline: none;
    }

    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      background: var(--accent);
      color: #041226;
      border: none;
      padding: 10px 18px;
      border-radius: 8px;
      font-weight: 600;
      font-size: 13px;
      cursor: pointer;
      transition: all 0.2s ease;
      box-shadow: 0 2px 10px var(--accent-glow);
    }

    .btn:hover {
      background: #7dd3fc;
      transform: translateY(-1px);
    }

    .btn.secondary {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border);
      color: var(--text-main);
      box-shadow: none;
    }

    .btn.secondary:hover {
      background: rgba(255, 255, 255, 0.1);
    }

    .preset-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    .preset-btn {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--border);
      color: #94a3b8;
      padding: 5px 10px;
      border-radius: 6px;
      font-size: 12px;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .preset-btn:hover {
      background: rgba(56, 189, 248, 0.1);
      border-color: var(--border-accent);
      color: #e0f2fe;
    }

    .editor-container {
      position: relative;
    }

    .copy-btn {
      position: absolute;
      top: 10px;
      right: 10px;
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid var(--border);
      color: var(--text-muted);
      padding: 5px 10px;
      border-radius: 6px;
      font-size: 11px;
      cursor: pointer;
      backdrop-filter: blur(4px);
    }

    .copy-btn:hover {
      color: #fff;
      background: rgba(255, 255, 255, 0.15);
    }

    .status-bar {
      margin-top: 20px;
      padding: 12px 18px;
      border-radius: 10px;
      background: rgba(16, 23, 38, 0.5);
      border: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 13px;
      color: var(--text-muted);
    }

    .toast {
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #10b981;
      color: #fff;
      padding: 10px 18px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 500;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.3s ease;
      box-shadow: 0 10px 25px rgba(0,0,0,0.4);
      z-index: 1000;
    }
    .toast.show { opacity: 1; }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <div class="logo-badge">
          <span>ESP32-S3</span> &bull; <span>RUBBER DUCKY STUDIO</span>
        </div>
        <h1>Natural Language &rarr; DuckyScript &rarr; Arduino</h1>
        <p class="subtitle">Write prompts in normal human language, convert to DuckyScript, and compile for USB or Bluetooth HID.</p>
      </div>
      <div>
        <span class="pill green">ESP32-S3 Ready</span>
      </div>
    </header>

    <div class="grid-layout">
      <!-- LEFT CARD: Natural Language Input -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">
            <span>Natural Human Language Prompt</span>
          </div>
          <span class="pill purple">Auto-Parser</span>
        </div>

        <div class="controls-row">
          <label for="target-os">Target System:</label>
          <select id="target-os" onchange="updateScreenPresets()">
            <option value="windows" selected>Windows (PC)</option>
            <option value="android">Android (Mobile)</option>
            <option value="ios">iOS (iPhone / iPad)</option>
            <option value="mac">macOS (Apple Mac)</option>
            <option value="linux">Linux (Desktop)</option>
          </select>
          <label for="screen-res" style="margin-left: 10px;">Screen Resolution:</label>
          <select id="screen-res">
            <option value="1080 2400" selected>Android (1080x2400)</option>
            <option value="1170 2532">iPhone (1170x2532)</option>
            <option value="720 1600">Android 720p (720x1600)</option>
            <option value="1920 1080">PC (1920x1080)</option>
            <option value="2560 1440">PC 2K (2560x1440)</option>
          </select>
        </div>

        <div class="preset-chips">
          <button class="preset-btn" onclick="applyPreset('notepad')">Notepad & Type</button>
          <button class="preset-btn" onclick="applyPreset('mobile')">Mobile Spotlight & URL</button>
          <button class="preset-btn" onclick="applyPreset('mobile_mouse')">Mobile App & Click Allow</button>
          <button class="preset-btn" onclick="applyPreset('sysinfo')">Grab System Info</button>
          <button class="preset-btn" onclick="applyPreset('rickroll')">Open Browser to Video</button>
          <button class="preset-btn" onclick="applyPreset('lock')">Lock Workstation</button>
        </div>

        <textarea id="nl-input" placeholder="Type instructions in plain English, for example:
1. Open notepad
2. Wait 1 second
3. Type Hello from my ESP32-S3 Rubber Ducky!
4. Press Enter"></textarea>

        <div class="controls-row">
          <button class="btn" onclick="convertNL()">
            <span>Convert to DuckyScript</span> &rarr;
          </button>
          <button class="btn secondary" onclick="document.getElementById('nl-input').value = ''">Clear</button>
        </div>
      </div>

      <!-- RIGHT CARD: Generated DuckyScript & Compiler -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">
            <span>DuckyScript Editor</span>
          </div>
          <div class="controls-row">
            <select id="sample-payloads" onchange="loadSample(this.value)">
              <option value="">-- Load Existing Payload --</option>
            </select>
          </div>
        </div>

        <div class="editor-container">
          <button class="copy-btn" onclick="copyText('ducky-output')">Copy Script</button>
          <textarea id="ducky-output" placeholder="// Your compiled DuckyScript will appear here..."></textarea>
        </div>

        <div class="controls-row" style="border-top: 1px solid var(--border); padding-top: 14px;">
          <div>
            <label for="hid-target">HID Interface:</label>
            <select id="hid-target">
              <option value="usb" selected>Wired USB HID (PC)</option>
              <option value="ble">Bluetooth BLE HID (Mobile & PC)</option>
              <option value="dual">Dual-Mode (USB + BLE)</option>
            </select>
          </div>
          <div>
            <label for="ble-name">BLE Name:</label>
            <input type="text" id="ble-name" value="Wireless Keyboard" style="width: 160px;">
          </div>
          <button class="btn secondary" onclick="runSimulation()">
            <span>🎮 Run Virtual Simulator</span>
          </button>
          <button class="btn" style="margin-left: auto;" onclick="compileToArduino()">
            <span>Generate Arduino .ino</span>
          </button>
        </div>
      </div>
    </div>

    <!-- VIRTUAL SIMULATOR CARD -->
    <div class="card" style="margin-top: 24px;" id="sim-card">
      <div class="card-header">
        <div class="card-title">
          <span>🎮 Live Virtual Device Simulator</span>
          <span class="pill green" id="sim-badge">Ready</span>
        </div>
        <div class="controls-row">
          <span id="sim-timer" class="pill purple">0.0s / 0.0s</span>
          <button class="btn secondary" onclick="runSimulation()">Re-run Simulation</button>
        </div>
      </div>

      <div style="display: grid; grid-template-columns: 280px 1fr; gap: 24px; align-items: start;">
        <!-- Virtual Phone Display Mockup -->
        <div style="width: 260px; height: 500px; background: #000; border-radius: 36px; border: 4px solid #334155; position: relative; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.6); margin: 0 auto;">
          <!-- Speaker Notch -->
          <div style="position: absolute; top: 10px; left: 50%; transform: translateX(-50%); width: 70px; height: 18px; background: #0f172a; border-radius: 12px; z-index: 20;"></div>
          
          <!-- Screen Wallpaper -->
          <div style="position: absolute; inset: 0; background: radial-gradient(circle at 50% 20%, #1e1b4b 0%, #030712 100%); display: flex; flex-direction: column; justify-content: space-between; padding: 36px 16px 20px 16px; font-family: sans-serif;">
            <!-- Top Status -->
            <div style="display: flex; justify-content: space-between; font-size: 11px; color: #94a3b8; font-weight: 600;">
              <span>9:41</span>
              <span>📶 5G 🔋 80%</span>
            </div>

            <!-- Virtual Typing Box -->
            <div id="sim-typing-box" style="background: rgba(30, 41, 59, 0.85); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 10px; font-family: 'Fira Code', monospace; font-size: 11px; color: #38bdf8; min-height: 50px; word-break: break-all; backdrop-filter: blur(8px);">
              <span style="color: #64748b;">// Virtual typing...</span>
            </div>

            <!-- Virtual Permission Modal Dialog -->
            <div id="sim-modal-dialog" style="background: #1e293b; border: 1px solid #38bdf8; border-radius: 16px; padding: 14px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.8); transition: all 0.3s ease; opacity: 0; transform: scale(0.9);">
              <div style="font-size: 12px; font-weight: 700; color: #f8fafc; margin-bottom: 4px;">Allow Permissions?</div>
              <div style="font-size: 10px; color: #94a3b8; margin-bottom: 12px;">Chrome wants to access your device.</div>
              <div style="display: flex; gap: 8px;">
                <button style="flex: 1; padding: 6px; font-size: 11px; background: #334155; border: none; color: #94a3b8; border-radius: 6px;">Deny</button>
                <button id="sim-allow-btn" style="flex: 1; padding: 6px; font-size: 11px; background: #0284c7; border: none; color: #fff; border-radius: 6px; font-weight: 700; transition: all 0.2s;">Allow</button>
              </div>
            </div>

            <!-- Bottom Home Indicator -->
            <div style="width: 90px; height: 4px; background: #475569; border-radius: 2px; margin: 0 auto;"></div>
          </div>

          <!-- Animated Mouse Cursor Pointer -->
          <div id="sim-cursor" style="position: absolute; width: 14px; height: 14px; border-radius: 50%; background: #38bdf8; border: 2px solid #fff; box-shadow: 0 0 14px #38bdf8; transform: translate(-50%, -50%); transition: top 0.25s ease-out, left 0.25s ease-out, transform 0.1s; top: 10px; left: 10px; z-index: 30; pointer-events: none;"></div>
        </div>

        <!-- Simulation Event Stream Log -->
        <div style="display: flex; flex-direction: column; gap: 12px;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <label style="font-weight: 600;">Simulation Execution Log:</label>
            <span id="sim-step-count" style="font-size: 12px; color: var(--text-muted);">0 / 0 steps</span>
          </div>
          <div id="sim-log" style="background: var(--code-bg); border: 1px solid var(--border); border-radius: 12px; height: 440px; overflow-y: auto; padding: 14px; font-family: 'Fira Code', monospace; font-size: 12px; line-height: 1.6; display: flex; flex-direction: column; gap: 6px;">
            <div style="color: #64748b;">Click "Run Virtual Simulator" to start hardware emulation test...</div>
          </div>
        </div>
      </div>
    </div>

    <!-- ARDUINO OUTPUT CARD -->
    <div class="card" style="margin-top: 24px;" id="arduino-card">
      <div class="card-header">
        <div class="card-title">
          <span>Generated Arduino Sketch (ESP32-S3 C++)</span>
        </div>
        <div class="controls-row">
          <button class="btn secondary" onclick="copyText('arduino-code')">Copy Code</button>
          <button class="btn" onclick="downloadIno()">Download .ino File</button>
        </div>
      </div>
      <div class="editor-container">
        <textarea id="arduino-code" style="height: 280px;" readonly placeholder="// Click 'Generate Arduino .ino' above to view the sketch..."></textarea>
      </div>
    </div>

    <div class="status-bar">
      <span id="status-text">Ready. Enter instructions or choose a preset.</span>
      <span>Dashboard: http://localhost:8080</span>
    </div>
  </div>

  <div id="toast" class="toast">Copied to clipboard!</div>

  <script>
    const PRESETS = {
      notepad: "1. Open notepad\\n2. Wait 1 second\\n3. Type Hello from ESP32-S3 DIY Rubber Ducky!\\n4. Press Enter",
      mobile: "1. Press GUI SPACE\\n2. Wait 800ms\\n3. Type https://example.com and press enter",
      mobile_mouse: "1. Open Chrome\\n2. Wait 1.5 seconds\\n3. Move mouse down 150\\n4. Click allow",
      sysinfo: "1. Open powershell\\n2. Wait 1 second\\n3. Type whoami and press enter\\n4. Type ipconfig and press enter",
      rickroll: "1. Open browser to https://www.youtube.com/watch?v=dQw4w9WgXcQ\\n2. Press Enter",
      lock: "1. Wait 500ms\\n2. Lock screen"
    };

    function applyPreset(key) {
      document.getElementById('nl-input').value = PRESETS[key] || '';
      convertNL();
    }

    async function loadSampleList() {
      try {
        const res = await fetch('/api/payloads');
        const data = await res.json();
        const sel = document.getElementById('sample-payloads');
        data.payloads.forEach(p => {
          const opt = document.createElement('option');
          opt.value = p;
          opt.textContent = p;
          sel.appendChild(opt);
        });
      } catch (err) {
        console.error(err);
      }
    }

    async function loadSample(name) {
      if (!name) return;
      try {
        const res = await fetch('/api/payload?file=' + encodeURIComponent(name));
        const data = await res.json();
        if (data.content) {
          document.getElementById('ducky-output').value = data.content;
          showStatus('Loaded payload: ' + name);
        }
      } catch (err) {
        alert('Failed to load payload: ' + err);
      }
    }

    async function convertNL() {
      const prompt = document.getElementById('nl-input').value.trim();
      const targetOs = document.getElementById('target-os').value;
      const screenRes = document.getElementById('screen-res').value;
      if (!prompt) {
        alert('Please write some instructions first.');
        return;
      }
      showStatus('Converting natural language with adaptive resolution scaling...');
      try {
        const res = await fetch('/api/convert', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt, target_os: targetOs, screen_res: screenRes })
        });
        const data = await res.json();
        if (data.success) {
          const resCmd = `SCREEN_SIZE ${screenRes}\\n`;
          document.getElementById('ducky-output').value = resCmd + data.script;
          showStatus(`Converted ${data.count} actions with calibrated resolution (${screenRes}).`);
        } else {
          alert('Error converting: ' + data.error);
        }
      } catch (err) {
        alert('Failed to convert: ' + err);
      }
    }

    async function compileToArduino() {
      const script = document.getElementById('ducky-output').value.trim();
      const target = document.getElementById('hid-target').value;
      const bleName = document.getElementById('ble-name').value;
      if (!script) {
        alert('DuckyScript is empty. Convert a prompt or write script first.');
        return;
      }
      showStatus('Compiling to Arduino...');
      try {
        const res = await fetch('/api/compile', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ script, target, ble_name: bleName })
        });
        const data = await res.json();
        if (data.success) {
          document.getElementById('arduino-code').value = data.code;
          showStatus(`Successfully compiled sketch for [${target.toUpperCase()}] target!`);
          document.getElementById('arduino-card').scrollIntoView({ behavior: 'smooth' });
        } else {
          alert('Compiler error:\\n' + data.error);
        }
      } catch (err) {
        alert('Compilation failed: ' + err);
      }
    }

    let simInterval = null;

    async function runSimulation() {
      const script = document.getElementById('ducky-output').value.trim();
      const screenRes = document.getElementById('screen-res').value;
      if (!script) {
        alert('DuckyScript is empty. Please convert or write a payload first.');
        return;
      }
      showStatus('Initializing virtual hardware simulation...');
      document.getElementById('sim-card').scrollIntoView({ behavior: 'smooth' });
      document.getElementById('sim-badge').textContent = 'Running...';
      document.getElementById('sim-badge').className = 'pill purple';

      try {
        const res = await fetch('/api/simulate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ script, screen_res: screenRes })
        });
        const data = await res.json();
        if (!data.success) {
          alert('Simulation failed: ' + data.error);
          return;
        }

        const logContainer = document.getElementById('sim-log');
        logContainer.innerHTML = '';
        const cursor = document.getElementById('sim-cursor');
        const typingBox = document.getElementById('sim-typing-box');
        const modal = document.getElementById('sim-modal-dialog');
        const allowBtn = document.getElementById('sim-allow-btn');
        const timerElem = document.getElementById('sim-timer');
        const stepCountElem = document.getElementById('sim-step-count');

        cursor.style.left = '10px';
        cursor.style.top = '10px';
        typingBox.innerHTML = '<span style="color: #64748b;">// Virtual typing...</span>';
        modal.style.opacity = '0';
        modal.style.transform = 'scale(0.9)';
        allowBtn.style.background = '#0284c7';
        allowBtn.textContent = 'Allow';

        let currentIdx = 0;
        const timeline = data.timeline;
        const totalDuration = data.total_duration_sec;

        function playNextStep() {
          if (currentIdx >= timeline.length) {
            document.getElementById('sim-badge').textContent = 'Completed';
            document.getElementById('sim-badge').className = 'pill green';
            showStatus(`Simulation complete! All ${timeline.length} actions verified.`);
            return;
          }

          const step = timeline[currentIdx];
          timerElem.textContent = `${step.time_formatted} / ${totalDuration}s`;
          stepCountElem.textContent = `${currentIdx + 1} / ${timeline.length} steps`;

          // Log entry
          const row = document.createElement('div');
          const color = step.channel === 'KEYBOARD' ? '#38bdf8' : (step.channel === 'MOUSE' ? '#a855f7' : (step.channel === 'DELAY' ? '#e2e8f0' : '#10b981'));
          row.innerHTML = `<span style="color: #64748b;">[${step.time_formatted}]</span> <span style="color: ${color}; font-weight: 600;">[${step.channel}]</span> ${step.description}`;
          logContainer.appendChild(row);
          logContainer.scrollTop = logContainer.scrollHeight;

          // Visual reactions
          if (step.text) {
            typingBox.textContent = '> ' + step.text;
          }

          if (step.pct_x !== undefined && step.pct_y !== undefined) {
            cursor.style.left = `${step.pct_x}%`;
            cursor.style.top = `${step.pct_y}%`;
          } else if (step.x !== undefined && step.y !== undefined) {
            const px = Math.min(95, Math.max(5, (step.x / data.screen_size.width) * 100));
            const py = Math.min(95, Math.max(5, (step.y / data.screen_size.height) * 100));
            cursor.style.left = `${px}%`;
            cursor.style.top = `${py}%`;
          }

          if (step.description.toLowerCase().includes('allow') || step.description.toLowerCase().includes('modal')) {
            modal.style.opacity = '1';
            modal.style.transform = 'scale(1)';
          }

          if (step.button) {
            cursor.style.transform = 'translate(-50%, -50%) scale(1.6)';
            setTimeout(() => { cursor.style.transform = 'translate(-50%, -50%) scale(1.0)'; }, 150);
            if (modal.style.opacity === '1') {
              allowBtn.style.background = '#10b981';
              allowBtn.textContent = '✓ Clicked!';
              setTimeout(() => {
                modal.style.opacity = '0';
                modal.style.transform = 'scale(0.9)';
              }, 700);
            }
          }

          currentIdx++;
          const nextDelay = Math.max(140, Math.min(500, step.duration_ms / 2));
          setTimeout(playNextStep, nextDelay);
        }

        playNextStep();
      } catch (err) {
        alert('Simulation error: ' + err);
      }
    }

    function downloadIno() {
      const code = document.getElementById('arduino-code').value;
      if (!code) {
        alert('Please compile code first.');
        return;
      }
      const blob = new Blob([code], { type: 'text/plain' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'esp32s3_ducky.ino';
      a.click();
    }

    function copyText(elemId) {
      const val = document.getElementById(elemId).value;
      if (!val) return;
      navigator.clipboard.writeText(val);
      const toast = document.getElementById('toast');
      toast.classList.add('show');
      setTimeout(() => toast.classList.remove('show'), 2000);
    }

    function showStatus(text) {
      document.getElementById('status-text').textContent = text;
    }

    window.onload = () => {
      loadSampleList();
      applyPreset('notepad');
    };
  </script>
</body>
</html>
"""


class DuckyRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
            return

        if path == "/api/payloads":
            files = [f.name for f in sorted(PAYLOADS_DIR.glob("*.duck"))] if PAYLOADS_DIR.exists() else []
            self._send_json({"payloads": files})
            return

        if path == "/api/payload":
            qs = urllib.parse.parse_qs(parsed.query)
            file_name = qs.get("file", [""])[0]
            target_file = PAYLOADS_DIR / file_name
            if target_file.exists() and target_file.suffix == ".duck":
                content = target_file.read_text(encoding="utf-8")
                self._send_json({"content": content})
            else:
                self._send_json({"error": "File not found"}, status=404)
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"

        try:
            data = json.loads(body)
        except Exception:
            data = {}

        if path == "/api/convert":
            prompt = data.get("prompt", "")
            target_os = data.get("target_os", "windows")
            converter = NaturalLanguageToDucky()
            result = converter.convert(prompt, target_os=target_os)
            self._send_json(result)
            return

        if path == "/api/simulate":
            script = data.get("script", "")
            screen_res = data.get("screen_res", "1080 2400").split()
            screen_w = int(screen_res[0]) if len(screen_res) > 0 else 1080
            screen_h = int(screen_res[1]) if len(screen_res) > 1 else 2400

            parser = DuckyScriptParser()
            try:
                commands = parser.parse(script)
            except SyntaxError as e:
                self._send_json({"success": False, "error": str(e)}, status=400)
                return

            sim = VirtualSimulator(screen_w=screen_w, screen_h=screen_h)
            result = sim.simulate(commands, default_delay=parser.default_delay)
            result["success"] = True
            self._send_json(result)
            return

        if path == "/api/compile":
            script = data.get("script", "")
            target = data.get("target", "usb").lower()
            ble_name = data.get("ble_name", "Wireless Keyboard")

            parser = DuckyScriptParser()
            try:
                commands = parser.parse(script)
            except SyntaxError as e:
                self._send_json({"success": False, "error": str(e)}, status=400)
                return

            if target == "ble":
                gen = BleGenerator(device_name=ble_name)
            elif target == "dual":
                gen = DualModeGenerator(device_name=ble_name)
            else:
                gen = ArduinoGenerator()

            code = gen.generate(commands, default_delay=parser.default_delay)
            self._send_json({"success": True, "code": code})
            return

        self.send_response(404)
        self.end_headers()

    def _send_json(self, obj, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode("utf-8"))

    def log_message(self, format, *args):
        # Concise logging
        sys.stderr.write(f"[{self.log_date_time_string()}] {args[0]} {args[1]}\n")


def run():
    server_address = ("127.0.0.1", PORT)
    httpd = http.server.HTTPServer(server_address, DuckyRequestHandler)
    print(f"\n=======================================================")
    print(f"  ESP32-S3 Ducky Studio Web Dashboard")
    print(f"  Running locally at: http://localhost:{PORT}")
    print(f"  Open this in your browser to write natural language prompts!")
    print(f"=======================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Server stopped.")


if __name__ == "__main__":
    run()
