"""
DuckLM — Synthetic Training Data Generator
Generates NL → {DuckyScript JSON + mouse coords} pairs for SFT.
Run with: python generate_data.py --n 50000 --out ./data/sft_pairs.jsonl

Uses rule-based templates (no copyright entanglement, fully proprietary corpus).
"""

import json
import random
import argparse
from pathlib import Path
from itertools import product


# ═══════════════════════════════════════════════════════════════
#  TEMPLATE LIBRARY
# ═══════════════════════════════════════════════════════════════

# (instruction_template, ducky_script, mouse_x%, mouse_y%)
# mouse coords are None when no click needed

TEMPLATES = {

    "open_app": {
        "instructions": [
            "open {app}",
            "launch {app}",
            "start {app}",
            "run {app}",
            "open up {app}",
        ],
        "apps": {
            "notepad":       ("GUI r\nDELAY 600\nSTRINGLN notepad\nDELAY 1500", None, None),
            "calculator":    ("GUI r\nDELAY 600\nSTRINGLN calc\nDELAY 1000", None, None),
            "file explorer": ("GUI e\nDELAY 1500", None, None),
            "task manager":  ("CTRL-ALT ESCAPE\nDELAY 1000", None, None),
            "powershell":    ("GUI r\nDELAY 600\nSTRINGLN powershell\nDELAY 2000", None, None),
            "command prompt":("GUI r\nDELAY 600\nSTRINGLN cmd\nDELAY 1000", None, None),
            "chrome":        ("GUI r\nDELAY 600\nSTRINGLN chrome\nDELAY 2500", None, None),
            "edge":          ("GUI r\nDELAY 600\nSTRINGLN msedge\nDELAY 2000", None, None),
            "paint":         ("GUI r\nDELAY 600\nSTRINGLN mspaint\nDELAY 1500", None, None),
            "control panel": ("GUI r\nDELAY 600\nSTRINGLN control\nDELAY 1500", None, None),
        }
    },

    "search_web": {
        "instructions": [
            "search for {query} on google",
            "google {query}",
            "open chrome and search {query}",
            "search {query} in browser",
            "look up {query}",
        ],
        "queries": [
            "weather today", "how to reset windows", "file transfer over bluetooth",
            "powershell list running processes", "how to send files via email",
            "windows shortcut keys", "how to screenshot on windows",
        ],
        "script_template": (
            "GUI r\nDELAY 600\nSTRINGLN chrome\nDELAY 2500\n"
            "CTRL l\nDELAY 400\nSTRINGLN https://www.google.com/search?q={encoded_query}\nDELAY 1500"
        ),
    },

    "file_ops": {
        "instructions": [
            "copy all {ext} files from {src} to {dst}",
            "move {ext} files in {src} to {dst}",
            "open powershell and copy {ext} files from {src} to {dst}",
            "transfer all {ext} from {src} folder to {dst}",
        ],
        "exts": ["jpg", "jpeg", "png", "pdf", "docx", "txt", "mp4", "mp3"],
        "srcs": [
            "%USERPROFILE%\\Pictures",
            "%USERPROFILE%\\Downloads",
            "%USERPROFILE%\\Documents",
            "%USERPROFILE%\\Desktop",
            "C:\\Users\\Public",
        ],
        "dsts": [
            "D:\\Backup",
            "E:\\Transfer",
            "%USERPROFILE%\\Desktop\\Backup",
            "C:\\Temp\\Export",
        ],
        "script_template": (
            "GUI r\nDELAY 600\nSTRINGLN powershell\nDELAY 2000\n"
            "STRINGLN Copy-Item -Path \"{src}\\*.{ext}\" -Destination \"{dst}\" -Force\nDELAY 1000"
        ),
    },

    "wifi_creds": {
        "instructions": [
            "show saved wifi passwords",
            "export wifi credentials",
            "get all wifi passwords",
            "dump wifi profiles",
            "list saved networks and passwords",
        ],
        "script": (
            "GUI r\nDELAY 600\nSTRINGLN powershell\nDELAY 2000\n"
            "STRINGLN (netsh wlan show profiles) | "
            "Select-String \":(.+)$\" | %{{$name=$_.Matches.Groups[1].Value.Trim();"
            "netsh wlan show profile name=$name key=clear}} | "
            "Select-String \"Key Content\" | %{{$_.Line}} | "
            "Out-File $env:TEMP\\wifi.txt\nDELAY 1000\n"
            "STRINGLN Start-Process notepad $env:TEMP\\wifi.txt\nDELAY 500"
        ),
        "mouse_x": None, "mouse_y": None,
    },

    "lock_screen": {
        "instructions": [
            "lock the screen", "lock the computer", "lock this pc",
            "lock screen", "press win l", "lock workstation",
        ],
        "script": "DELAY 300\nGUI l",
        "mouse_x": None, "mouse_y": None,
    },

    "screenshot": {
        "instructions": [
            "take a screenshot", "capture the screen", "screenshot",
            "grab a screenshot", "print screen", "capture display",
        ],
        "script": "GUI PRINTSCREEN\nDELAY 500",
        "mouse_x": None, "mouse_y": None,
    },

    "type_text": {
        "instructions": [
            "open notepad and type {text}",
            "type {text} in notepad",
            "write {text} in a text file",
            "open notepad and write {text} then save it",
        ],
        "texts": [
            "Hello World", "Testing 123", "This is a test",
            "OmniDucky payload executed", "Authorized security test",
        ],
        "script_template": (
            "GUI r\nDELAY 600\nSTRINGLN notepad\nDELAY 1500\n"
            "STRING {text}\nDELAY 300\nCTRL s\nDELAY 500"
        ),
    },

    "mouse_click": {
        "instructions": [
            "click on the {position} of the screen",
            "move mouse to {position} and click",
            "click {position}",
            "tap {position}",
        ],
        "positions": {
            "center":        (50, 50),
            "top left":      (10, 10),
            "top right":     (90, 10),
            "bottom left":   (10, 90),
            "bottom right":  (90, 90),
            "top center":    (50, 10),
            "bottom center": (50, 90),
            "middle left":   (10, 50),
            "middle right":  (90, 50),
        },
        "script_template": (
            "SCREEN_SIZE 1920 1080\n"
            "MOUSE_POS_PCT {x} {y}\nDELAY 100\nMOUSE_CLICK LEFT"
        ),
    },

    "run_command": {
        "instructions": [
            "open powershell and run {cmd}",
            "run {cmd} in powershell",
            "execute {cmd} in terminal",
            "open cmd and run {cmd}",
        ],
        "cmds": [
            "ipconfig", "ipconfig /all", "whoami", "systeminfo",
            "netstat -an", "tasklist", "dir %USERPROFILE%",
            "Get-Process", "Get-NetIPAddress",
            "Get-WifiProfile", "net user",
        ],
        "script_template": (
            "GUI r\nDELAY 600\nSTRINGLN powershell\nDELAY 2000\n"
            "STRINGLN {cmd}\nDELAY 1500"
        ),
    },

}


# ═══════════════════════════════════════════════════════════════
#  GENERATOR
# ═══════════════════════════════════════════════════════════════

def encode_query(q: str) -> str:
    return q.replace(' ', '+').replace('&', '%26')


def generate_pair() -> dict:
    """Generate one (instruction, output_json) training pair."""
    category = random.choice(list(TEMPLATES.keys()))
    t = TEMPLATES[category]

    mouse_x, mouse_y = None, None

    if category == "open_app":
        app_name = random.choice(list(t["apps"].keys()))
        instruction_tmpl = random.choice(t["instructions"])
        instruction = instruction_tmpl.format(app=app_name)
        script, mouse_x, mouse_y = t["apps"][app_name]

    elif category == "search_web":
        query = random.choice(t["queries"])
        instruction_tmpl = random.choice(t["instructions"])
        instruction = instruction_tmpl.format(query=query)
        script = t["script_template"].format(encoded_query=encode_query(query))

    elif category == "file_ops":
        ext = random.choice(t["exts"])
        src = random.choice(t["srcs"])
        dst = random.choice(t["dsts"])
        instruction_tmpl = random.choice(t["instructions"])
        instruction = instruction_tmpl.format(ext=ext, src=src.split("\\")[-1], dst=dst.split("\\")[-1])
        script = t["script_template"].format(ext=ext, src=src, dst=dst)

    elif category == "wifi_creds":
        instruction = random.choice(t["instructions"])
        script = t["script"]
        mouse_x, mouse_y = t["mouse_x"], t["mouse_y"]

    elif category == "lock_screen":
        instruction = random.choice(t["instructions"])
        script = t["script"]
        mouse_x, mouse_y = t["mouse_x"], t["mouse_y"]

    elif category == "screenshot":
        instruction = random.choice(t["instructions"])
        script = t["script"]
        mouse_x, mouse_y = t["mouse_x"], t["mouse_y"]

    elif category == "type_text":
        text = random.choice(t["texts"])
        instruction_tmpl = random.choice(t["instructions"])
        instruction = instruction_tmpl.format(text=text)
        script = t["script_template"].format(text=text)

    elif category == "mouse_click":
        pos_name = random.choice(list(t["positions"].keys()))
        x, y = t["positions"][pos_name]
        instruction_tmpl = random.choice(t["instructions"])
        instruction = instruction_tmpl.format(position=pos_name)
        script = t["script_template"].format(x=x, y=y)
        mouse_x, mouse_y = x, y

    elif category == "run_command":
        cmd = random.choice(t["cmds"])
        instruction_tmpl = random.choice(t["instructions"])
        instruction = instruction_tmpl.format(cmd=cmd)
        script = t["script_template"].format(cmd=cmd)

    else:
        return generate_pair()  # retry

    output = {
        "tool": "ducky_exec",
        "script": script,
        "mouse_x_pct": mouse_x,
        "mouse_y_pct": mouse_y,
        "confidence": round(random.uniform(0.88, 0.99), 2),
    }

    return {
        "instruction": instruction,
        "output": json.dumps(output),
        "category": category,
    }


def add_biomorph_variations(pair: dict) -> dict:
    """Randomly add BIOMORPH prefix to some payloads to teach that feature."""
    profiles = ["GHOST", "CASUAL_USER", "FAST_TYPIST", "SLOW_HUNT_PECK", "EXAM_STUDENT"]
    if random.random() < 0.3:  # 30% of pairs get biomorph prefix
        output = json.loads(pair["output"])
        profile = random.choice(profiles)
        output["script"] = f"BIOMORPH {profile}\n" + output["script"]
        pair["output"] = json.dumps(output)
        pair["instruction"] += f" (type like a {profile.lower().replace('_', ' ')})"
    return pair


# ═══════════════════════════════════════════════════════════════
#  TOKENIZER TRAINING DATA (domain BPE corpus)
# ═══════════════════════════════════════════════════════════════

def generate_tokenizer_corpus(n_pairs: int, out_path: Path):
    """Write raw text corpus for BPE tokenizer training."""
    lines = []
    for _ in range(n_pairs):
        pair = generate_pair()
        output = json.loads(pair["output"])
        lines.append(pair["instruction"])
        lines.append(output["script"])
        lines.append(pair["output"])

    # Add DuckyScript command vocabulary as seed
    ducky_cmds = [
        "DELAY DEFAULT_DELAY STRING STRINGLN ENTER GUI CTRL ALT SHIFT",
        "MOUSE_MOVE MOUSE_CLICK MOUSE_SCROLL MOUSE_POS_PCT SCREEN_SIZE",
        "REPEAT BIOMORPH GHOST CASUAL_USER FAST_TYPIST SLOW_HUNT_PECK EXAM_STUDENT",
        "LEFT RIGHT MIDDLE BACKSPACE TAB ESCAPE DELETE PRINTSCREEN",
        "KEY_RETURN KEY_ESC KEY_LEFT_GUI KEY_LEFT_CTRL KEY_LEFT_ALT KEY_LEFT_SHIFT",
        "powershell cmd notepad chrome msedge calc mspaint control",
        "Copy-Item Move-Item Get-Process Get-NetIPAddress netsh wlan ipconfig whoami",
        '{"tool":"ducky_exec","script":"...","mouse_x_pct":50,"mouse_y_pct":50}',
    ]
    lines.extend(ducky_cmds * 50)

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[tokenizer corpus] {len(lines)} lines → {out_path}")


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="DuckLM training data generator")
    parser.add_argument("--n", type=int, default=50000, help="Number of SFT pairs")
    parser.add_argument("--out", type=str, default="./data", help="Output directory")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"Generating {args.n} SFT pairs...")
    pairs = []
    for i in range(args.n):
        pair = generate_pair()
        pair = add_biomorph_variations(pair)
        pairs.append(pair)
        if (i + 1) % 5000 == 0:
            print(f"  {i+1}/{args.n} pairs generated")

    sft_path = out / "sft_pairs.jsonl"
    with open(sft_path, "w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p) + "\n")
    print(f"\n[SFT data] {len(pairs)} pairs → {sft_path}")

    # Category distribution
    from collections import Counter
    cats = Counter(p["category"] for p in pairs)
    print("\n[Category distribution]")
    for cat, count in sorted(cats.items()):
        print(f"  {cat:20s}: {count:6d} ({count/len(pairs)*100:.1f}%)")

    # Tokenizer corpus
    tok_path = out / "tokenizer_corpus.txt"
    generate_tokenizer_corpus(args.n // 5, tok_path)

    print(f"\n✅ Done. Files in {out}/")
    print(f"   Next: python train/tokenizer.py --corpus {tok_path}")
    print(f"   Then: python train/pretrain.py --data {sft_path}")


if __name__ == "__main__":
    main()
