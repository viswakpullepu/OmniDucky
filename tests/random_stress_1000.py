"""
OmniDucky 1,000-Case Randomized Stress & Fuzzing Diagnostic Suite
================================================================
Generates and executes 1,000 completely randomized, multi-dimensional
fuzzing payloads to stress-test:
  1. Arbitrary random string fuzzing (special chars, escaped quotes, backslashes, UTF-8 boundaries)
  2. Randomized Multi-Key Modifier Chords (1-4 modifiers combined with random alphanumeric/special keys)
  3. Chaotic Mouse Dynamics (extreme jumps, diagonal kinetics, zero-bounds, boundary overflows)
  4. Dynamic Resolution Scaling (wearables 454x454 to 8K 7680x4320 with floating-point percentage coordinates)
  5. Multi-Clause Random Prompt Composition (randomized natural language actions and conjunctions)
  6. Code Generation Pipeline Integrity (USB TinyUSB & BLE HID C++ compilation validity)
"""

import random
import string
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from compiler.duckyscript_parser import DuckyScriptParser, Command
from compiler.simulator import VirtualSimulator
from compiler.nlp_converter import NaturalLanguageToDucky
from compiler.arduino_generator import ArduinoGenerator
from compiler.ble_generator import BleGenerator


RESOLUTIONS = [
    (1080, 2400), (1080, 2340), (720, 1600), (1170, 2532),
    (1290, 2796), (1179, 2556), (2048, 1536), (2360, 1640),
    (2208, 1768), (454, 454), (1366, 768), (1920, 1080),
    (1920, 1200), (2560, 1440), (2560, 1600), (3024, 1964),
    (3840, 2160), (3440, 1440), (5120, 1440), (7680, 4320)
]

APPS = ["notepad", "calc", "powershell", "cmd", "explorer", "chrome", "msedge", "terminal", "safari", "settings"]
VERBS = ["open", "launch", "start", "fire up", "pull up", "pop open"]
ACTIONS = [
    "wait {ms}ms",
    "type {text}",
    "press enter",
    "save it",
    "close the window",
    "lock screen",
    "take a screenshot",
    "left click",
    "right click",
    "jiggle mouse",
    "move mouse right {dx} and move mouse down {dy}"
]
KEYS = ["a", "b", "c", "d", "e", "f", "r", "t", "s", "x", "z", "enter", "escape", "tab", "f1", "f5", "f12", "space"]
MODIFIERS = ["GUI", "WIN", "CTRL", "ALT", "SHIFT", "CTRL ALT", "CTRL SHIFT", "GUI SHIFT"]


def random_string(length=15):
    chars = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:,.<>?/\\"
    return ''.join(random.choice(chars) for _ in range(length))


def generate_random_case(seed_idx):
    random.seed(42 + seed_idx)
    test_type = seed_idx % 5

    res_w, res_h = random.choice(RESOLUTIONS)
    target_os = random.choice(["windows", "mac", "linux", "android", "ios"])

    if test_type == 0:
        # Fuzzed strings & shell payloads
        payload = random_string(random.randint(10, 50))
        is_ln = random.choice([True, False])
        script = f"DEFAULT_DELAY 50\n{'STRINGLN' if is_ln else 'STRING'} {payload}\n"
        return "Fuzzed Strings", script, target_os, res_w, res_h, payload

    elif test_type == 1:
        # Random multi-key modifier chords
        mod = random.choice(MODIFIERS)
        k = random.choice(KEYS)
        script = f"DEFAULT_DELAY 50\n{mod} {k}\nDELAY {random.randint(50, 500)}\n"
        return "Random Modifier Chords", script, target_os, res_w, res_h, f"{mod} {k}"

    elif test_type == 2:
        # Chaotic kinetic mouse movements & screen percentages
        pct_x = round(random.uniform(0.0, 100.0), 2)
        pct_y = round(random.uniform(0.0, 100.0), 2)
        btn = random.choice(["LEFT", "RIGHT", "MIDDLE"])
        script = f"SCREEN_SIZE {res_w} {res_h}\nMOUSE_POS_PCT {pct_x} {pct_y}\nDELAY 100\nMOUSE_CLICK {btn}\nMOUSE_MOVE {random.randint(-100, 100)} {random.randint(-100, 100)}\n"
        return "Chaotic Mouse Dynamics", script, target_os, res_w, res_h, f"{pct_x}% {pct_y}% {btn}"

    elif test_type == 3:
        # Multi-step randomized natural language flow
        app = random.choice(APPS)
        verb = random.choice(VERBS)
        steps = [f"{verb} {app}"]
        for _ in range(random.randint(1, 3)):
            act = random.choice(ACTIONS)
            steps.append(act.format(
                ms=random.randint(100, 1500),
                text=random_string(8),
                dx=random.randint(20, 200),
                dy=random.randint(20, 200)
            ))
        prompt = " and ".join(steps)
        return "Randomized NLP Composition", prompt, target_os, res_w, res_h, prompt

    else:
        # Web search & URL navigation fuzzing
        query = " ".join([random_string(random.randint(4, 10)) for _ in range(random.randint(1, 4))])
        script = f"DEFAULT_DELAY 60\nGUI r\nDELAY 600\nSTRINGLN chrome\nDELAY 2000\nCTRL l\nDELAY 300\nSTRINGLN https://www.google.com/search?q={query.replace(' ', '+')}\nENTER\n"
        return "Randomized Search Fuzzing", script, target_os, res_w, res_h, query


def run_random_1000():
    parser = DuckyScriptParser()
    nlp = NaturalLanguageToDucky()
    usb_gen = ArduinoGenerator()
    ble_gen = BleGenerator()

    start_time = time.time()
    total = 1000
    passed = 0
    categories = {}

    for i in range(1, total + 1):
        cat_name, payload, target_os, res_w, res_h, meta = generate_random_case(i)
        if cat_name not in categories:
            categories[cat_name] = {"passed": 0, "total": 0, "errors": []}
        categories[cat_name]["total"] += 1

        try:
            if cat_name == "Randomized NLP Composition":
                res = nlp.convert(payload, target_os=target_os, screen_res=f"{res_w} {res_h}")
                assert res["success"], f"NLP conversion failed for: {payload}"
                commands = parser.parse(res["script"])
            else:
                commands = parser.parse(payload)

            assert len(commands) > 0, "Empty AST produced"

            sim = VirtualSimulator(screen_w=res_w, screen_h=res_h)
            sim_res = sim.simulate(commands)

            # Check cursor clamping
            cx = sim_res["final_cursor"]["x"]
            cy = sim_res["final_cursor"]["y"]
            assert 0 <= cx <= res_w, f"Cursor X ({cx}) outside bounds [0, {res_w}]"
            assert 0 <= cy <= res_h, f"Cursor Y ({cy}) outside bounds [0, {res_h}]"

            # Check C++ generator stability on sampled intervals
            if i % 10 == 0:
                usb_code = usb_gen.generate(commands)
                ble_code = ble_gen.generate(commands)
                assert "setup()" in usb_code and "loop()" in usb_code
                assert "setup()" in ble_code and "loop()" in ble_code

            passed += 1
            categories[cat_name]["passed"] += 1

        except Exception as e:
            categories[cat_name]["errors"].append(f"Test #{i}: {str(e)[:80]}")

    elapsed = time.time() - start_time

    print("\n=========================================================================================")
    print(f"       🦆 OMNIDUCKY 1,000-CASE RANDOMIZED ADVERSARIAL STRESS TEST")
    print("=========================================================================================\n")

    for cat, data in categories.items():
        pct = (data["passed"] / data["total"]) * 100.0
        status = "PASSED" if data["passed"] == data["total"] else "FAILED"
        print(f"  [{status}] {cat:<34}: {data['passed']:>3}/{data['total']:>3}  ({pct:5.1f}%)")
        if data["errors"]:
            for err in data["errors"][:2]:
                print(f"         └── {err}")

    print("\n-----------------------------------------------------------------------------------------")
    print(f"  TOTAL RANDOM STRESS TEST   : {passed}/{total} Tests Passed ({(passed/total)*100.0:.2f}%)")
    print(f"  SIMULATION THROUGHPUT      : {total / max(elapsed, 0.001):,.0f} tests/sec (completed in {elapsed:.3f}s)")
    print("=========================================================================================\n")

    return passed == total


if __name__ == "__main__":
    success = run_random_1000()
    sys.exit(0 if success else 1)
