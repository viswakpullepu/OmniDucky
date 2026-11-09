"""
Natural Language to DuckyScript Converter
=========================================
Converts human-language instructions (sentences, bullet points, or step-by-step commands)
into valid DuckyScript for PC, Android, and iOS targets.
"""

import re
from typing import List, Dict, Any, Tuple


class NaturalLanguageToDucky:
    """Rules and heuristic parser for translating human prompts to DuckyScript."""

    def __init__(self):
        pass

    def convert(self, prompt: str, target_os: str = "windows") -> Dict[str, Any]:
        """
        Convert a natural language prompt to DuckyScript.
        Returns a dict with generated script, detected steps, and status.
        """
        lines = [line.strip() for line in prompt.splitlines() if line.strip()]
        ducky_lines: List[str] = [
            f"REM Auto-generated from natural language prompt",
            f"REM Target OS: {target_os.capitalize()}",
            "DEFAULT_DELAY 100",
            "DELAY 1000",
            ""
        ]

        steps_translated = []

        # Split sentences if single line containing multiple actions (e.g., separated by "then", "and then", periods, semicolons)
        flattened_actions = []
        for raw_line in lines:
            # Strip numbering like "1. ", "Step 1: ", "- "
            clean_line = re.sub(r'^(step\s*\d+[:.]?|\d+[\.\)]|\*|-)\s*', '', raw_line, flags=re.IGNORECASE).strip()
            if not clean_line:
                continue

            # Split compound instructions like "Open notepad and then type hello", but do not split on dots in URLs or numbers
            # Split on 'and then', 'then', or dot followed by whitespace/end of line (not dot within url or decimal)
            parts = re.split(r'\b(?:and\s+then|then)\b|(?<!\w\.\w)(?<=\s)\.|\.(?=\s+[A-Z]|\s*$)', clean_line, flags=re.IGNORECASE)
            for part in parts:
                if part:
                    p = part.strip()
                    if p:
                        flattened_actions.append(p)

        for action in flattened_actions:
            translated, desc = self._translate_action(action, target_os.lower())
            if translated:
                ducky_lines.append(f"REM {desc}")
                ducky_lines.extend(translated)
                ducky_lines.append("")
                steps_translated.append(desc)

        script_text = "\n".join(ducky_lines).strip() + "\n"
        return {
            "success": True,
            "script": script_text,
            "steps": steps_translated,
            "count": len(steps_translated)
        }

    def _translate_action(self, text: str, target_os: str) -> Tuple[List[str], str]:
        t = text.strip()

        # 1. Delays / Wait
        wait_match = re.search(r'(?:wait|delay|sleep|pause)\s*(?:for)?\s*(\d+(?:\.\d+)?)\s*(seconds?|secs?|s|milliseconds?|ms)?', t, re.IGNORECASE)
        if wait_match:
            val = float(wait_match.group(1))
            unit = (wait_match.group(2) or 'seconds').lower()
            ms = int(val * 1000) if 's' in unit and 'm' not in unit else int(val)
            return [f"DELAY {ms}"], f"Wait {ms}ms"

        # 2. Open / Visit URL
        url_match = re.search(r'(?:open|go\s*to|browse\s*to|visit)\s*(?:url|website|site)?\s*(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9-]+\.[a-z]{2,}(?:/[^\s]*)?)', t, re.IGNORECASE)
        if url_match:
            url = url_match.group(1)
            if not url.startswith('http://') and not url.startswith('https://'):
                url = 'https://' + url
            if target_os in ("android", "ios"):
                return [
                    "GUI SPACE",
                    "DELAY 800",
                    f"STRING {url}",
                    "ENTER"
                ], f"Open URL: {url} via Search"
            else:
                return [
                    "GUI r",
                    "DELAY 500",
                    f"STRING {url}",
                    "ENTER"
                ], f"Open URL in default browser: {url}"

        # 3. Open Terminal / PowerShell / CMD / Command Prompt
        if re.search(r'\b(?:open|launch|start)\s*(?:powershell|terminal|cmd|command\s*prompt)\b', t, re.IGNORECASE):
            cmd_type = "powershell" if "powershell" in t.lower() else ("cmd" if "cmd" in t.lower() or "command prompt" in t.lower() else "terminal")
            if target_os == "mac":
                return [
                    "GUI SPACE",
                    "DELAY 500",
                    "STRING Terminal",
                    "ENTER",
                    "DELAY 1000"
                ], "Launch Terminal via Spotlight"
            else:
                return [
                    "GUI r",
                    "DELAY 500",
                    f"STRING {cmd_type}",
                    "ENTER",
                    "DELAY 1000"
                ], f"Launch {cmd_type.upper()}"

        # 4. Run terminal command
        run_match = re.search(r'(?:run|execute|type\s*in\s*terminal)\s*(?:command)?:?\s*["\']?([^"\']+)["\']?$', t, re.IGNORECASE)
        if run_match and any(kw in t.lower() for kw in ("run", "execute", "command")):
            cmd = run_match.group(1).strip()
            return [
                f"STRINGLN {cmd}"
            ], f"Run command: {cmd}"

        # 5. Open specific App (e.g. notepad, chrome, calculator, notes, settings)
        open_app_match = re.search(r'\b(?:open|launch|start)\s+([a-zA-Z0-9\s_-]+)$', t, re.IGNORECASE)
        if open_app_match and not any(kw in t.lower() for kw in ("url", "website", "link")):
            app_name = open_app_match.group(1).strip()
            if target_os in ("android", "ios"):
                return [
                    "GUI SPACE",
                    "DELAY 700",
                    f"STRING {app_name}",
                    "DELAY 400",
                    "ENTER"
                ], f"Search & open {app_name} on mobile"
            elif target_os == "mac":
                return [
                    "GUI SPACE",
                    "DELAY 600",
                    f"STRING {app_name}",
                    "ENTER",
                    "DELAY 800"
                ], f"Open {app_name} via Spotlight"
            else:
                return [
                    "GUI r",
                    "DELAY 500",
                    f"STRING {app_name}",
                    "ENTER",
                    "DELAY 800"
                ], f"Open application: {app_name}"

        # 6. Type / Write Text
        type_match = re.search(r'\b(?:type|write|input|enter\s*text)\s*(?:the\s*text)?\s*[:\'"]?\s*(.+?)[\'"]?$', t, re.IGNORECASE)
        if type_match:
            text_to_type = type_match.group(1).strip().strip('"\'')
            # Check if mentions press enter at end
            if "and press enter" in t.lower() or "with enter" in t.lower():
                text_to_type = re.sub(r'\s+and\s+press\s+enter.*$', '', text_to_type, flags=re.IGNORECASE).strip()
                return [f"STRINGLN {text_to_type}"], f"Type text with Enter: '{text_to_type}'"
            return [f"STRING {text_to_type}"], f"Type text: '{text_to_type}'"

        # 7. Mouse Actions & Permissions
        # Click Allow / Accept / Permission prompt
        if re.search(r'\b(?:click\s*allow|allow\s*permission|grant\s*permission|click\s*ok|accept\s*permission)\b', t, re.IGNORECASE):
            if target_os in ("android", "ios"):
                # Adaptive resolution scaling: Tab focus + Calibrated Screen % positioning
                return [
                    "REM Dual strategy: Keyboard focus + Calibrated screen tap",
                    "TAB",
                    "DELAY 200",
                    "TAB",
                    "DELAY 200",
                    "ENTER",
                    "REM Adaptive mouse tap at 50% X, 62% Y (standard mobile modal button)",
                    "MOUSE_POS_PCT 50 62",
                    "DELAY 150",
                    "MOUSE_CLICK LEFT"
                ], "Adaptive Click Allow / Grant permission (Tab focus + Screen % tap)"
            else:
                return ["ENTER"], "Press Enter on dialog button"

        # Click at screen percentage (e.g. "click center", "click at 50% 60%")
        pct_click_m = re.search(r'\b(?:click|tap)\s*(?:at)?\s*(\d+(?:\.\d+)?)\s*%\s*(?:and|,)?\s*(\d+(?:\.\d+)?)\s*%', t, re.IGNORECASE)
        if pct_click_m:
            px = float(pct_click_m.group(1))
            py = float(pct_click_m.group(2))
            return [
                f"MOUSE_POS_PCT {px} {py}",
                "DELAY 100",
                "MOUSE_CLICK LEFT"
            ], f"Adaptive click at {px}% X, {py}% Y"

        if re.search(r'\b(?:click|tap)\s*(?:the\s*)?center\b', t, re.IGNORECASE):
            return [
                "MOUSE_POS_PCT 50 50",
                "DELAY 100",
                "MOUSE_CLICK LEFT"
            ], "Adaptive click at screen center (50%, 50%)"

        # Mouse Click
        if re.search(r'\b(?:left\s*click|click\s*left|single\s*click|click\s*mouse|click\s*here|mouse\s*click)\b', t, re.IGNORECASE) or t.lower() in ("click", "tap"):
            return ["MOUSE_CLICK LEFT"], "Mouse Left Click"
        if re.search(r'\b(?:right\s*click|click\s*right)\b', t, re.IGNORECASE):
            return ["MOUSE_CLICK RIGHT"], "Mouse Right Click"
        if re.search(r'\b(?:middle\s*click)\b', t, re.IGNORECASE):
            return ["MOUSE_CLICK MIDDLE"], "Mouse Middle Click"
        if re.search(r'\b(?:double\s*click)\b', t, re.IGNORECASE):
            return [
                "MOUSE_CLICK LEFT",
                "DELAY 100",
                "MOUSE_CLICK LEFT"
            ], "Mouse Double Click"

        # Mouse Move
        # "move mouse [x] [y]"
        mm_xy = re.search(r'\b(?:move\s*(?:mouse|cursor)|cursor|mouse)\s*(?:by|to)?\s*(-?\d+)\s*[, ]\s*(-?\d+)', t, re.IGNORECASE)
        if mm_xy:
            mx = int(mm_xy.group(1))
            my = int(mm_xy.group(2))
            return [f"MOUSE_MOVE {mx} {my}"], f"Move mouse cursor ({mx}, {my})"

        # "move mouse down 100", "move mouse right 50", etc.
        mm_dir = re.search(r'\b(?:move\s*(?:mouse|cursor)|scroll)\s*(?:to\s*the)?\s*(down|up|left|right)\s*(?:by)?\s*(\d+)?', t, re.IGNORECASE)
        if mm_dir:
            direction = mm_dir.group(1).lower()
            amt = int(mm_dir.group(2)) if mm_dir.group(2) else 100
            dx, dy = 0, 0
            if direction == "down": dy = amt
            elif direction == "up": dy = -amt
            elif direction == "right": dx = amt
            elif direction == "left": dx = -amt
            return [f"MOUSE_MOVE {dx} {dy}"], f"Move mouse {direction} by {amt}px"

        # Mouse Scroll
        scroll_m = re.search(r'\b(?:mouse\s*scroll|scroll\s*wheel)\s*(-?\d+)', t, re.IGNORECASE)
        if scroll_m:
            s_val = int(scroll_m.group(1))
            return [f"MOUSE_SCROLL {s_val}"], f"Scroll mouse wheel: {s_val}"

        # 8. Press Keys & Key Combos
        if re.search(r'\b(?:press|hit)\s+(?:enter|return)\b', t, re.IGNORECASE):
            return ["ENTER"], "Press Enter"
        if re.search(r'\b(?:press|hit)\s+(?:tab)\b', t, re.IGNORECASE):
            return ["TAB"], "Press Tab"
        if re.search(r'\b(?:press|hit)\s+(?:esc|escape)\b', t, re.IGNORECASE):
            return ["ESCAPE"], "Press Escape"
        if re.search(r'\b(?:press|hit)\s+(?:space|spacebar)\b', t, re.IGNORECASE):
            return ["SPACE"], "Press Space"
        if re.search(r'\b(?:lock\s*(?:the)?\s*(?:pc|screen|computer)|lock\s*screen)\b', t, re.IGNORECASE):
            return ["GUI l"], "Lock Screen"
        if re.search(r'\b(?:show\s*desktop|minimize\s*all)\b', t, re.IGNORECASE):
            return ["GUI d"], "Minimize All / Show Desktop"
        if re.search(r'\b(?:take\s*(?:a)?\s*screenshot|screenshot)\b', t, re.IGNORECASE):
            return ["PRINTSCREEN"], "Take Screenshot"

        # Arbitrary hotkey like "press ctrl+c", "press win+r", "press alt+f4"
        combo_match = re.search(r'\b(?:press|hotkey|keys?)\s+([a-zA-Z0-9\+\s]+)', t, re.IGNORECASE)
        if combo_match:
            raw_combo = combo_match.group(1).replace("+", " ").strip().upper()
            return [raw_combo], f"Press combo: {raw_combo}"

        # 8. Fallback: treat as typing string
        return [f"STRING {t}"], f"Type: {t}"
