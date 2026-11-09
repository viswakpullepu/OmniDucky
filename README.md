<div align="center">

```
  ____                  _ _____             _           
 / __ \                (_)  __ \           | |          
| |  | |_ __ ___  _ __  _| |  | |_   _  ___| | ___   _  
| |  | | '_ ` _ \| '_ \| | |  | | | | |/ __| |/ / | | | 
| |__| | | | | | | | | | | |__| | |_| | (__|   <| |_| | 
 \____/|_| |_| |_|_| |_|_|_____/ \__,_|\___|_|\_\\__, | 
                                                  __/ | 
                                                 |___/  
```

# 🦆 OmniDucky

### Next-Generation ESP32-S3 Keystroke Injection & Wireless HID Exploitation Toolkit

[![ESP32-S3](https://img.shields.io/badge/Hardware-ESP32--S3-E7352C?style=for-the-badge&logo=espressif&logoColor=white)](https://www.espressif.com/)
[![Language](https://img.shields.io/badge/Language-Python%20%7C%20C%2B%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Platform](https://img.shields.io/badge/Target-Android%20%7C%20iOS%20%7C%20Windows%20%7C%20macOS%20%7C%20Linux-green?style=for-the-badge)](https://github.com/viswakpullepu/OmniDucky)
[![Web Studio](https://img.shields.io/badge/Web%20Studio-Localhost:8080-purple?style=for-the-badge)](http://localhost:8080)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

<p align="center">
  <b>Turn any $5 ESP32-S3 board into a military-grade USB & Bluetooth Rubber Ducky.</b><br>
  Speak to it in plain human language &bull; Compile for PC & Mobile &bull; Physical Mouse & Keyboard Emulation
</p>

---

[Key Features](#-key-features) &bull;
[Architecture](#-system-architecture) &bull;
[Web Studio](#-web-studio) &bull;
[Mobile Attack Vectors](#-mobile-targeting-android--ios) &bull;
[Quickstart](#-quickstart) &bull;
[DuckyScript Reference](#-duckyscript-syntax--mouse-extensions) &bull;
[Flashing Guide](#-flashing-your-esp32-s3) &bull;
[Disclaimer](#-legal-disclaimer)

---

</div>

## ⚡ Key Features

* 🧠 **Natural Language to DuckyScript Engine**: Type plain human commands like *"Open Chrome, wait 2 seconds, click allow, and type Hello"* — the parser converts it into synchronized, platform-specific DuckyScript automatically.
* 📶 **Dual-Channel HID Attack Vectors**:
  * **Wired USB HID**: Plug directly into any PC/Mac/Linux workstation for sub-second payload execution.
  * **Wireless BLE HID**: Emulates an authentic Bluetooth Keyboard & Mouse (e.g., *"Logitech K380"*). Silently executes upon pairing with **Android phones**, **iPhones**, tablets, or laptops from up to 10 meters away.
  * **Dual-Mode**: Runs both wired USB and wireless Bluetooth injection vectors simultaneously.
* 🖱️ **Adaptive Mouse & Touch Emulation**:
  * Full relative and normalized coordinate mouse control (`MOUSE_MOVE`, `MOUSE_CLICK`, `MOUSE_SCROLL`).
  * **Hardware Corner-Reset Auto-Homing**: Re-zeros cursor drift to `(0, 0)` before stepping accurately to button targets.
  * **Dynamic Screen Resolution Scaling**: Automatically maps percentage coordinates (`MOUSE_POS_PCT`) to target display sizes (1080p, 1440p, 20:9 phone displays, Retina displays).
  * **Smart Modal Auto-Accept**: Combines accessibility keyboard navigation (`TAB` + `ENTER`) with calibrated screen clicks to accept permission dialogs on mobile devices.
* 🖥️ **Built-in Web Studio**: A sleek, dark-mode dashboard running locally at `http://localhost:8080` with real-time translation, device presets, payload library, and instant `.ino` sketch generation.
* 🔒 **Zero Telemetry & 100% Offline**: No cloud APIs, no external telemetry, and no AI overhead on the microcontroller. The ESP32-S3 runs high-speed bare-metal C++ firmware.

---

## 🏛️ System Architecture

```
                    ┌───────────────────────────────────────────────┐
                    │            HUMAN OPERATOR / WEB UI            │
                    │   "Open browser, go to URL, click Allow"     │
                    └───────────────────────┬───────────────────────┘
                                            │
                                            ▼
                    ┌───────────────────────────────────────────────┐
                    │        NATURAL LANGUAGE PARSER (NLP)          │
                    │      compiler/nlp_converter.py                │
                    └───────────────────────┬───────────────────────┘
                                            │
                                            ▼
                    ┌───────────────────────────────────────────────┐
                    │               DUCKYSCRIPT IR                  │
                    │   GUI SPACE -> STRING URL -> MOUSE_POS_PCT    │
                    └───────────────────────┬───────────────────────┘
                                            │
               ┌────────────────────────────┴────────────────────────────┐
               ▼                                                         ▼
┌───────────────────────────────┐                         ┌───────────────────────────────┐
│       USB HID GENERATOR       │                         │       BLE HID GENERATOR       │
│    Native TinyUSB (PC/Mac)    │                         │  Wireless Keyboard & Mouse    │
└──────────────┬────────────────┘                         └──────────────┬────────────────┘
               │                                                         │
               └────────────────────────────┬────────────────────────────┘
                                            │
                                            ▼
                    ┌───────────────────────────────────────────────┐
                    │         ESP32-S3 FIRMWARE (.INO)              │
                    │      High-speed bare-metal execution          │
                    └───────────────────────┬───────────────────────┘
                                            │
                    ┌───────────────────────┴───────────────────────┐
                    ▼                                               ▼
         ┌─────────────────────┐                         ┌─────────────────────┐
         │     TARGET PC       │                         │    TARGET PHONE     │
         │ Windows/macOS/Linux │                         │   Android / iOS     │
         └─────────────────────┘                         └─────────────────────┘
```

---

## 🎨 Web Studio

OmniDucky includes a built-in web-based IDE that lets you design, translate, and compile payloads in seconds.

To start the studio:
```bash
python web_server.py
```
Then open **[http://localhost:8080](http://localhost:8080)** in your browser.

<div align="center">

| Feature | Description |
|---|---|
| **Natural Language Studio** | Type instructions in plain English; watch them compile into DuckyScript in real-time. |
| **Target OS Presets** | One-click presets for Windows, macOS, Linux, Android, and iOS. |
| **Screen Resolution Calibrator** | Preset resolutions for standard Android (1080x2400), iPhone (1170x2532), and PC monitors. |
| **HID Profile Switcher** | Select Wired USB, Wireless BLE, or Dual-Mode with customizable Bluetooth device names. |
| **Instant Arduino Export** | View generated C++ code live, copy with one click, or download the `.ino` file ready for flashing. |

</div>

---

## 📱 Mobile Targeting (Android & iOS)

Standard USB Rubber Duckies only work when plugged into a PC. **OmniDucky redefines this** by turning your ESP32-S3 into a wireless Bluetooth peripheral that mobile devices eagerly accept.

### How It Works:
1. **Device Masquerading**: The ESP32-S3 advertises as a benign peripheral like `"Logitech K380"` or `"Wireless Keyboard"`.
2. **Instant Pairing**: When the victim connects or pairs from Bluetooth settings, the payload executes automatically.
3. **App Launching**:
   * **iOS**: Sends `GUI SPACE` (Cmd + Space) to trigger **Spotlight Search**, launches Safari or notes, and executes commands.
   * **Android**: Uses `GUI SPACE` or `GUI b` to access system search and the default browser.
4. **Adaptive Permission Dialog Bypass**:
   * Mobile permission dialogs ("Allow location", "Allow notifications") block pure keyboard commands.
   * OmniDucky uses an **adaptive dual strategy**:
     1. Injects `TAB` &rarr; `TAB` &rarr; `ENTER` to shift accessibility focus directly to affirmative buttons.
     2. Simulates an on-screen mouse pointer that auto-homes to `(0, 0)` and clicks the calibrated modal dialog coordinates (`MOUSE_POS_PCT 50 62`).

---

## 🚀 Quickstart

### 1. Clone the Repository
```bash
git clone https://github.com/viswakpullepu/OmniDucky.git
cd OmniDucky
```

### 2. Compile via CLI
```bash
# List example payloads
python cli.py list

# Compile for PC (Wired USB)
python cli.py compile payloads/hello_world.duck --target usb

# Compile for Mobile (Bluetooth BLE) with disguised device name
python cli.py compile payloads/mobile_mouse_allow.duck --target ble --name "Logitech K380"

# Compile for Dual-Mode (USB + BLE)
python cli.py compile payloads/hello_world.duck --target dual --name "DualDucky"
```

---

## 📝 DuckyScript Syntax & Mouse Extensions

OmniDucky supports standard DuckyScript alongside custom mouse and calibration extensions:

### Keyboard Commands
| Command | Action | Example |
|---|---|---|
| `REM` | Comment / annotation | `REM Open shell` |
| `DELAY <ms>` | Wait specified milliseconds | `DELAY 1000` |
| `DEFAULT_DELAY <ms>` | Delay between every command | `DEFAULT_DELAY 100` |
| `STRING <text>` | Type literal string | `STRING notepad` |
| `STRINGLN <text>` | Type string + press Enter | `STRINGLN whoami` |
| `ENTER` | Press Enter / Return key | `ENTER` |
| `GUI <key>` | Windows / Command key combo | `GUI r` or `GUI SPACE` |
| `CTRL ALT DELETE` | Multi-modifier shortcut | `CTRL ALT DELETE` |
| `REPEAT <n>` | Repeat previous command N times | `REPEAT 5` |

### Mouse & Adaptive Calibration Extensions
| Command | Action | Example |
|---|---|---|
| `SCREEN_SIZE <w> <h>` | Sets target device resolution for percentage scaling | `SCREEN_SIZE 1080 2400` |
| `MOUSE_POS_PCT <x> <y>` | Homes cursor to (0,0) and moves to % of screen | `MOUSE_POS_PCT 50 62` |
| `MOUSE_MOVE <x> <y>` | Relative cursor movement in pixels | `MOUSE_MOVE 0 150` |
| `MOUSE_CLICK <btn>` | Click mouse button (`LEFT`, `RIGHT`, `MIDDLE`) | `MOUSE_CLICK LEFT` |
| `MOUSE_SCROLL <val>` | Scroll mouse wheel up or down | `MOUSE_SCROLL -5` |

---

## 🔧 Flashing Your ESP32-S3

### 1. Prepare Arduino IDE
1. Download [Arduino IDE 2.x](https://www.arduino.cc/en/software).
2. Go to **File > Preferences > Additional Boards Manager URLs** and add:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
3. Open **Tools > Board > Boards Manager**, search for `esp32` by Espressif, and install it.
4. *(For Bluetooth Mode)*: Open **Sketch > Include Library > Manage Libraries**, search for `ESP32 BLE Keyboard` by **T-vK**, and click **Install**. (Optionally install `ESP32 BLE Mouse` if utilizing Bluetooth mouse features).

### 2. Configure Board Options
Under the **Tools** menu, select the following:
* **Board**: `ESP32S3 Dev Module`
* **USB Mode**: `USB-OTG (TinyUSB)` ⚠️ *(Crucial for USB HID functionality)*
* **USB CDC On Boot**: `Disabled`
* **Upload Mode**: `UART0 / Hardware CDC`

### 3. Flash & Execute
1. Open your generated `.ino` file in Arduino IDE.
2. Connect your ESP32-S3 via a **data USB-C cable**.
3. Click **Upload** (hold the `BOOT` button if flashing fails to initialize).
4. **Arm & Strike**:
   * For USB: Unplug and plug into target machine. Keystrokes execute automatically.
   * For BLE: Turn on the ESP32-S3, pair from target phone's Bluetooth settings, and enjoy autonomous payload execution.
   * Press the `BOOT` button (GPIO 0) at any time to re-trigger the payload.

---

## 📁 Repository Structure

```
OmniDucky/
├── cli.py                     # Command-line interface & compiler
├── web_server.py              # Web Studio local server (port 8080)
├── compiler/
│   ├── __init__.py
│   ├── keycodes.py            # HID keycode definitions & mappings
│   ├── duckyscript_parser.py  # DuckyScript tokenization & IR parser
│   ├── arduino_generator.py   # Wired USB HID sketch generator
│   ├── ble_generator.py       # Wireless Bluetooth BLE sketch generator
│   ├── dual_generator.py      # Dual-mode USB+BLE sketch generator
│   └── nlp_converter.py       # Natural Language translation engine
├── payloads/                  # Ready-to-use sample payloads
│   ├── hello_world.duck       # Basic PC test
│   ├── sysinfo_windows.duck   # Reconnaissance & system audit
│   ├── mobile_browser_open.duck # Mobile browser opener
│   ├── mobile_notes_test.duck # Mobile BLE typing test
│   ├── mobile_mouse_allow.duck# Mobile app launch & modal accept
│   ├── rickroll.duck          # Harmless browser prank
│   └── reverse_shell.duck     # Lab environment reverse shell
└── README.md
```

---

## ⚖️ Legal Disclaimer

> **IMPORTANT**: OmniDucky is developed solely for **authorized penetration testing**, **academic research**, and **educational demonstrations**.
> 
> Executing keystroke injection or unauthorized access against computer systems or mobile devices without prior explicit written permission is strictly prohibited by law (including the Computer Fraud and Abuse Act (CFAA), the UK Computer Misuse Act, the Indian Information Technology Act 2000, and equivalent regional legislation). The developers assume no liability for misuse or damage caused by this software.

---

<div align="center">
  <sub>Engineered by <b>Viswak Pullepu</b> &bull; Built with passion for hardware hacking and offensive security research.</sub>
</div>
