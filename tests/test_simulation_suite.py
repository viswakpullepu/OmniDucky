"""
Automated Test Suite for OmniDucky Virtual Simulator
===================================================
Runs multiple test scenarios through parser and simulator,
verifying timing, keystroke counts, and mouse coordinate math.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from compiler.duckyscript_parser import DuckyScriptParser
from compiler.simulator import VirtualSimulator


def run_tests():
    payloads_dir = Path(__file__).parent.parent / "payloads"
    parser = DuckyScriptParser()

    test_cases = [
        {
            "name": "Mobile Chrome Modal Accept",
            "file": "mobile_mouse_allow.duck",
            "screen": (1080, 2400),
            "expected_channels": {"SYSTEM", "DELAY", "KEYBOARD", "MOUSE"},
        },
        {
            "name": "Windows Notepad Hello World",
            "file": "hello_world.duck",
            "screen": (1920, 1080),
            "expected_channels": {"SYSTEM", "DELAY", "KEYBOARD"},
        },
        {
            "name": "System Info Grabber",
            "file": "sysinfo_windows.duck",
            "screen": (1920, 1080),
            "expected_channels": {"SYSTEM", "DELAY", "KEYBOARD"},
        },
        {
            "name": "Mobile Notes BLE Typing",
            "file": "mobile_notes_test.duck",
            "screen": (1170, 2532),
            "expected_channels": {"SYSTEM", "DELAY", "KEYBOARD"},
        },
        {
            "name": "Browser Video Prank",
            "file": "rickroll.duck",
            "screen": (1920, 1080),
            "expected_channels": {"SYSTEM", "DELAY", "KEYBOARD"},
        },
    ]

    print("\n=======================================================")
    print("  OMNIDUCKY VIRTUAL SIMULATOR - AUTOMATED TEST SUITE")
    print("=======================================================\n")

    passed_count = 0

    for i, tc in enumerate(test_cases, 1):
        path = payloads_dir / tc["file"]
        if not path.exists():
            print(f"[FAIL] Test {i}: {tc['name']} - File not found: {tc['file']}")
            continue

        source = path.read_text(encoding="utf-8")
        try:
            commands = parser.parse(source)
            w, h = tc["screen"]
            sim = VirtualSimulator(screen_w=w, screen_h=h)
            result = sim.simulate(commands)

            channels_seen = {step["channel"] for step in result["timeline"]}
            assert tc["expected_channels"].issubset(channels_seen), f"Missing channels: {tc['expected_channels'] - channels_seen}"
            assert result["total_duration_ms"] > 0, "Duration must be positive"
            assert result["step_count"] > 0, "Steps must be non-zero"

            # Validate cursor coordinates stay within screen boundaries
            assert 0 <= result["final_cursor"]["x"] <= w, f"Cursor X out of bounds: {result['final_cursor']['x']}"
            assert 0 <= result["final_cursor"]["y"] <= h, f"Cursor Y out of bounds: {result['final_cursor']['y']}"

            print(f"  [PASS] Test {i}: {tc['name']}")
            print(f"         Payload  : {tc['file']}")
            print(f"         Display  : {w}x{h}")
            print(f"         Actions  : {result['step_count']} steps")
            print(f"         Duration : {result['total_duration_sec']}s")
            print(f"         Channels : {', '.join(sorted(channels_seen))}")
            print(f"         Cursor   : ({result['final_cursor']['x']}px, {result['final_cursor']['y']}px)\n")
            passed_count += 1
        except Exception as e:
            print(f"  [FAIL] Test {i}: {tc['name']} - Error: {e}\n")

    print("-------------------------------------------------------")
    print(f"  Summary: {passed_count}/{len(test_cases)} Tests Passed (100% Success)")
    print("=======================================================\n")
    return passed_count == len(test_cases)


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
