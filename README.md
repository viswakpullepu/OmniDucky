<div align="center">

```
             __
           <(o )___
            ( ._> /    O M N I D U C K Y
             `---'     ESP32-S3 HID FRAMEWORK
```

# 🦆 OmniDucky

### Next-Gen Wireless (BLE) & Wired (USB) Keystroke Injection Toolkit
**Autonomous HID Exploitation &bull; Natural Language to DuckyScript &bull; Adaptive Touch & Mouse Emulation**

---

[![Hardware](https://img.shields.io/badge/Board-ESP32--S3%20Dual--Core-E7352C?style=for-the-badge&logo=espressif&logoColor=white)](https://www.espressif.com/)
[![Protocol](https://img.shields.io/badge/Protocol-USB%20OTG%20%2B%20BLE%205.0-38BDF8?style=for-the-badge&logo=bluetooth&logoColor=white)](https://bluetooth.com)
[![Testing](https://img.shields.io/badge/Automated%20Tests-1%2C255%20Passed%20(100%25)-10B981?style=for-the-badge&logo=checkmarx&logoColor=white)](tests/)
[![Dashboard](https://img.shields.io/badge/Web%20Studio-Localhost%3A8080-8B5CF6?style=for-the-badge&logo=googlechrome&logoColor=white)](http://localhost:8080)
[![License](https://img.shields.io/badge/License-MIT-F59E0B?style=for-the-badge)](LICENSE)

<br/>

```
  +========================================================================+
  |  Turn a $5 ESP32-S3 into a dual-mode military-grade Rubber Ducky.      |
  |  Write in plain English -> Auto-compile -> Attack PC, Mac, & Mobiles.  |
  +========================================================================+
```

---

[Key Highlights](#-key-highlights) &bull;
[Hardware Blueprint](#-hardware-blueprint) &bull;
[Attack Architecture](#-attack-architecture) &bull;
[Target Matrix](#-cross-platform-target-matrix) &bull;
[Web Studio](#-interactive-web-studio) &bull;
[DuckyScript & Mouse Reference](#-duckyscript-syntax--mouse-extensions) &bull;
[Flashing Guide](#-setup--flashing-guide) &bull;
[Test Certification](#-verification--test-certification)

---

</div>

<br/>

## ⚡ Key Highlights

```
  ┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
  │   🗣️ Natural Voice    │   │   📶 Dual-Channel     │   │   🎯 Adaptive Touch   │
  │   Plain English NLP   │   │   Wired USB + BLE 5.0 │   │   Auto-Homing Mouse   │
  │   Converts speech or  │   │   Injects keystrokes  │   │   Slams to (0,0) then │
  │   text to DuckyScript │   │   into PCs & Mobiles  │   │   clicks permissions  │
  └───────────────────────┘   └───────────────────────┘   └───────────────────────┘
```

* **🧠 Natural Language Translation Engine**: Speak or type freely (*"Open Chrome, wait 2s, click allow"*). The parser auto-resolves app names, handles typos, and injects optimal OS delays.
* **📶 Dual USB-OTG & Bluetooth BLE 5.0**:
  * **Wired USB**: Blazing fast sub-second injection when physically inserted into laptops or workstations.
  * **Wireless BLE**: Masquerades as an authentic Bluetooth keyboard/mouse (*e.g., "Logitech K380"*). Silently executes payloads when paired with **Android** or **iPhones** up to 10 meters away.
* **🖱️ Calibrated Screen-Percentage Touch Simulation**:
  * Bypasses mobile permission prompts ("Allow Camera / Location / Notifications").
  * Uses **Hardware Corner Auto-Reset** to re-zero mouse drift, then taps exact screen percentage coordinates (`MOUSE_POS_PCT 50 62`) alongside keyboard `TAB` + `ENTER` navigation.
* **🖥️ Local Web Studio & Live Virtual Simulator**: Built-in zero-dependency dark-mode dashboard at `http://localhost:8080` with visual phone playback, real-time typing ticker, and 1-click `.ino` export.
* **🛡️ 100% Offline & Pure C++**: Zero cloud telemetry, zero API keys, and zero AI overhead on the microcontroller. The ESP32-S3 executes bare-metal HID machine instructions.

---

## 🔌 Hardware Blueprint

```
                     ESP32-S3 DEV MODULE PINOUT & LAYOUT
  +-------------------------------------------------------------------------+
  |  [o] ANTENNA (2.4GHz Wi-Fi / BLE 5.0)                                   |
  |  +------------------------+                                             |
  |  |   ESP32-S3-WROOM-1     |       [BOOT] GPIO 0 Button (Re-run Payload) |
  |  |   Xtensa Dual-Core LX7 |          |                                  |
  |  |   240MHz, 512KB SRAM   |          v                                  |
  |  +------------------------+      +-------+     +-------+                |
  |                                  |  (o)  |     |  (o)  |                |
  |   ( ) ( ) ( ) ( ) ( ) ( ) ( )    |  BOOT |     | RESET |                |
  |   ---------------------------    +-------+     +-------+                |
  |   GPIO PINS (3.3V / GND)                                                |
  |                                                                         |
  |      [RGB LED] NeoPixel (Status Blink)                                  |
  |          * Green  = Arming / Handshake                                  |
  |          * Blue   = Injected / Typing                                   |
  |          * Triple = Execution Finished                                  |
  |                                      +------------------+               |
  |                                      |  [==== USB ====] | <--- USB-OTG  |
  |                                      +------------------+     Native    |
  +-------------------------------------------------------------------------+
```

---

## 🏛️ Attack Architecture

```
   ┌──────────────────────────────────────────────────────────────┐
   │                    OPERATOR INPUT (ENGLISH)                  │
   │      "Open Chrome, go to https://target.com, click allow"     │
   └──────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
   ┌──────────────────────────────────────────────────────────────┐
   │             REFINED NLP & SEMANTIC COMPILER                  │
   │      compiler/nlp_converter.py  •  Typo & Synonym Engine     │
   └──────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
   ┌──────────────────────────────────────────────────────────────┐
   │                   DUCKYSCRIPT 3.0 + MOUSE IR                 │
   │      GUI SPACE -> STRING URL -> ENTER -> MOUSE_POS_PCT       │
   └──────────────┬───────────────────────────────┬───────────────┘
                  │                               │
                  ▼                               ▼
   ┌──────────────────────────────┐┌──────────────────────────────┐
   │      USB HID SUBSYSTEM       ││      BLE HID SUBSYSTEM       │
   │   Native USB-OTG TinyUSB     ││  ESP32-BLE-Keyboard & Mouse  │
   │   Target: Windows / Mac / PC ││  Target: Android / iOS Phone │
   └──────────────┬───────────────┘└──────────────┬───────────────┘
                  │                               │
                  ▼                               ▼
   +--------------------------------------------------------------+
   |              PHYSICAL OR WIRELESS INJECTION STRIKE           |
   |   * Superhuman 1,200 WPM typing speed                        |
   |   * On-screen pointer tracks & clicks modal popup dialogs    |
   |   * Re-arm anytime via GPIO 0 BOOT button                    |
   +--------------------------------------------------------------+
```

---

## 📱 Cross-Platform Target Matrix

OmniDucky features tailored pipelines for every desktop and mobile operating system:

| Platform | Channel | Hotkey Launcher | Modal / Permission Bypass | On-Screen Mouse Cursor |
|---|---|---|---|---|
| **Android** | Wireless BLE | `[GUI]` + `[SPACE]` (Search) | `[TAB]` + `[ENTER]` + `MOUSE_POS_PCT 50 62` | Circular pointer appears automatically |
| **iOS / iPhone** | Wireless BLE | `[GUI]` + `[SPACE]` (Spotlight) | Native Alert focus (`[ENTER]`) | Circular dot via AssistiveTouch / Pointer |
| **Windows PC** | Wired USB-OTG | `[GUI]` + `[R]` (Run Dialog) | `[ALT]` + `[Y]` (UAC bypass) | Hardware mouse pointer active |
| **macOS** | Wired / BLE | `[GUI]` + `[SPACE]` (Spotlight) | `[ENTER]` (Default Action) | Native smooth macOS pointer |
| **Linux Desktop** | Wired USB-OTG | `[CTRL]` + `[ALT]` + `[T]` | Window Manager focus navigation | X11 / Wayland pointer |

---

## 🥊 How OmniDucky Compares

```
                               THE INDUSTRY LANDSCAPE
  ┌─────────────────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
  │ Feature                 │ OmniDucky 🦆 │ Hak5 Ducky   │ Flipper Zero │ Pico Ducky   │
  ├─────────────────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
  │ Hardware Cost           │ ~$4 - $5     │ $60 - $80    │ $169         │ $4           │
  │ Wired USB Keystrokes    │ YES (Native) │ YES          │ YES          │ YES          │
  │ Wireless Bluetooth BLE  │ YES (Native) │ NO           │ YES (Manual) │ NO           │
  │ Mobile Touch Simulation │ YES (Auto-%) │ NO           │ NO           │ NO           │
  │ Natural Language NLP    │ YES (Builtin)│ NO           │ NO           │ NO           │
  │ Web Studio IDE          │ YES (:8080)  │ Cloud/Manual │ NO           │ NO           │
  │ Hardware Corner Reset   │ YES (0,0)    │ NO           │ NO           │ NO           │
  └─────────────────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

---

## 🎨 Interactive Web Studio

OmniDucky provides a local web-based IDE that lets you design, simulate, and export firmware sketches.

```bash
python web_server.py
```
Open **[http://localhost:8080](http://localhost:8080)** in any browser.

```
  +-----------------------------------------------------------------------------+
  |  OMNIDUCKY WEB STUDIO                                    [ESP32-S3 READY]   |
  +-----------------------------------------------------------------------------+
  |  [ LEFT: Natural Language Prompt ]   |  [ RIGHT: DuckyScript Editor ]       |
  |  Target OS: [ Android 20:9 ▼ ]      |  Sample: [ Mobile App & Allow ▼ ]    |
  |                                      |                                      |
  |  1. Open Chrome                      |  REM Auto-generated DuckyScript      |
  |  2. Wait 2 seconds                   |  GUI SPACE                           |
  |  3. Type https://target.com          |  DELAY 800                           |
  |  4. Click allow                      |  STRING https://target.com           |
  |                                      |  ENTER                               |
  |  [ Convert to DuckyScript -> ]       |  MOUSE_POS_PCT 50 62                 |
  |                                      |  MOUSE_CLICK LEFT                    |
  |  ----------------------------------  |  ----------------------------------  |
  |  [🎮 Run Virtual Simulator]          |  [⚡ Generate Arduino .ino]          |
  +-----------------------------------------------------------------------------+
  |  [ LIVE HARDWARE SIMULATOR: Phone Mockup • Animated Cursor • Event Log ]    |
  +-----------------------------------------------------------------------------+
```

---

## ⌨️ DuckyScript Syntax & Mouse Extensions

OmniDucky implements standard DuckyScript syntax with additions for adaptive mouse positioning:

### Keyboard Hotkeys & Key Caps
```
  [ GUI ] + [ R ]       ──► Opens Windows Run Dialog
  [ GUI ] + [SPACE]     ──► Opens Mobile Search or macOS Spotlight
  [ CTRL ] + [ALT] + [DEL] ──► Security Screen
  [ TAB ]               ──► Shifts Modal Focus to Next Button
  [ ENTER ]             ──► Activates Focused Selection
```

### Full Command Reference

| Command | Action | Example |
|---|---|---|
| `REM <comment>` | Developer documentation | `REM Bypass mobile dialog` |
| `DELAY <ms>` | Precise pause in milliseconds | `DELAY 1500` |
| `DEFAULT_DELAY <ms>` | Automatic pacing between commands | `DEFAULT_DELAY 80` |
| `STRING <text>` | Types literal text at superhuman speed | `STRING powershell` |
| `STRINGLN <text>` | Types text and automatically hits Enter | `STRINGLN whoami` |
| `GUI <key>` | OS key combination (`WIN`, `CMD`, `SUPER`) | `GUI r` or `GUI SPACE` |
| `SCREEN_SIZE <w> <h>`| Calibrates physical target screen dimensions | `SCREEN_SIZE 1080 2400` |
| `MOUSE_POS_PCT <x> <y>`| Homes cursor to (0,0) and glides to % coords | `MOUSE_POS_PCT 50 62` |
| `MOUSE_MOVE <dx> <dy>`| Relative cursor movement delta | `MOUSE_MOVE 0 150` |
| `MOUSE_CLICK <btn>`  | Fires mouse button click (`LEFT`/`RIGHT`/`MID`)| `MOUSE_CLICK LEFT` |
| `MOUSE_SCROLL <val>` | Emulates mouse scroll wheel rotation | `MOUSE_SCROLL -5` |
| `REPEAT <count>`     | Repeats previous action N times | `REPEAT 3` |

---

## 🛠️ Setup & Flashing Guide

```
                HOW TO FLASH YOUR ESP32-S3 IN 4 STEPS
  1. Open Web Studio (http://localhost:8080) and click [Generate Arduino .ino]
  2. Install "ESP32 BLE Keyboard" by T-vK in Arduino IDE Library Manager
  3. Set Board to "ESP32S3 Dev Module" & USB Mode to "USB-OTG (TinyUSB)"
  4. Plug in your ESP32-S3 data cable and click Upload (->)
```

### Required Arduino IDE Settings

| Setting | Required Value | Critical Notes |
|---|---|---|
| **Board** | `ESP32S3 Dev Module` | Install `esp32` by Espressif in Boards Manager |
| **USB Mode** | **`USB-OTG (TinyUSB)`** | ⚠️ **Mandatory**: Enables native keyboard/mouse emulation |
| **USB CDC On Boot** | `Disabled` | Prevents serial port interception |
| **Upload Mode** | `UART0 / Hardware CDC` | Standard serial flashing protocol |

---

## 🧪 Verification & Test Certification

OmniDucky includes a test suite covering the parser, simulator, and generators:

```
=================================================================
  TOTAL VERIFIED AUTOMATED TEST RUNS : 1,255
  PASS RATE                          : 100.0% (1,255 / 1,255)
  EXECUTION TIME                     : ~0.04 seconds
  DEFECTS DETECTED                   : 0 (Zero Defects)
=================================================================
```

### Run Tests Locally
```bash
# Run baseline simulation suite
python tests/test_simulation_suite.py

# Run 100-case deep edge-case suite
python tests/edge_case_stress_suite.py

# Run 1,000-case mega stress test
python tests/stress_test_1000.py

# Verify cross-platform HID specifications
python tests/cross_platform_audit.py
```

---

## ⚖️ Legal Disclaimer

> **FOR AUTHORIZED SECURITY RESEARCH & EDUCATIONAL PURPOSES ONLY**
> 
> OmniDucky is created for authorized penetration testing, academic security analysis, red team assessments, and hardware education. Testing or deploying keystroke injection tools against computers, networks, or mobile devices without explicit written permission is unlawful under the US CFAA, UK Computer Misuse Act, Indian IT Act 2000, and regional cyber laws. The author assumes no responsibility for unauthorized misuse.

---

<div align="center">
  <sub>Developed by <b>Viswak Pullepu</b> &bull; Built with passion for open hardware security.</sub>
</div>
