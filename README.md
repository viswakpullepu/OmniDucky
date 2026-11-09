# 🦆 ESP32-S3 USB Rubber Ducky Toolkit

A DuckyScript-to-Arduino compiler that turns your **ESP32-S3** into a USB Rubber Ducky for authorized penetration testing and cybersecurity education.

> ⚠️ **LEGAL DISCLAIMER**: This tool is for **authorized security testing and educational purposes ONLY**. Using HID injection attacks on systems without explicit written permission is illegal under computer fraud laws (CFAA, IT Act 2000, GDPR, etc.). You are solely responsible for your actions.

---

## How It Works

```
DuckyScript (.duck)  →  Python Compiler  →  Arduino Sketch (.ino)  →  ESP32-S3 Flash  →  USB Keyboard Attack
```

1. You write a payload in **DuckyScript** (same language as Hak5 USB Rubber Ducky)
2. The **compiler** converts it to an Arduino sketch using ESP32-S3's native USB HID
3. You **flash** the sketch to your ESP32-S3 via Arduino IDE
4. When plugged into a target, the ESP32-S3 appears as a **USB keyboard** and injects keystrokes

---

## Requirements

### Software
- **Python 3.8+** (for the compiler)
- **Arduino IDE 2.x** (for flashing the ESP32-S3)
- **ESP32 Arduino Core** (installed via Board Manager)

### Hardware
- **ESP32-S3 Dev Board** (any variant with native USB — NOT the UART-only versions)
- **USB-C cable** (data cable, not charge-only)

---

## Quick Start

### 1. Launch the Web Studio (Natural Language &rarr; DuckyScript)

```bash
python web_server.py
```
Open **[http://localhost:8080](http://localhost:8080)** in your browser:
* Write plain human English instructions (e.g., *"Open notepad and type Hello"*, *"Open safari and go to example.com"*).
* Converts instantly to DuckyScript for Windows, Android, iOS, Mac, or Linux.
* One-click compile to **USB**, **BLE**, or **Dual-Mode** with instant `.ino` download.

---

### 2. Or Use the CLI Compiler

```bash
# List available example payloads
python cli.py list

# Compile the hello world test payload
python cli.py compile payloads/hello_world.duck

# Compile with custom output path
python cli.py compile payloads/hello_world.duck -o my_sketch.ino

# Validate syntax without compiling
python cli.py validate payloads/hello_world.duck
```

### 2. Arduino IDE Setup

```
1. Install Arduino IDE → https://www.arduino.cc/en/software

2. Add ESP32 board URL:
   File > Preferences > Additional Board Manager URLs:
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json

3. Install ESP32 boards:
   Tools > Board Manager > search "esp32" > Install "esp32 by Espressif"

4. Select board:
   Tools > Board > ESP32S3 Dev Module

5. CRITICAL USB settings:
   Tools > USB Mode:        "USB-OTG (TinyUSB)"
   Tools > USB CDC On Boot: "Disabled"
   Tools > Upload Mode:     "UART0 / Hardware CDC"
```

### 3. Flash & Run

1. Open the generated `.ino` file in Arduino IDE
2. Connect ESP32-S3 via USB
3. Click **Upload** (→ button)
4. Once flashed, **unplug** the ESP32-S3
5. **Plug it into the target** — payload runs automatically
6. Press the **BOOT button** (GPIO 0) to re-trigger

---

## DuckyScript Reference

| Command | Description | Example |
|---------|-------------|---------|
| `REM` | Comment (ignored) | `REM This is a comment` |
| `DELAY` | Wait N milliseconds | `DELAY 1000` |
| `STRING` | Type a string | `STRING Hello World` |
| `STRINGLN` | Type string + press Enter | `STRINGLN whoami` |
| `ENTER` | Press Enter key | `ENTER` |
| `GUI r` | Windows key + R | `GUI r` |
| `CTRL ALT DELETE` | Key combination | `CTRL ALT DELETE` |
| `ALT F4` | Alt + F4 | `ALT F4` |
| `TAB` | Press Tab | `TAB` |
| `ESCAPE` | Press Escape | `ESCAPE` |
| `UPARROW` | Arrow key | `UPARROW` |
| `F1`-`F12` | Function keys | `F5` |
| `REPEAT` | Repeat last command N times | `REPEAT 3` |
| `DEFAULT_DELAY` | Add delay between all commands | `DEFAULT_DELAY 100` |

---

## Example Payloads

### Hello World (Test)
```
DELAY 1000
GUI r
DELAY 500
STRING notepad
ENTER
DELAY 800
STRING Hello from ESP32-S3 Ducky!
```

### Custom Payload Template
```
REM My Custom Payload
REM Description of what it does

DELAY 1000

REM Open Run dialog
GUI r
DELAY 500

REM Type command
STRING <your command here>
ENTER
```

---

## Project Structure

```
esp32-ducky/
├── cli.py                              # Main CLI tool
├── compiler/
│   ├── __init__.py
│   ├── keycodes.py                     # USB HID keycode mappings
│   ├── duckyscript_parser.py           # DuckyScript lexer/parser
│   └── arduino_generator.py           # Arduino code generator
├── payloads/
│   ├── hello_world.duck               # Basic test
│   ├── sysinfo_windows.duck           # System info grabber
│   ├── reverse_shell.duck             # Reverse shell (lab only)
│   ├── rickroll.duck                  # Harmless prank
│   └── disable_defender.duck          # Disable AV (lab only)
└── README.md
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| ESP32-S3 not detected | Use a **data** USB cable, not charge-only |
| Upload fails | Hold **BOOT** button while clicking Upload |
| Keyboard not recognized | Ensure USB Mode is set to **USB-OTG (TinyUSB)** |
| Wrong characters typed | Check keyboard layout — this uses US layout |
| Payload too fast | Add more `DELAY` commands between steps |
| Want to stop payload | Unplug the ESP32-S3 immediately |

---

## Extending

- **Add BLE support**: ESP32-S3 also supports Bluetooth HID — pair wirelessly as a keyboard
- **Add mass storage**: Emulate a USB drive + keyboard simultaneously for data exfiltration
- **OS detection**: Use Caps Lock LED response to detect Windows/Mac/Linux
- **Encode payloads**: Obfuscate payload strings to avoid AV detection

---

## Legal

This tool is provided for **educational and authorized security testing purposes only**. The authors are not responsible for any misuse. Always obtain **written permission** before testing any system you do not own.
