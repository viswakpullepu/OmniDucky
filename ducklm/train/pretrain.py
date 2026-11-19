"""
DuckLM — Training Script (Pre-training + SFT in one pass)
Runs on: single A100 / RTX 3090+ (or Vast.ai ~$0.30/hr)

Usage:
  python train/pretrain.py \
    --data ./data/sft_pairs.jsonl \
    --tokenizer ./data/tokenizer.model \
    --out ./checkpoints \
    --steps 20000

Estimated time: ~6-10 hours on A100 for 28M model, 50K pairs × 20 epochs
"""

import json
import math
import time
import argparse
from pathlib import Path
from dataclasses import asdict

import torch
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

# Our model
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from model.architecture import DuckLM, DuckLMConfig


# ═══════════════════════════════════════════════════════════════
#  TOKENIZER (uses sentencepiece BPE trained on domain corpus)
# ═══════════════════════════════════════════════════════════════

try:
    import sentencepiece as spm

    class DuckTokenizer:
        def __init__(self, model_path: str):
            self.sp = spm.SentencePieceProcessor()
            self.sp.Load(model_path)
            self.bos_id = self.sp.bos_id()
            self.eos_id = self.sp.eos_id()
            self.pad_id = self.sp.pad_id()

        def encode(self, text: str) -> list:
            return [self.bos_id] + self.sp.EncodeAsIds(text) + [self.eos_id]

        def decode(self, ids: list) -> str:
            return self.sp.DecodeIds(ids)

        def __len__(self):
            return self.sp.GetPieceSize()

except ImportError:
    print("[!] sentencepiece not installed. Using dummy tokenizer for shape testing.")

    class DuckTokenizer:
        def __init__(self, model_path: str = None):
            self.bos_id = 1; self.eos_id = 2; self.pad_id = 0
        def encode(self, text: str) -> list:
            # Dummy: character-level for testing shapes
            ids = [1] + [min(ord(c), 4095) for c in text[:200]] + [2]
            return ids
        def decode(self, ids: list) -> str:
            return "".join(chr(i) if 32 <= i < 127 else '?' for i in ids)
        def __len__(self): return 4096


# ═══════════════════════════════════════════════════════════════
#  DATASET
# ═══════════════════════════════════════════════════════════════

class DuckLMDataset(Dataset):
    """
    Each item: instruction → output JSON
    Packed as: [BOS] instruction [SEP] output [EOS]
    Loss computed only on output tokens (instruction is context, not supervised).
    """

    SEP = "\n### Output:\n"
    PRE = "### Instruction:\n"

    def __init__(self, path: str, tokenizer: DuckTokenizer, max_len: int = 256):
        self.tokenizer = tokenizer
        self.max_len = max_len
        self.items = []

        with open(path, encoding="utf-8") as f:
            for line in f:
                obj = json.loads(line.strip())
                self.items.append(obj)

        print(f"[dataset] Loaded {len(self.items)} pairs from {path}")

    def __len__(self):
        return len(self.items)

    def __getitem__(self, idx):
        item = self.items[idx]
        instruction = item["instruction"]
        output      = item["output"]

        # Format: system prompt + instruction + separator + output
        full_text = f"{self.PRE}{instruction}{self.SEP}{output}"
        tokens = self.tokenizer.encode(full_text)

        # Find separator position to mask instruction tokens in loss
        instruction_text = f"{self.PRE}{instruction}{self.SEP}"
        instruction_tokens = self.tokenizer.encode(instruction_text)
        sep_idx = len(instruction_tokens) - 1  # output starts here

        # Pad / truncate to max_len
        if len(tokens) > self.max_len:
            tokens = tokens[:self.max_len]
        sep_idx = min(sep_idx, len(tokens) - 1)

        pad_len = self.max_len - len(tokens)
        input_ids = tokens + [self.tokenizer.pad_id] * pad_len

        # Labels: -100 for instruction tokens (don't compute loss on them)
        labels = [-100] * sep_idx + tokens[sep_idx:] + [-100] * pad_len
        labels = labels[:self.max_len]

        return {
            "input_ids": torch.tensor(input_ids, dtype=torch.long),
            "labels":    torch.tensor(labels,    dtype=torch.long),
        }


# ═══════════════════════════════════════════════════════════════
#  TRAINING LOOP
# ═══════════════════════════════════════════════════════════════

def cosine_lr(step: int, warmup: int, total: int, max_lr: float, min_lr: float) -> float:
    if step < warmup:
        return max_lr * step / warmup
    if step > total:
        return min_lr
    progress = (step - warmup) / (total - warmup)
    return min_lr + 0.5 * (max_lr - min_lr) * (1 + math.cos(math.pi * progress))


def train(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[train] Device: {device}")

    # Model
    cfg = DuckLMConfig()
    model = DuckLM(cfg).to(device)
    model.count_params()

    # Tokenizer
    tokenizer = DuckTokenizer(args.tokenizer) if args.tokenizer else DuckTokenizer()

    # Dataset
    dataset = DuckLMDataset(args.data, tokenizer, max_len=cfg.max_seq_len)
    loader  = DataLoader(dataset, batch_size=args.batch_size, shuffle=True,
                         num_workers=2, pin_memory=True, drop_last=True)

    # Optimizer (AdamW with decoupled weight decay)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.lr,
        betas=(0.9, 0.95),
        weight_decay=0.1,
        eps=1e-8,
    )

    # Mixed precision
    scaler = torch.cuda.amp.GradScaler(enabled=(device.type == "cuda"))

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    step = 0
    total_loss = 0.0
    best_loss = float("inf")
    t0 = time.time()

    print(f"\n[train] Starting training for {args.steps} steps...")
    print(f"        Batch={args.batch_size}, LR={args.lr}, Warmup={args.warmup}")

    model.train()
    for epoch in range(999):
        for batch in loader:
            if step >= args.steps:
                break

            input_ids = batch["input_ids"].to(device)
            labels    = batch["labels"].to(device)

            # LR schedule
            lr = cosine_lr(step, args.warmup, args.steps, args.lr, args.lr * 0.1)
            for g in optimizer.param_groups:
                g["lr"] = lr

            # Forward + loss
            with torch.cuda.amp.autocast(enabled=(device.type == "cuda")):
                logits = model(input_ids)                           # [B, T, V]
                # Shift: predict next token
                shift_logits = logits[:, :-1, :].contiguous()
                shift_labels = labels[:, 1:].contiguous()
                loss = F.cross_entropy(
                    shift_logits.view(-1, cfg.vocab_size),
                    shift_labels.view(-1),
                    ignore_index=-100,
                )

            # Backward
            optimizer.zero_grad()
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()

            total_loss += loss.item()
            step += 1

            # Logging
            if step % 100 == 0:
                avg_loss = total_loss / 100
                total_loss = 0.0
                elapsed = time.time() - t0
                tps = step / elapsed
                eta = (args.steps - step) / max(tps, 1e-5)
                print(
                    f"  step={step:6d}/{args.steps} | loss={avg_loss:.4f} | "
                    f"lr={lr:.6f} | {tps:.1f} steps/s | ETA {eta/60:.0f}m"
                )

            # Save checkpoint
            if step % 2000 == 0 or step == args.steps:
                avg_save_loss = total_loss / max(1, step % 100)
                ckpt_path = out_dir / f"ducklm_step{step}.pt"
                torch.save({
                    "step":        step,
                    "model":       model.state_dict(),
                    "optimizer":   optimizer.state_dict(),
                    "config":      asdict(cfg),
                    "loss":        avg_save_loss,
                }, ckpt_path)
                print(f"  [ckpt] Saved → {ckpt_path}")

                if avg_save_loss < best_loss:
                    best_loss = avg_save_loss
                    best_path = out_dir / "ducklm_best.pt"
                    torch.save({"step": step, "model": model.state_dict(), "config": asdict(cfg)}, best_path)
                    print(f"  [ckpt] New best! → {best_path}")

        if step >= args.steps:
            break

    print(f"\n[train] Done. Best loss: {best_loss:.4f}")
    print(f"        Run quantize/duckquant.py to compress for ESP32.")


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data",       default="./data/sft_pairs.jsonl")
    parser.add_argument("--tokenizer",  default="./data/tokenizer.model")
    parser.add_argument("--out",        default="./checkpoints")
    parser.add_argument("--steps",      type=int,   default=20000)
    parser.add_argument("--batch_size", type=int,   default=32)
    parser.add_argument("--lr",         type=float, default=3e-4)
    parser.add_argument("--warmup",     type=int,   default=500)
    args = parser.parse_args()
    train(args)
