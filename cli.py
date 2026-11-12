#!/usr/bin/env python3
"""
ESP32-S3 Ducky Toolkit - CLI
=============================
A DuckyScript compiler that generates Arduino sketches for the ESP32-S3
to turn it into a USB, BLE, or Dual-Mode Rubber Ducky (supporting PCs, Android, and iOS).

Usage:
    python cli.py compile <payload.duck>                       # USB mode (default)
    python cli.py compile <payload.duck> --target ble          # Bluetooth mode (Phones/Tablets/PCs)
    python cli.py compile <payload.duck> --target dual         # Dual USB + BLE mode
    python cli.py compile <payload.duck> --name "Logitech K380" # Disguise BLE device name
    python cli.py list                                         # List example payloads
    python cli.py validate <payload.duck>                      # Check syntax only
    python cli.py info                                         # Setup instructions

Author:  Cybersecurity Student Toolkit
License: Educational use only - authorized testing ONLY.
"""

import argparse
import os
import sys
from pathlib import Path

from compiler.duckyscript_parser import DuckyScriptParser
from compiler.arduino_generator import ArduinoGenerator
from compiler.ble_generator import BleGenerator
from compiler.dual_generator import DualModeGenerator
from compiler.simulator import VirtualSimulator


PAYLOADS_DIR = Path(__file__).parent / "payloads"

BANNER = r"""
  +=================================================+
  |      ESP32-S3 USB & BLE Rubber Ducky Toolkit    |
  |      -----------------------------------------  |
  |      DuckyScript -> Arduino Compiler            |
  |      Targets: USB (PC) | BLE (Mobile & PC)      |
  |      For AUTHORIZED testing only.               |
  +=================================================+
"""

SETUP_INFO = """
===================================================
  ESP32-S3 SETUP GUIDE (USB & BLUETOOTH)
===================================================

  1. INSTALL ARDUINO IDE
     > https://www.arduino.cc/en/software

  2. ADD ESP32 BOARD SUPPORT
     > File > Preferences > Additional Board URLs:
       https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
     > Tools > Board Manager > search "esp32" > Install

  3. FOR BLUETOOTH (BLE) MODE (Mobile & PC):
     > Sketch > Include Library > Manage Libraries
     > Search "ESP32 BLE Keyboard" by T-vK > Install

  4. SELECT YOUR BOARD
     > Tools > Board > ESP32S3 Dev Module

  5. CRITICAL USB/FLASH SETTINGS
     > Tools > USB Mode:         "USB-OTG (TinyUSB)" (Required for USB & Dual)
     > Tools > USB CDC On Boot:  "Disabled"
     > Tools > Upload Mode:      "UART0 / Hardware CDC"

  6. UPLOAD & TARGETS:
     - USB Mode:  Plug directly into host PC.
     - BLE Mode:  Pair from Android, iOS, or PC via Bluetooth settings.
                  Payload triggers on successful connection.
     - Re-trigger: Press BOOT button (GPIO 0).

===================================================
"""


def cmd_compile(args):
    """Compile a DuckyScript file to an Arduino sketch."""
    payload_path = Path(args.payload)
    if not payload_path.exists():
        print(f"[ERROR] Payload file not found: {payload_path}")
        sys.exit(1)

    source = payload_path.read_text(encoding="utf-8")

    # Parse
    parser = DuckyScriptParser()
    try:
        commands = parser.parse(source)
    except SyntaxError as e:
        print(f"[SYNTAX ERROR]\n{e}")
        sys.exit(1)

    print(f"[OK] Parsed {len(commands)} commands from {payload_path.name}")

    target = args.target.lower()
    dev_name = args.name or "Wireless Keyboard"

    if target == "ble":
        generator = BleGenerator(device_name=dev_name)
        arduino_code = generator.generate(commands, default_delay=parser.default_delay)
        mode_label = f"BLE HID Keyboard (Name: '{dev_name}')"
    elif target == "dual":
        generator = DualModeGenerator(device_name=dev_name)
        arduino_code = generator.generate(commands, default_delay=parser.default_delay)
        mode_label = f"Dual Mode (USB + BLE: '{dev_name}')"
    else:
        generator = ArduinoGenerator()
        arduino_code = generator.generate(commands, default_delay=parser.default_delay)
        mode_label = "USB HID Keyboard"

    # Output
    if args.output:
        output_path = Path(args.output)
    else:
        suffix = f"_{target}.ino" if target != "usb" else ".ino"
        output_path = payload_path.with_name(payload_path.stem + suffix)

    output_path.write_text(arduino_code, encoding="utf-8")
    print(f"[OK] Target Mode: {mode_label}")
    print(f"[OK] Generated Arduino sketch: {output_path}")
    print(f"[OK] Open in Arduino IDE and upload to your ESP32-S3")


def cmd_simulate(args):
    """Run virtual simulation of a payload without hardware."""
    payload_path = Path(args.payload)
    if not payload_path.exists():
        print(f"[ERROR] Payload file not found: {payload_path}")
        sys.exit(1)

    source = payload_path.read_text(encoding="utf-8")
    parser = DuckyScriptParser()
    try:
        commands = parser.parse(source)
    except SyntaxError as e:
        print(f"[SYNTAX ERROR]\n{e}")
        sys.exit(1)

    screen_w, screen_h = 1080, 2400
    if args.res:
        parts = args.res.split("x")
        if len(parts) == 2:
            screen_w, screen_h = int(parts[0]), int(parts[1])

    sim = VirtualSimulator(screen_w=screen_w, screen_h=screen_h)
    result = sim.simulate(commands, default_delay=parser.default_delay)

    print(f"\n=======================================================")
    print(f"  VIRTUAL EXECUTION SIMULATION: {payload_path.name}")
    print(f"  Target Resolution: {result['screen_size']['width']}x{result['screen_size']['height']}")
    print(f"=======================================================")
    for step in result["timeline"]:
        ch = f"[{step['channel']:<8}]"
        print(f"  {step['time_formatted']:<7} {ch} {step['description']}")
    print(f"-------------------------------------------------------")
    print(f"  Total Estimated Duration : {result['total_duration_sec']}s")
    print(f"  Total Executed Actions   : {result['step_count']}")
    print(f"  Final Cursor Position    : ({result['final_cursor']['x']}px, {result['final_cursor']['y']}px)")
    print(f"=======================================================\n")


def cmd_validate(args):
    """Validate DuckyScript syntax without generating code."""
    payload_path = Path(args.payload)
    if not payload_path.exists():
        print(f"[ERROR] Payload file not found: {payload_path}")
        sys.exit(1)

    source = payload_path.read_text(encoding="utf-8")
    parser = DuckyScriptParser()

    try:
        commands = parser.parse(source)
        print(f"[VALID] {payload_path.name} - {len(commands)} commands, no errors.")
    except SyntaxError as e:
        print(f"[INVALID]\n{e}")
        sys.exit(1)


def cmd_list(args):
    """List available example payloads."""
    if not PAYLOADS_DIR.exists():
        print("[WARN] No payloads directory found.")
        return

    duck_files = sorted(PAYLOADS_DIR.glob("*.duck"))
    if not duck_files:
        print("[INFO] No .duck payload files found.")
        return

    print("\n  Available Example Payloads:")
    print("  " + "-" * 55)
    for f in duck_files:
        desc = ""
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.startswith("REM "):
                desc = line[4:]
                break
        print(f"  > {f.name:<28} {desc}")

    print(f"\n  Compile USB:  python cli.py compile payloads/<file>")
    print(f"  Compile BLE:  python cli.py compile payloads/<file> --target ble")
    print(f"  Compile Dual: python cli.py compile payloads/<file> --target dual")
    print()


def cmd_info(args):
    """Print setup instructions."""
    print(SETUP_INFO)


def main():
    print(BANNER)

    parser = argparse.ArgumentParser(
        description="ESP32-S3 USB & BLE Rubber Ducky Toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # compile
    p_compile = subparsers.add_parser("compile", help="Compile DuckyScript to Arduino .ino")
    p_compile.add_argument("payload", help="Path to .duck payload file")
    p_compile.add_argument("-o", "--output", help="Output .ino file path")
    p_compile.add_argument(
        "--target",
        choices=["usb", "ble", "dual"],
        default="usb",
        help="Target HID interface: usb, ble (mobile/PC), or dual (default: usb)",
    )
    p_compile.add_argument(
        "--name",
        default="Wireless Keyboard",
        help="Bluetooth advertised name (for ble/dual targets)",
    )
    p_compile.set_defaults(func=cmd_compile)

    # simulate
    p_sim = subparsers.add_parser("simulate", help="Virtually simulate payload timing & actions")
    p_sim.add_argument("payload", help="Path to .duck payload file")
    p_sim.add_argument("--res", default="1080x2400", help="Screen resolution (e.g. 1080x2400 or 1920x1080)")
    p_sim.set_defaults(func=cmd_simulate)

    # validate
    p_validate = subparsers.add_parser("validate", help="Validate DuckyScript syntax")
    p_validate.add_argument("payload", help="Path to .duck payload file")
    p_validate.set_defaults(func=cmd_validate)

    # list
    p_list = subparsers.add_parser("list", help="List example payloads")
    p_list.set_defaults(func=cmd_list)

    # info
    p_info = subparsers.add_parser("info", help="Show ESP32-S3 setup guide")
    p_info.set_defaults(func=cmd_info)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
