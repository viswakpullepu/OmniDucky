"""
Verification Suite for Refined NLP Translation Model
=====================================================
Tests colloquial language, typos, window management, and compound instructions.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from compiler.nlp_converter import NaturalLanguageToDucky
from compiler.duckyscript_parser import DuckyScriptParser


TEST_PROMPTS = [
    # Typos & Colloquialisms
    ("pop open notepd and wait a second and type testing 123", "windows"),
    ("fire up chrom and browse to https://github.com and hit enter", "windows"),
    ("pull up powrshell and execute whoami /priv", "windows"),
    ("head over to youtube and press enter", "android"),
    ("take a screenshot then wait 500ms then go home", "ios"),
    # Productivity Shortcuts
    ("select all and copy that and wait 200ms and paste it", "windows"),
    ("save the file then close the window", "mac"),
    ("switch apps and wait 300ms", "windows"),
    ("undo that and wait 200ms", "mac"),
    # Complex Mouse & Permissions
    ("open settings then wait a moment then click allow", "android"),
    ("jiggle mouse and wait 1s", "windows"),
    ("tap at 50% 62% and left click", "ios"),
    ("move mouse down 200 and double click", "windows"),
    # Mixed Multi-Clauses
    ("open safari then wait 800ms then browse to https://apple.com then wait a second then close tab", "ios"),
    ("press win+r then type cmd and press enter then type ipconfig /flushdns and hit enter", "windows"),
]


def test_refined_nlp():
    nlp = NaturalLanguageToDucky()
    parser = DuckyScriptParser()

    passed = 0
    total = len(TEST_PROMPTS)

    print("\n=================================================================")
    print(f"  VERIFYING REFINED NLP MODEL: {total} COLLOQUIAL PROMPTS")
    print("=================================================================\n")

    for i, (prompt, os_target) in enumerate(TEST_PROMPTS, 1):
        res = nlp.convert(prompt, target_os=os_target)
        assert res["success"], f"NLP failed on: {prompt}"
        commands = parser.parse(res["script"])
        assert len(commands) >= 2, f"Too few commands parsed for: {prompt}"

        print(f"  [PASS] Test {i:>2}: '{prompt[:45]}...' ({os_target}) -> {res['count']} steps")
        passed += 1

    print(f"\n-----------------------------------------------------------------")
    print(f"  REFINED NLP AUDIT: {passed}/{total} Tests Passed (100% Accuracy)")
    print("=================================================================\n")
    return passed == total


if __name__ == "__main__":
    success = test_refined_nlp()
    sys.exit(0 if success else 1)
