"""
DuckLM — Training Monitor with Checkpoint Failsafe
Proprietary SRGN Architecture — All rights reserved

Features:
  - Auto-checkpoint every 5 minutes (time-based, never lose progress)
  - Resume from last checkpoint automatically on restart
  - Thermal safety: pauses if GPU > 85C or CPU > 90C
  - Console progress every 50 steps
  - Final checkpoint + best checkpoint always saved

Usage:
  python train/train_monitor.py --steps 50000
  python train/train_monitor.py --steps 50000 --resume  # auto-resume from last ckpt
"""

import os
import sys
import time
import json
import math
import glob
import argparse
import traceback
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional

import torch
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

# Optional: psutil for CPU temp (gracefully absent)
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

sys.path.insert(0, str(Path(__file__).parent.parent))
from model.architecture import DuckLM, DuckLMConfig
from train.train_tokenizer import DuckTokenizer


# ═══════════════════════════════════════════════════════════════
#  THERMAL SAFETY MONITOR
# ═══════════════════════════════════════════════════════════════

GPU_TEMP_LIMIT = 85   # °C — pause training above this
CPU_TEMP_LIMIT = 90   # °C

def get_gpu_temp() -> Optional[float]:
    """Read GPU temperature via nvidia-smi."""
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3
        )
        return float(result.stdout.strip())
    except Exception:
        return None

def get_cpu_temp() -> Optional[float]:
    """Read CPU temp via psutil (Windows: needs OpenHardwareMonitor or similar)."""
    if not HAS_PSUTIL:
        return None
    try:
        temps = psutil.sensors_temperatures()
        if not temps:
            return None
        for name, entries in temps.items():
            for entry in entries:
                if entry.current and entry.current > 0:
                    return entry.current
    except Exception:
        return None
    return None

def check_thermal_safety() -> tuple[bool, str]:
    """
    Returns (safe, message).
    safe=False → caller should pause training immediately.
    """
    gpu_t = get_gpu_temp()
    cpu_t = get_cpu_temp()

    if gpu_t is not None and gpu_t >= GPU_TEMP_LIMIT:
        return False, f"🌡️ GPU OVERHEAT: {gpu_t}°C ≥ {GPU_TEMP_LIMIT}°C — PAUSING TRAINING"
    if cpu_t is not None and cpu_t >= CPU_TEMP_LIMIT:
        return False, f"🌡️ CPU OVERHEAT: {cpu_t}°C ≥ {CPU_TEMP_LIMIT}°C — PAUSING TRAINING"
    return True, f"GPU={gpu_t or '?'}°C  CPU={cpu_t or '?'}°C  ✅ OK"


# ═══════════════════════════════════════════════════════════════
#  TRAINING STATE
# ═══════════════════════════════════════════════════════════════

@dataclass
class TrainState:
    step:        int   = 0
    total_steps: int   = 0
    loss:        float = 0.0
    best_loss:   float = float("inf")
    start_time:  float = field(default_factory=time.time)
    losses:      List[float] = field(default_factory=list)
    gpu_name:    str   = "CPU"
    batch_size:  int   = 32
    lr:          float = 3e-4

    def eta_str(self) -> str:
        if self.step == 0:
            return "calculating..."
        elapsed = time.time() - self.start_time
        steps_remaining = self.total_steps - self.step
        sps = self.step / elapsed
        eta_s = steps_remaining / max(sps, 1e-5)
        h, m = int(eta_s // 3600), int((eta_s % 3600) // 60)
        return f"{h}h {m}m"

    def elapsed_str(self) -> str:
        s = time.time() - self.start_time
        h, m = int(s // 3600), int((s % 3600) // 60)
        return f"{h}h {m:02d}m"

    def steps_per_min(self) -> float:
        elapsed = max(time.time() - self.start_time, 1)
        return self.step / elapsed * 60

    def build_report(self) -> str:
        avg_loss = sum(self.losses[-100:]) / max(len(self.losses[-100:]), 1)
        pct = self.step / max(self.total_steps, 1) * 100
        bar_filled = int(pct / 5)
        bar = "█" * bar_filled + "░" * (20 - bar_filled)
        gpu_t = get_gpu_temp()
        _, thermal_msg = check_thermal_safety()

        return f"""
╔══════════════════════════════════════════════════════╗
║          DuckLM TRAINING PROGRESS REPORT             ║
╠══════════════════════════════════════════════════════╣
║                                                      ║
║  Progress:  [{bar}] {pct:.1f}%        ║
║  Step:      {self.step:,} / {self.total_steps:,}                    ║
║  Loss:      {avg_loss:.4f}  (best: {self.best_loss:.4f})           ║
║  Speed:     {self.steps_per_min():.1f} steps/min                     ║
║  Elapsed:   {self.elapsed_str()}                             ║
║  ETA:       {self.eta_str()}                             ║
║                                                      ║
║  Hardware:  {self.gpu_name[:40]:40s}  ║
║  Batch:     {self.batch_size}  |  LR: {self.lr:.6f}              ║
║  Thermal:   {thermal_msg[:40]:40s}  ║
║                                                      ║
╠══════════════════════════════════════════════════════╣
║  STATUS: {"✅ TRAINING" if self.step < self.total_steps else "✅ COMPLETE":40s}  ║
╚══════════════════════════════════════════════════════╝

Auto-checkpoint every 5 min — safe to shut down anytime.
Resume anytime with: python train/train_monitor.py --resume
"""


# ═══════════════════════════════════════════════════════════════
#  DATASET
# ═══════════════════════════════════════════════════════════════

class DuckDataset(Dataset):
    SEP = "\n### Output:\n"
    PRE = "### Instruction:\n"

    def __init__(self, path: str, tokenizer: DuckTokenizer, max_len: int = 256):
        self.tokenizer = tokenizer
        self.max_len   = max_len
        self.items     = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                obj = json.loads(line.strip())
                self.items.append(obj)
        print(f"[dataset] {len(self.items):,} pairs loaded")

    def __len__(self):
        return len(self.items)

    def __getitem__(self, idx):
        item = self.items[idx]
        full = f"{self.PRE}{item['instruction']}{self.SEP}{item['output']}"
        instr_text = f"{self.PRE}{item['instruction']}{self.SEP}"

        all_ids   = self.tokenizer.encode(full)
        instr_ids = self.tokenizer.encode(instr_text)
        sep_idx   = min(len(instr_ids), len(all_ids) - 1)

        if len(all_ids) > self.max_len:
            all_ids = all_ids[:self.max_len]
        sep_idx = min(sep_idx, len(all_ids) - 1)

        pad_len  = self.max_len - len(all_ids)
        input_ids = all_ids + [self.tokenizer.PAD_ID] * pad_len

        labels = [-100] * sep_idx + all_ids[sep_idx:] + [-100] * pad_len
        labels = labels[:self.max_len]

        return {
            "input_ids": torch.tensor(input_ids, dtype=torch.long),
            "labels":    torch.tensor(labels,    dtype=torch.long),
        }


# ═══════════════════════════════════════════════════════════════
#  LR SCHEDULE
# ═══════════════════════════════════════════════════════════════

def cosine_lr(step, warmup, total, max_lr, min_lr=None):
    min_lr = min_lr or max_lr * 0.1
    if step < warmup:
        return max_lr * (step / warmup)
    if step >= total:
        return min_lr
    p = (step - warmup) / (total - warmup)
    return min_lr + 0.5 * (max_lr - min_lr) * (1 + math.cos(math.pi * p))


# ═══════════════════════════════════════════════════════════════
#  CHECKPOINT HELPERS
# ═══════════════════════════════════════════════════════════════

def find_latest_checkpoint(out_dir: Path) -> Optional[Path]:
    """Find the most recent checkpoint to resume from."""
    # Prefer ducklm_resume.pt (rolling save), then step checkpoints
    resume_path = out_dir / "ducklm_resume.pt"
    if resume_path.exists():
        return resume_path

    step_ckpts = sorted(
        out_dir.glob("ducklm_step*.pt"),
        key=lambda p: int(p.stem.replace("ducklm_step", ""))
    )
    if step_ckpts:
        return step_ckpts[-1]
    return None


def save_checkpoint(out_dir: Path, model, optimizer, scaler, state: TrainState,
                    tag: str = "resume"):
    """Save a full resumable checkpoint."""
    path = out_dir / f"ducklm_{tag}.pt"
    torch.save({
        "step":       state.step,
        "model":      model.state_dict(),
        "optimizer":  optimizer.state_dict(),
        "scaler":     scaler.state_dict(),
        "config":     asdict(DuckLMConfig()),
        "best_loss":  state.best_loss,
        "losses_tail": state.losses[-500:],   # keep last 500 for continuity
    }, path)
    return path


# ═══════════════════════════════════════════════════════════════
#  MAIN TRAINING LOOP
# ═══════════════════════════════════════════════════════════════

def train(args):
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available! Training requires the dedicated NVIDIA GPU.")
    
    # Exclusively lock to dedicated NVIDIA GPU (Device 0)
    torch.cuda.set_device(0)
    device = torch.device("cuda:0")
    gpu_name = torch.cuda.get_device_name(0)

    print(f"\n{'='*60}")
    print(f"  DuckLM Training — Proprietary SRGN Architecture")
    print(f"  Dedicated GPU: {gpu_name} (Device ID: {torch.cuda.current_device()})")
    print(f"  Checkpoint interval: every 5 minutes")
    print(f"  Thermal limits: GPU<{GPU_TEMP_LIMIT}°C  CPU<{CPU_TEMP_LIMIT}°C")
    print(f"{'='*60}\n")

    # Model
    cfg   = DuckLMConfig()
    model = DuckLM(cfg).to(device)
    model.count_params()

    # Tokenizer
    tok_path = Path(args.tokenizer)
    if tok_path.exists():
        tokenizer = DuckTokenizer.load(str(tok_path))
        print(f"[tokenizer] Loaded from {tok_path} | vocab={tokenizer.vocab_size()}")
    else:
        raise FileNotFoundError(f"Tokenizer not found at {tok_path}")

    # Dataset + DataLoader
    dataset = DuckDataset(args.data, tokenizer, max_len=cfg.max_seq_len)
    loader  = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=0,
        pin_memory=(device.type == "cuda"),
        drop_last=True,
    )

    # Optimizer + AMP scaler
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.lr,
        betas=(0.9, 0.95),
        weight_decay=0.1,
    )
    use_amp = device.type == "cuda"
    scaler  = torch.amp.GradScaler("cuda", enabled=use_amp)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Training state
    state = TrainState(
        total_steps = args.steps,
        gpu_name    = gpu_name,
        batch_size  = args.batch_size,
        lr          = args.lr,
        start_time  = time.time(),
    )

    # ── RESUME ──────────────────────────────────────────────────
    resume_step = 0
    if args.resume:
        ckpt_path = find_latest_checkpoint(out_dir)
        if ckpt_path:
            print(f"\n[resume] ✅ Loading checkpoint: {ckpt_path}")
            ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
            model.load_state_dict(ckpt["model"])
            optimizer.load_state_dict(ckpt["optimizer"])
            if "scaler" in ckpt:
                scaler.load_state_dict(ckpt["scaler"])
            state.step      = ckpt["step"]
            state.best_loss = ckpt.get("best_loss", float("inf"))
            state.losses    = ckpt.get("losses_tail", [])
            resume_step     = state.step
            print(f"[resume] Resuming from step {state.step:,} | best_loss={state.best_loss:.4f}\n")
        else:
            print("[resume] No checkpoint found — starting fresh.\n")
    # ────────────────────────────────────────────────────────────

    last_ckpt_time  = time.time()
    ckpt_interval   = args.ckpt_interval   # seconds (default 300 = 5 min)
    running_loss    = 0.0
    log_interval    = 50
    thermal_pause_logged = False

    print(f"[train] Starting from step {state.step:,} → target {args.steps:,} | "
          f"batch={args.batch_size} | lr={args.lr}\n")
    model.train()

    try:
        for epoch in range(9999):
            for batch in loader:
                if state.step >= args.steps:
                    break

                # ── THERMAL SAFETY CHECK (every 100 steps) ──────
                if state.step % 100 == 0:
                    safe, thermal_msg = check_thermal_safety()
                    if not safe:
                        print(f"\n{'!'*60}")
                        print(f"  {thermal_msg}")
                        print(f"  Saving emergency checkpoint before pause...")
                        save_checkpoint(out_dir, model, optimizer, scaler, state, tag="resume")
                        print(f"  Checkpoint saved. Sleeping 60s to let hardware cool...")
                        print(f"{'!'*60}\n")
                        time.sleep(60)
                        thermal_pause_logged = True
                        # Re-check; if still hot, keep sleeping
                        while True:
                            safe2, msg2 = check_thermal_safety()
                            if safe2:
                                print(f"[thermal] ✅ Cooled down — resuming training.\n")
                                break
                            print(f"[thermal] Still hot: {msg2} — waiting 30s more...")
                            time.sleep(30)
                # ────────────────────────────────────────────────

                input_ids = batch["input_ids"].to(device, non_blocking=True)
                labels    = batch["labels"].to(device, non_blocking=True)

                # Update LR
                lr = cosine_lr(state.step, args.warmup, args.steps, args.lr)
                for g in optimizer.param_groups:
                    g["lr"] = lr
                state.lr = lr

                # Forward
                with torch.amp.autocast("cuda", enabled=use_amp):
                    logits = model(input_ids)
                    shift_logits = logits[:, :-1].contiguous()
                    shift_labels = labels[:, 1:].contiguous()
                    loss = F.cross_entropy(
                        shift_logits.view(-1, cfg.vocab_size),
                        shift_labels.view(-1),
                        ignore_index=-100,
                    )

                # Backward
                optimizer.zero_grad(set_to_none=True)
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(optimizer)
                scaler.update()

                loss_val = loss.item()
                running_loss += loss_val
                state.losses.append(loss_val)
                state.step += 1

                if loss_val < state.best_loss:
                    state.best_loss = loss_val

                # Console log
                if state.step % log_interval == 0:
                    avg = running_loss / log_interval
                    running_loss = 0.0
                    gpu_t = get_gpu_temp()
                    print(
                        f"  step={state.step:6d}/{args.steps} | "
                        f"loss={avg:.4f} | best={state.best_loss:.4f} | "
                        f"lr={lr:.6f} | {state.steps_per_min():.1f} spm | "
                        f"ETA={state.eta_str()} | GPU={gpu_t or '?'}°C"
                    )

                # ── 5-MINUTE AUTO CHECKPOINT ─────────────────────
                now = time.time()
                if now - last_ckpt_time >= ckpt_interval:
                    ckpt_path = save_checkpoint(
                        out_dir, model, optimizer, scaler, state, tag="resume"
                    )
                    # Also save a timestamped copy
                    ts = int(now)
                    tagged = save_checkpoint(
                        out_dir, model, optimizer, scaler, state,
                        tag=f"step{state.step}"
                    )
                    print(f"  [ckpt] ⏱️  5-min checkpoint → {ckpt_path.name}  "
                          f"(step={state.step:,} | loss={state.best_loss:.4f})")
                    last_ckpt_time = now

                    # Save best separately
                    recent = state.losses[-500:] if state.losses else [state.best_loss]
                    if state.best_loss <= min(recent):
                        save_checkpoint(
                            out_dir, model, optimizer, scaler, state, tag="best"
                        )
                        print(f"  [ckpt] ⭐ New best loss={state.best_loss:.4f} → ducklm_best.pt")
                # ─────────────────────────────────────────────────

            if state.step >= args.steps:
                break

    except KeyboardInterrupt:
        print(f"\n[train] ⚠️  Interrupted at step {state.step:,}. Saving emergency checkpoint...")
        save_checkpoint(out_dir, model, optimizer, scaler, state, tag="resume")
        print(f"[train] ✅ Checkpoint saved. Resume with: python train/train_monitor.py --resume")
        sys.exit(0)

    # ── TRAINING COMPLETE ────────────────────────────────────────
    final_path = save_checkpoint(out_dir, model, optimizer, scaler, state, tag="final")
    print(f"\n[train] ✅ Training complete! {state.step:,} steps | best loss={state.best_loss:.4f}")
    print(f"[train] Final checkpoint → {final_path}")
    print(f"\nNEXT STEPS:")
    print(f"  1. Quantize:  python quantize/duckquant.py --ckpt {out_dir}/ducklm_final.pt --calibrate")
    print(f"  2. Flash:     esptool.py --chip esp32s3 write_flash 0x300000 export/ducklm.dq2")
    print(state.build_report())


# ═══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data",          default="./data/sft_pairs.jsonl")
    p.add_argument("--tokenizer",     default="./data/tokenizer.json")
    p.add_argument("--out",           default="./checkpoints")
    p.add_argument("--steps",         type=int,   default=50000)
    p.add_argument("--batch_size",    type=int,   default=32)
    p.add_argument("--lr",            type=float, default=3e-4)
    p.add_argument("--warmup",        type=int,   default=500)
    p.add_argument("--resume",        action="store_true",
                                      help="Auto-resume from last checkpoint")
    p.add_argument("--ckpt_interval", type=int,   default=300,
                                      help="Checkpoint every N seconds (default 300=5min)")
    args = p.parse_args()
    train(args)
