"""
DuckyScript Parser
Tokenizes and parses DuckyScript payload files into an intermediate representation (IR).

Supported DuckyScript Commands:
  REM         - Comment (ignored)
  DELAY       - Pause in milliseconds
  STRING      - Type a string of characters
  STRINGLN    - Type a string followed by ENTER
  ENTER/RETURN, ESC, TAB, etc. - Press a single special key
  GUI r       - Modifier + key combo
  CTRL ALT DELETE - Multi-modifier combos
  REPEAT      - Repeat the previous command N times
  DEFAULT_DELAY / DEFAULTDELAY - Set delay between every command
"""

from dataclasses import dataclass, field
from typing import List, Optional
from compiler.keycodes import MODIFIERS, SPECIAL_KEYS, ALL_KEYS


@dataclass
class Command:
    """Represents a single parsed DuckyScript command."""
    line_num: int
    cmd_type: str          # "delay", "string", "stringln", "keypress", "combo", "repeat", "default_delay", "mouse_move", "mouse_click", "mouse_scroll"
    value: Optional[str] = None
    keys: List[str] = field(default_factory=list)
    modifiers: List[str] = field(default_factory=list)
    delay_ms: int = 0
    repeat_count: int = 0
    mouse_x: int = 0
    mouse_y: int = 0
    mouse_wheel: int = 0
    mouse_button: str = "LEFT"


class DuckyScriptParser:
    """Parse DuckyScript source into a list of Command objects."""

    def __init__(self):
        self.commands: List[Command] = []
        self.default_delay: int = 0
        self.errors: List[str] = []

    def parse(self, source: str) -> List[Command]:
        """Parse DuckyScript source text and return command list."""
        self.commands = []
        self.errors = []
        self.default_delay = 0

        lines = source.strip().split("\n")

        for line_num, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("REM ") or line == "REM":
                continue

            try:
                cmd = self._parse_line(line_num, line)
                if cmd:
                    self.commands.append(cmd)
            except ValueError as e:
                self.errors.append(f"Line {line_num}: {e}")

        if self.errors:
            raise SyntaxError(
                "DuckyScript parse errors:\n" + "\n".join(self.errors)
            )

        return self.commands

    def _parse_line(self, line_num: int, line: str) -> Optional[Command]:
        """Parse a single DuckyScript line into a Command."""
        parts = line.split(" ", 1)
        keyword = parts[0].upper()
        argument = parts[1] if len(parts) > 1 else ""

        # DELAY <ms>
        if keyword == "DELAY":
            ms = int(argument.strip())
            return Command(line_num=line_num, cmd_type="delay", delay_ms=ms)

        # DEFAULT_DELAY / DEFAULTDELAY <ms>
        if keyword in ("DEFAULT_DELAY", "DEFAULTDELAY"):
            self.default_delay = int(argument.strip())
            return Command(
                line_num=line_num,
                cmd_type="default_delay",
                delay_ms=self.default_delay,
            )

        # STRING <text>
        if keyword == "STRING":
            return Command(line_num=line_num, cmd_type="string", value=argument)

        # STRINGLN <text>
        if keyword == "STRINGLN":
            return Command(line_num=line_num, cmd_type="stringln", value=argument)

        # REPEAT <count>
        if keyword == "REPEAT":
            count = int(argument.strip())
            return Command(
                line_num=line_num, cmd_type="repeat", repeat_count=count
            )

        # MOUSE COMMANDS
        # MOUSE_MOVE <x> <y>  or  MOUSE MOVE <x> <y>
        if keyword in ("MOUSE_MOVE", "MOUSEMOVE") or (keyword == "MOUSE" and argument.upper().startswith("MOVE")):
            raw_args = argument if keyword in ("MOUSE_MOVE", "MOUSEMOVE") else argument[4:].strip()
            pts = raw_args.split()
            mx = int(pts[0]) if len(pts) > 0 else 0
            my = int(pts[1]) if len(pts) > 1 else 0
            return Command(line_num=line_num, cmd_type="mouse_move", mouse_x=mx, mouse_y=my)

        # MOUSE_CLICK [LEFT|RIGHT|MIDDLE]  or  MOUSE CLICK [button]
        if keyword in ("MOUSE_CLICK", "MOUSECLICK") or (keyword == "MOUSE" and argument.upper().startswith("CLICK")):
            raw_btn = (argument if keyword in ("MOUSE_CLICK", "MOUSECLICK") else argument[5:].strip()).upper()
            btn = "LEFT" if not raw_btn or "LEFT" in raw_btn else ("RIGHT" if "RIGHT" in raw_btn else "MIDDLE")
            return Command(line_num=line_num, cmd_type="mouse_click", mouse_button=btn)

        # MOUSE_SCROLL <amount>
        if keyword in ("MOUSE_SCROLL", "MOUSESCROLL") or (keyword == "MOUSE" and argument.upper().startswith("SCROLL")):
            raw_val = argument if keyword in ("MOUSE_SCROLL", "MOUSESCROLL") else argument[6:].strip()
            val = int(raw_val) if raw_val else 1
            return Command(line_num=line_num, cmd_type="mouse_scroll", mouse_wheel=val)

        # SCREEN_SIZE <width> <height>
        if keyword in ("SCREEN_SIZE", "SCREENSIZE", "RESOLUTION"):
            pts = argument.strip().split()
            w = int(pts[0]) if len(pts) > 0 else 1080
            h = int(pts[1]) if len(pts) > 1 else 2400
            return Command(line_num=line_num, cmd_type="screen_size", mouse_x=w, mouse_y=h)

        # MOUSE_POS_PCT <x_pct> <y_pct> (Percentage of screen e.g. 50 60)
        if keyword in ("MOUSE_POS_PCT", "MOUSE_PERCENT", "MOUSE_PCT"):
            pts = argument.strip().split()
            px = float(pts[0]) if len(pts) > 0 else 50.0
            py = float(pts[1]) if len(pts) > 1 else 50.0
            return Command(line_num=line_num, cmd_type="mouse_pos_pct", value=f"{px},{py}")

        # Key combinations or single key presses
        # e.g., "GUI r", "CTRL ALT DELETE", "ENTER", "F5"
        tokens = line.upper().split()
        modifiers = []
        keys = []

        for token in tokens:
            if token in MODIFIERS:
                modifiers.append(token)
            elif token in SPECIAL_KEYS:
                keys.append(token)
            elif len(token) == 1 and token.isalnum():
                keys.append(token.lower())
            else:
                raise ValueError(
                    f"Unknown key or command: '{token}' in line: '{line}'"
                )

        if modifiers and keys:
            return Command(
                line_num=line_num,
                cmd_type="combo",
                modifiers=modifiers,
                keys=keys,
            )
        elif keys and not modifiers:
            return Command(
                line_num=line_num, cmd_type="keypress", keys=keys
            )
        elif modifiers and not keys:
            # Just modifier pressed alone (rare but valid)
            return Command(
                line_num=line_num, cmd_type="keypress", keys=modifiers
            )

        raise ValueError(f"Could not parse line: '{line}'")
