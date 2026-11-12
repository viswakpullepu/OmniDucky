"""
OmniDucky Virtual Execution Simulator
=====================================
Simulates the execution of DuckyScript / ESP32-S3 payloads virtually.
Calculates exact timing, tracks simulated cursor coordinates on target resolutions,
and outputs step-by-step visual logs without needing physical hardware.
"""

import time
from typing import List, Dict, Any
from compiler.duckyscript_parser import Command, DuckyScriptParser


class VirtualSimulator:
    """Simulates payload execution on a virtual host (PC or Mobile)."""

    def __init__(self, screen_w: int = 1080, screen_h: int = 2400):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.cursor_x = 0
        self.cursor_y = 0
        self.timeline: List[Dict[str, Any]] = []
        self.elapsed_ms = 0

    def simulate(self, commands: List[Command], default_delay: int = 0) -> Dict[str, Any]:
        """Simulate a list of commands and generate a time-indexed execution trace."""
        self.timeline = []
        self.elapsed_ms = 0
        self.cursor_x = 0
        self.cursor_y = 0

        # Boot & enumeration delay
        self._record("SYSTEM", "USB/BLE Enumeration & Handshake", duration_ms=1500)

        prev_cmd = None
        for cmd in commands:
            if default_delay > 0 and prev_cmd is not None:
                self._record("DELAY", f"Default inter-command delay ({default_delay}ms)", duration_ms=default_delay)

            if cmd.cmd_type == "screen_size":
                self.screen_w = cmd.mouse_x
                self.screen_h = cmd.mouse_y
                self._record("CONFIG", f"Target screen resolution set to {self.screen_w}x{self.screen_h}")

            elif cmd.cmd_type == "delay":
                self._record("DELAY", f"Pause {cmd.delay_ms}ms", duration_ms=cmd.delay_ms)

            elif cmd.cmd_type == "default_delay":
                default_delay = cmd.delay_ms
                self._record("CONFIG", f"Default delay set to {default_delay}ms")

            elif cmd.cmd_type == "string":
                # Simulated typing speed: ~10ms per char
                type_duration = len(cmd.value) * 10
                self._record("KEYBOARD", f"Type string: '{cmd.value}'", duration_ms=type_duration, text=cmd.value)

            elif cmd.cmd_type == "stringln":
                type_duration = len(cmd.value) * 10 + 20
                self._record("KEYBOARD", f"Type string with Enter: '{cmd.value}'", duration_ms=type_duration, text=cmd.value + "\\n")

            elif cmd.cmd_type == "keypress":
                keys_str = " + ".join(cmd.keys)
                self._record("KEYBOARD", f"Press key: {keys_str}", duration_ms=40, keys=cmd.keys)

            elif cmd.cmd_type == "combo":
                combo_str = " + ".join(cmd.modifiers + cmd.keys)
                self._record("KEYBOARD", f"Press combo: {combo_str}", duration_ms=50, combo=combo_str)

            elif cmd.cmd_type == "mouse_pos_pct":
                parts = cmd.value.split(",")
                px = float(parts[0])
                py = float(parts[1])
                target_x = int((px / 100.0) * self.screen_w)
                target_y = int((py / 100.0) * self.screen_h)

                # Reset to 0,0 first (takes ~150ms)
                self._record("MOUSE", "Corner-Reset: Homing cursor to top-left (0, 0)", duration_ms=150, x=0, y=0)
                # Step to target
                travel_ms = max(50, int((abs(target_x) + abs(target_y)) * 0.1))
                self.cursor_x = target_x
                self.cursor_y = target_y
                self._record("MOUSE", f"Move cursor to {px}% X, {py}% Y -> ({target_x}px, {target_y}px)",
                             duration_ms=travel_ms, x=target_x, y=target_y, pct_x=px, pct_y=py)

            elif cmd.cmd_type == "mouse_move":
                self.cursor_x = max(0, min(self.cursor_x + cmd.mouse_x, self.screen_w))
                self.cursor_y = max(0, min(self.cursor_y + cmd.mouse_y, self.screen_h))
                self._record("MOUSE", f"Relative mouse move: dx={cmd.mouse_x}, dy={cmd.mouse_y} -> ({self.cursor_x}, {self.cursor_y})",
                             duration_ms=30, x=self.cursor_x, y=self.cursor_y)

            elif cmd.cmd_type == "mouse_click":
                self._record("MOUSE", f"Mouse click: {cmd.mouse_button} at ({self.cursor_x}, {self.cursor_y})",
                             duration_ms=60, button=cmd.mouse_button, x=self.cursor_x, y=self.cursor_y)

            elif cmd.cmd_type == "mouse_scroll":
                self._record("MOUSE", f"Mouse scroll: {cmd.mouse_wheel} ticks", duration_ms=40)

            prev_cmd = cmd

        return {
            "total_duration_ms": self.elapsed_ms,
            "total_duration_sec": round(self.elapsed_ms / 1000.0, 2),
            "step_count": len(self.timeline),
            "final_cursor": {"x": self.cursor_x, "y": self.cursor_y},
            "screen_size": {"width": self.screen_w, "height": self.screen_h},
            "timeline": self.timeline
        }

    def _record(self, channel: str, description: str, duration_ms: int = 0, **kwargs):
        event = {
            "timestamp_ms": self.elapsed_ms,
            "time_formatted": f"{self.elapsed_ms / 1000.0:.2f}s",
            "channel": channel,
            "description": description,
            "duration_ms": duration_ms
        }
        event.update(kwargs)
        self.timeline.append(event)
        self.elapsed_ms += duration_ms
