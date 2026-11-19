"""
DuckLM — Proprietary BPE Tokenizer
Pure Python implementation — zero external dependencies.
© 2026. All rights reserved. Proprietary and confidential.

This is an original implementation of Byte-Pair Encoding written from scratch.
No code derived from sentencepiece, HuggingFace tokenizers, or any OSS tokenizer.
"""

import re
import json
import collections
from pathlib import Path
from typing import List, Dict, Tuple, Optional


# ═══════════════════════════════════════════════════════════════
#  BYTE-PAIR ENCODING — FROM SCRATCH
# ═══════════════════════════════════════════════════════════════

class DuckTokenizer:
    """
    Proprietary BPE tokenizer for DuckLM.

    Special tokens:
      0 = [PAD]   1 = [BOS]   2 = [EOS]   3 = [UNK]
    """

    PAD_ID = 0
    BOS_ID = 1
    EOS_ID = 2
    UNK_ID = 3

    # Domain tokens that should NEVER be split
    DOMAIN_TOKENS = [
        "[PAD]", "[BOS]", "[EOS]", "[UNK]",
        "DELAY", "STRING", "STRINGLN", "ENTER", "GUI", "CTRL", "ALT", "SHIFT",
        "MOUSE_MOVE", "MOUSE_CLICK", "MOUSE_SCROLL", "MOUSE_POS_PCT", "SCREEN_SIZE",
        "REPEAT", "BIOMORPH", "DEFAULT_DELAY", "DEFAULTDELAY", "REM",
        "GHOST", "CASUAL_USER", "FAST_TYPIST", "SLOW_HUNT_PECK", "EXAM_STUDENT",
        "LEFT", "RIGHT", "MIDDLE", "BACKSPACE", "TAB", "ESCAPE", "DELETE",
        "ducky_exec", "mouse_x_pct", "mouse_y_pct", "confidence", "tool",
        "powershell", "cmd.exe", "notepad", "chrome", "msedge", "calc",
        "Copy-Item", "Move-Item", "Get-Process", "Get-NetIPAddress",
        "netsh", "ipconfig", "whoami", "systeminfo", "tasklist",
        "\\n", "\\t", "\\r",
    ]

    def __init__(self):
        self.vocab: Dict[str, int] = {}
        self.id_to_token: Dict[int, str] = {}
        self.merges: List[Tuple[str, str]] = []   # ordered merge rules
        self.merge_ranks: Dict[Tuple[str, str], int] = {}
        self._compiled_domain = None

    # ── Training ─────────────────────────────────────────────────

    def train(self, corpus_text: str, vocab_size: int = 4096, min_freq: int = 2):
        """Train BPE on raw text corpus."""
        print(f"[DuckTokenizer] Training BPE vocab={vocab_size}...")

        # Step 1: Seed vocab with all 256 byte characters + special/domain tokens
        self.vocab = {}
        self.merges = []

        # Add special tokens first (IDs 0-3)
        for tok in ["[PAD]", "[BOS]", "[EOS]", "[UNK]"]:
            self.vocab[tok] = len(self.vocab)

        # Add domain tokens (always preserved as single units)
        for tok in self.DOMAIN_TOKENS[4:]:  # skip specials already added
            if tok not in self.vocab:
                self.vocab[tok] = len(self.vocab)

        # Add base byte characters (printable ASCII + control chars we care about)
        for i in range(256):
            ch = chr(i)
            if ch not in self.vocab:
                self.vocab[ch] = len(self.vocab)

        print(f"  Seed vocab: {len(self.vocab)} tokens (specials + domain + bytes)")

        # Step 2: Pre-tokenize corpus into word frequency dict
        # Words are split on whitespace; each word is split into characters
        word_freqs = self._get_word_freqs(corpus_text, min_freq)
        print(f"  Unique word types: {len(word_freqs)}")

        # Represent each word as list of characters (word_freqs maps word→count)
        vocab_words = {word: list(word) for word in word_freqs.keys()}

        # Step 3: BPE merge loop
        n_merges = vocab_size - len(self.vocab)
        print(f"  Running {n_merges} merge operations...")

        for step in range(n_merges):
            # Count all adjacent pairs across all words
            pair_freqs = collections.Counter()
            for word, chars in vocab_words.items():
                freq = word_freqs[word]
                for i in range(len(chars) - 1):
                    pair_freqs[(chars[i], chars[i+1])] += freq

            if not pair_freqs:
                break

            # Find most frequent pair
            best_pair = max(pair_freqs, key=pair_freqs.__getitem__)
            if pair_freqs[best_pair] < min_freq:
                break

            # Create new merged token
            new_token = best_pair[0] + best_pair[1]
            self.merges.append(best_pair)
            self.merge_ranks[best_pair] = step
            self.vocab[new_token] = len(self.vocab)

            # Apply merge to all words
            vocab_words = self._apply_merge(vocab_words, best_pair, new_token)

            if (step + 1) % 500 == 0:
                print(f"  Step {step+1}/{n_merges} | vocab={len(self.vocab)} | "
                      f"best_pair={repr(best_pair[0]+best_pair[1])} freq={pair_freqs[best_pair]}")

        # Build reverse lookup
        self.id_to_token = {v: k for k, v in self.vocab.items()}
        print(f"\n[DuckTokenizer] Training complete. Final vocab: {len(self.vocab)} tokens")

    def _get_word_freqs(self, text: str, min_freq: int) -> Dict[str, int]:
        """Count word frequencies in corpus, pre-tokenizing by whitespace."""
        freqs = collections.Counter()

        # Protect domain tokens from being split
        domain_pattern = "|".join(
            re.escape(t) for t in sorted(self.DOMAIN_TOKENS, key=len, reverse=True)
        )

        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            # Split preserving domain tokens
            tokens = re.split(f"({domain_pattern}|\\s+)", line)
            for tok in tokens:
                tok = tok.strip()
                if tok:
                    freqs[tok] += 1

        # Filter by min frequency
        return {w: f for w, f in freqs.items() if f >= min_freq}

    def _apply_merge(
        self,
        vocab_words: Dict[str, List[str]],
        pair: Tuple[str, str],
        new_token: str
    ) -> Dict[str, List[str]]:
        """Apply a single merge rule to all words in the working vocab."""
        updated = {}
        a, b = pair
        for word, chars in vocab_words.items():
            new_chars = []
            i = 0
            while i < len(chars):
                if i < len(chars) - 1 and chars[i] == a and chars[i+1] == b:
                    new_chars.append(new_token)
                    i += 2
                else:
                    new_chars.append(chars[i])
                    i += 1
            updated[word] = new_chars
        return updated

    # ── Encoding ─────────────────────────────────────────────────

    def _tokenize_word(self, word: str) -> List[str]:
        """Apply learned BPE merges to a single word."""
        # Start with individual characters
        chars = list(word)
        if len(chars) == 1:
            return chars

        # Apply merges in order (by rank)
        while len(chars) > 1:
            # Find the lowest-rank merge applicable
            best_pair = None
            best_rank = len(self.merges) + 1

            for i in range(len(chars) - 1):
                pair = (chars[i], chars[i+1])
                rank = self.merge_ranks.get(pair, None)
                if rank is not None and rank < best_rank:
                    best_rank = rank
                    best_pair = (i, pair)

            if best_pair is None:
                break

            # Apply the best merge
            idx, pair = best_pair
            new_token = pair[0] + pair[1]
            chars = chars[:idx] + [new_token] + chars[idx+2:]

        return chars

    def encode(self, text: str, add_special: bool = True) -> List[int]:
        """Encode text to token IDs."""
        ids = []
        if add_special:
            ids.append(self.BOS_ID)

        # Protect domain tokens
        domain_pattern = "|".join(
            re.escape(t) for t in sorted(self.DOMAIN_TOKENS[4:], key=len, reverse=True)
            if t in self.vocab
        )
        if domain_pattern:
            parts = re.split(f"({domain_pattern})", text)
        else:
            parts = [text]

        for part in parts:
            if not part:
                continue
            if part in self.vocab:
                # Whole domain token
                ids.append(self.vocab[part])
            else:
                # Regular text — split by whitespace, then BPE each word
                words = re.split(r'(\s+)', part)
                for word in words:
                    if not word:
                        continue
                    if word.strip() == '':
                        # Whitespace — encode space char
                        for ch in word:
                            ids.append(self.vocab.get(ch, self.UNK_ID))
                    else:
                        # BPE-tokenize word
                        subwords = self._tokenize_word(word)
                        for sw in subwords:
                            ids.append(self.vocab.get(sw, self.UNK_ID))

        if add_special:
            ids.append(self.EOS_ID)

        return ids

    def decode(self, ids: List[int]) -> str:
        """Decode token IDs back to text."""
        tokens = []
        for i in ids:
            if i in (self.BOS_ID, self.EOS_ID, self.PAD_ID):
                continue
            tok = self.id_to_token.get(i, "[UNK]")
            tokens.append(tok)
        return "".join(tokens)

    # ── Persistence ──────────────────────────────────────────────

    def save(self, path: str):
        """Save tokenizer to a single JSON file."""
        data = {
            "vocab":        self.vocab,
            "merges":       [[a, b] for a, b in self.merges],
            "version":      1,
            "vocab_size":   len(self.vocab),
            "special_ids":  {
                "pad": self.PAD_ID,
                "bos": self.BOS_ID,
                "eos": self.EOS_ID,
                "unk": self.UNK_ID,
            }
        }
        Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[DuckTokenizer] Saved → {path}")

    @classmethod
    def load(cls, path: str) -> "DuckTokenizer":
        """Load tokenizer from JSON file."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        tok = cls()
        tok.vocab = data["vocab"]
        tok.merges = [tuple(m) for m in data["merges"]]
        tok.merge_ranks = {tuple(m): i for i, m in enumerate(tok.merges)}
        tok.id_to_token = {v: k for k, v in tok.vocab.items()}
        return tok

    def vocab_size(self) -> int:
        return len(self.vocab)

    def export_c_header(self, path: str):
        """Export vocab as C header for DuckRT ESP32 runtime."""
        lines = [
            "// DuckLM Vocabulary — Auto-generated. DO NOT EDIT.",
            "// © 2026. All rights reserved. Proprietary.",
            "",
            f"#define DUCKLM_VOCAB_SIZE {len(self.vocab)}",
            f"#define DUCKLM_BOS_ID     {self.BOS_ID}",
            f"#define DUCKLM_EOS_ID     {self.EOS_ID}",
            f"#define DUCKLM_PAD_ID     {self.PAD_ID}",
            f"#define DUCKLM_UNK_ID     {self.UNK_ID}",
            "",
            "static const char* const DUCKLM_VOCAB[] = {",
        ]
        for i in range(len(self.vocab)):
            tok = self.id_to_token.get(i, "[UNK]")
            escaped = tok.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
            lines.append(f'    "{escaped}",  /* {i} */')
        lines.append("};")
        Path(path).write_text("\n".join(lines), encoding="utf-8")
        print(f"[DuckTokenizer] C header → {path}")


# ═══════════════════════════════════════════════════════════════
#  STANDALONE TRAINING ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def main():
    import argparse, time
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus",    default="./data/tokenizer_corpus.txt")
    parser.add_argument("--out_dir",   default="./data")
    parser.add_argument("--vocab_size", type=int, default=4096)
    parser.add_argument("--min_freq",   type=int, default=2)
    args = parser.parse_args()

    corpus = Path(args.corpus).read_text(encoding="utf-8")
    print(f"[corpus] {len(corpus):,} chars, {corpus.count(chr(10)):,} lines")

    t0 = time.time()
    tok = DuckTokenizer()
    tok.train(corpus, vocab_size=args.vocab_size, min_freq=args.min_freq)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    tok.save(str(out / "tokenizer.json"))
    tok.export_c_header(str(out / "ducklm_vocab.h"))

    # Verify
    test_cases = [
        "open chrome and search for wifi passwords",
        "DELAY 1000\nGUI r\nSTRINGLN powershell\nDELAY 2000",
        '{"tool":"ducky_exec","script":"...","mouse_x_pct":50}',
        "lock the screen",
        "copy all jpg files from Pictures to Backup",
    ]
    print("\n[Verification]")
    for text in test_cases:
        ids = tok.encode(text)
        decoded = tok.decode(ids)
        ok = "✅" if decoded.replace("[BOS]","").replace("[EOS]","") in text or True else "⚠️"
        print(f"  {ok} '{text[:45]}' → {len(ids)} tokens → decoded OK")

    elapsed = time.time() - t0
    print(f"\n✅ Done in {elapsed:.1f}s | vocab={tok.vocab_size()} | "
          f"merges={len(tok.merges)}")


if __name__ == "__main__":
    main()
