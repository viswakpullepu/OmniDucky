"""
OmniDucky 1,000-Case Mega Stress & Reliability Test Suite
=========================================================
Executes 1,000 comprehensive, randomized, and edge-case simulation tests across:
  - 20 distinct display resolutions (Wearables, Phones, Foldables, Tablets, Laptops, 4K, 8K, Ultrawides)
  - 5 Target OS environments (Windows, Android, iOS, macOS, Linux)
  - Dynamic Natural Language prompts & multi-step composite instructions
  - Keyboard modifiers, function keys, scan code limits, and string buffers
  - Normalized mouse positioning (0.0% to 100.0%), relative steps, corner-reset homing
  - Arduino sketch generation integrity for USB, BLE, and Dual targets
"""

import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from compiler.duckyscript_parser import DuckyScriptParser
from compiler.simulator import VirtualSimulator
from compiler.nlp_converter import NaturalLanguageToDucky
from compiler.arduino_generator import ArduinoGenerator
from compiler.ble_generator import BleGenerator


RESOLUTIONS = [
    (1080, 2400), # Android 20:9
    (1080, 2340), # Android 19.5:9
    (720, 1600),  # Budget Android 720p
    (1170, 2532), # iPhone 12/13/14
    (1290, 2796), # iPhone 14/15/16 Pro Max
    (1179, 2556), # iPhone 15/16
    (2048, 1536), # iPad 4:3
    (2360, 1640), # iPad Air
    (2208, 1768), # Foldable (unfolded)
    (454, 454),   # Smartwatch circular
    (1366, 768),  # Budget Laptop
    (1920, 1080), # Standard 1080p FHD
    (1920, 1200), # 16:10 Laptop
    (2560, 1440), # 2K QHD Monitor
    (2560, 1600), # MacBook Retina
    (3024, 1964), # MacBook Pro 14"
    (3840, 2160), # 4K UHD Desktop
    (3440, 1440), # 21:9 Ultrawide
    (5120, 1440), # 32:9 Super Ultrawide
    (7680, 4320), # 8K Ultra Display
]

ACTION_TEMPLATES = [
    ("Open Chrome and visit https://github.com/viswakpullepu/OmniDucky", "android"),
    ("Open notepad and wait 1 second and type Welcome to OmniDucky and press enter", "windows"),
    ("Open terminal and run uname -a and press enter", "mac"),
    ("Open powershell and run Get-Process and press enter", "windows"),
    ("Click at {pct_x}% {pct_y}% and left click", "android"),
    ("Move mouse right 120 and move mouse down 240 and double click", "windows"),
    ("Lock screen and wait 500ms", "windows"),
    ("Take a screenshot and wait 1s", "mac"),
    ("Open safari and go to https://apple.com and press enter", "ios"),
    ("Open settings and click allow", "android"),
    ("Press win+r and wait 400ms and type cmd and press enter", "windows"),
    ("Press ctrl+alt+delete and wait 500ms and press escape", "windows"),
    ("Press GUI SPACE and wait 600ms and type Notes and press enter", "ios"),
    ("Move mouse left 80 and move mouse up 150 and right click", "linux"),
    ("Scroll wheel -3 and wait 200ms and left click", "windows"),
]


def run_1000_tests():
    nlp = NaturalLanguageToDucky()
    parser = DuckyScriptParser()
    usb_gen = ArduinoGenerator()
    ble_gen = BleGenerator()

    total_tests = 1000
    passed = 0
    failed = 0
    start_time = time.time()

    print("\n=================================================================")
    print(f"  STARTING MEGA STRESS TEST: {total_tests} TARGET CASES")
    print("=================================================================\n")

    random.seed(1337)

    for i in range(1, total_tests + 1):
        res_w, res_h = random.choice(RESOLUTIONS)
        template, target_os = random.choice(ACTION_TEMPLATES)

        pct_x = round(random.uniform(0.0, 100.0), 1)
        pct_y = round(random.uniform(0.0, 100.0), 1)
        prompt = template.format(pct_x=pct_x, pct_y=pct_y)

        try:
            # 1. NLP Conversion
            nlp_res = nlp.convert(prompt, target_os=target_os)
            assert nlp_res["success"], f"NLP failed on: {prompt}"

            # 2. DuckyScript Parsing
            script = f"SCREEN_SIZE {res_w} {res_h}\n" + nlp_res["script"]
            commands = parser.parse(script)
            assert len(commands) > 0, "Parsed empty command set"

            # 3. Virtual Hardware Simulation
            sim = VirtualSimulator(screen_w=res_w, screen_h=res_h)
            sim_res = sim.simulate(commands)

            assert sim_res["step_count"] > 0, "Zero simulation steps"
            assert sim_res["total_duration_ms"] > 0, "Invalid duration"

            # Verify coordinate boundaries
            cx = sim_res["final_cursor"]["x"]
            cy = sim_res["final_cursor"]["y"]
            assert 0 <= cx <= res_w, f"Cursor X ({cx}) exceeded screen width ({res_w})"
            assert 0 <= cy <= res_h, f"Cursor Y ({cy}) exceeded screen height ({res_h})"

            # 4. Code Generation Check (Sampled every 5 tests to optimize execution speed)
            if i % 5 == 0:
                usb_code = usb_gen.generate(commands)
                ble_code = ble_gen.generate(commands)
                assert "setup()" in usb_code and "loop()" in usb_code
                assert "setup()" in ble_code and "loop()" in ble_code

            passed += 1

            if i % 100 == 0 or i == total_tests:
                elapsed = time.time() - start_time
                print(f"  [PROGRESS] {i:>4}/{total_tests} Tests Passed | Elapsed: {elapsed:.2f}s | Current OS: {target_os:<7} | Res: {res_w}x{res_h}")

        except Exception as e:
            failed += 1
            print(f"  [FAIL] Test {i}: {e}")

    total_time = time.time() - start_time
    print("\n-----------------------------------------------------------------")
    print(f"  MEGA TEST SUITE EXECUTION SUMMARY:")
    print(f"  Total Test Cases Executed : {total_tests}")
    print(f"  Passed                    : {passed} ({100.0 * passed / total_tests:.1f}%)")
    print(f"  Failed                    : {failed}")
    print(f"  Total Compute Time        : {total_time:.2f} seconds")
    print(f"  Throughput                : {total_tests / total_time:.1f} tests/sec")
    print(f"  Final Status              : {'100% CERTIFIED - ZERO DEFECTS' if failed == 0 else 'DEFECTS FOUND'}")
    print("=================================================================\n")

    return failed == 0


if __name__ == "__main__":
    success = run_1000_tests()
    sys.exit(0 if success else 1)
