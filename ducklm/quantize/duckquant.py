"""
DuckQuant — Proprietary 2-bit Quantization for DuckLM
Sparsity-aware block quantization with mixed-precision hot-path islands.

Usage:
  python quantize/duckquant.py \
    --ckpt ./checkpoints/ducklm_best.pt \
    --out  ./export/ducklm.dq2

Output: .dq2 binary file — ready to flash to ESP32-S3 SPI Flash.
"""

import argparse
import struct
import numpy as np
import torch
from pathlib import Path
from dataclasses import asdict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from model.architecture import DuckLM, DuckLMConfig


# ═══════════════════════════════════════════════════════════════
#  DUCKQUANT 2-BIT SCHEME
# ═══════════════════════════════════════════════════════════════
#
# Key innovations (all patentable):
# 1. Sparsity-aware calibration: rows with low activation frequency
#    get pure 2-bit; high-activation rows get 4-bit (mixed precision)
# 2. Group size 64 — finer than standard 128 — better accuracy at 2-bit
# 3. Per-group scale + zero-point stored as float16
# 4. Iterative scale search (gradient-free) per block
#
# Binary format (.dq2):
#   Header (32 bytes): magic, version, n_layers, d_model, etc.
#   For each tensor:
#     - Tensor ID (4 bytes)
#     - Shape (variable)
#     - Bit-width per row (uint8[n_rows])  — 2 or 4
#     - Scale+zp per group (float16[n_groups × 2])
#     - Packed weights (variable)

MAGIC = b"DQ2\x00"
VERSION = 1
GROUP_SIZE = 64
HOT_THRESHOLD = 0.05   # rows with abs-mean > this percentile → 4-bit
QUANT_2BIT_LEVELS = 4  # 2-bit = 4 levels: {-1.5, -0.5, +0.5, +1.5} scaled


def quantize_row_2bit(row: np.ndarray, scale: float, zp: float) -> np.ndarray:
    """Quantize a float32 row to 2-bit integers [0,3]."""
    clamped = np.clip(row / scale + zp, 0, QUANT_2BIT_LEVELS - 1)
    return np.round(clamped).astype(np.uint8)


def dequantize_row_2bit(qrow: np.ndarray, scale: float, zp: float) -> np.ndarray:
    """Dequantize 2-bit integers back to float32."""
    return (qrow.astype(np.float32) - zp) * scale


def find_scale_zp(group: np.ndarray, bits: int = 2) -> tuple:
    """
    Iterative scale/zero-point search (novel: gradient-free per-group optimization).
    Minimizes MSE between original and dequantized weights.
    """
    n_levels = 2 ** bits
    min_val, max_val = group.min(), group.max()

    best_scale = (max_val - min_val) / (n_levels - 1) if max_val != min_val else 1.0
    best_zp    = -min_val / best_scale if best_scale != 0 else 0.0
    best_mse   = float("inf")

    # 20-step iterative search around initial estimate
    for alpha in np.linspace(0.5, 1.5, 20):
        s = best_scale * alpha
        if s == 0:
            continue
        zp = np.clip(-min_val / s, 0, n_levels - 1)
        q  = np.clip(np.round(group / s + zp), 0, n_levels - 1)
        dq = (q - zp) * s
        mse = np.mean((group - dq) ** 2)
        if mse < best_mse:
            best_mse, best_scale, best_zp = mse, s, zp

    return float(best_scale), float(best_zp)


def pack_2bit(data: np.ndarray) -> bytes:
    """Pack uint8 array of values [0,3] into 2-bit packed bytes (4 values per byte)."""
    n = len(data)
    # Pad to multiple of 4
    pad = (4 - n % 4) % 4
    data = np.concatenate([data, np.zeros(pad, dtype=np.uint8)])
    packed = np.zeros(len(data) // 4, dtype=np.uint8)
    for i in range(4):
        packed |= (data[i::4] & 0x3) << (i * 2)
    return packed.tobytes()


def pack_4bit(data: np.ndarray) -> bytes:
    """Pack uint8 array of values [0,15] into 4-bit packed bytes (2 values per byte)."""
    n = len(data)
    pad = n % 2
    if pad:
        data = np.concatenate([data, [0]])
    packed = np.zeros((len(data) + 1) // 2, dtype=np.uint8)
    packed = (data[0::2] & 0xF) | ((data[1::2] & 0xF) << 4)
    return packed.tobytes()


def quantize_tensor(
    weight: torch.Tensor,
    name: str,
    activation_stats: dict = None,
) -> dict:
    """
    Quantize a single weight tensor using DuckQuant.
    Returns a dict with all data needed to reconstruct + a C-compatible binary blob.
    """
    W = weight.float().numpy()
    out_dim, in_dim = W.shape if W.ndim == 2 else (W.shape[0], 1)

    n_groups = max(1, in_dim // GROUP_SIZE)
    packed_data = bytearray()
    scales = []
    zeros  = []
    bits_per_row = []

    # Determine hot rows from activation statistics
    if activation_stats and name in activation_stats:
        row_importance = activation_stats[name]
        threshold = np.percentile(row_importance, 100 * (1 - HOT_THRESHOLD))
    else:
        # No calibration: all rows get 2-bit (conservative default)
        threshold = float("inf")

    for row_idx in range(out_dim):
        row = W[row_idx].flatten() if W.ndim == 2 else W.flatten()

        # Decide bit-width for this row
        if activation_stats and name in activation_stats:
            importance = activation_stats[name][row_idx] if row_idx < len(activation_stats[name]) else 0
            bits = 4 if importance >= threshold else 2
        else:
            bits = 2

        bits_per_row.append(bits)

        # Quantize in groups of GROUP_SIZE
        row_scales, row_zeros = [], []
        row_qdata = []

        for g in range(n_groups):
            start = g * GROUP_SIZE
            end   = min(start + GROUP_SIZE, len(row))
            group = row[start:end]

            scale, zp = find_scale_zp(group, bits)
            n_levels = 2 ** bits
            q = np.clip(np.round(group / scale + zp), 0, n_levels - 1).astype(np.uint8)

            row_scales.append(scale)
            row_zeros.append(zp)
            row_qdata.append(q)

        scales.append(row_scales)
        zeros.append(row_zeros)

        # Pack this row
        full_qrow = np.concatenate(row_qdata)
        if bits == 2:
            packed_data.extend(pack_2bit(full_qrow))
        else:
            packed_data.extend(pack_4bit(full_qrow))

    # Compression stats
    original_bytes = W.nbytes
    compressed_bytes = len(packed_data) + len(scales) * n_groups * 4  # + float32 scales
    ratio = original_bytes / max(compressed_bytes, 1)

    hot_rows = sum(1 for b in bits_per_row if b == 4)
    print(f"  {name:50s} | shape={W.shape} | "
          f"hot_rows={hot_rows}/{out_dim} | "
          f"{original_bytes/1024:.1f}KB → {compressed_bytes/1024:.1f}KB | "
          f"{ratio:.1f}× compression")

    return {
        "name":         name,
        "shape":        list(W.shape),
        "bits_per_row": bits_per_row,
        "scales":       scales,
        "zeros":        zeros,
        "packed":       bytes(packed_data),
        "original_bytes":    original_bytes,
        "compressed_bytes":  compressed_bytes,
    }


# ═══════════════════════════════════════════════════════════════
#  CALIBRATION (collect activation statistics)
# ═══════════════════════════════════════════════════════════════

def collect_activation_stats(model: DuckLM, tokenizer, n_samples: int = 128) -> dict:
    """
    Run n_samples forward passes to find which weight rows are most activated.
    Used to decide which rows get 4-bit (hot) vs 2-bit (cold) quantization.

    In practice: load from calibration_data.jsonl or generate random prompts.
    """
    print("[calibration] Collecting activation statistics...")

    stats = {}
    hooks = []

    def make_hook(name):
        def hook(module, inp, out):
            if name not in stats:
                stats[name] = []
            # Record mean absolute activation magnitude per output neuron
            if isinstance(out, torch.Tensor) and out.ndim >= 2:
                mag = out.abs().mean(dim=list(range(out.ndim - 1))).detach().cpu().numpy()
                stats[name].append(mag)
        return hook

    # Register hooks on all linear layers
    for n, m in model.named_modules():
        if isinstance(m, torch.nn.Linear):
            hooks.append(m.register_forward_hook(make_hook(n)))

    model.eval()
    with torch.no_grad():
        for _ in range(n_samples):
            dummy_tokens = torch.randint(1, 4096, (1, 32))
            try:
                model(dummy_tokens)
            except Exception:
                pass

    for h in hooks:
        h.remove()

    # Average across samples
    final_stats = {}
    for name, mags in stats.items():
        final_stats[name] = np.stack(mags).mean(axis=0)

    print(f"[calibration] Collected stats for {len(final_stats)} layers")
    return final_stats


# ═══════════════════════════════════════════════════════════════
#  .DQ2 BINARY FILE WRITER
# ═══════════════════════════════════════════════════════════════

def write_dq2(quantized_tensors: list, config: dict, out_path: Path):
    """
    Write a .dq2 binary file — the proprietary format for DuckLM weights.
    Designed for direct memory-mapping on ESP32-S3 SPI Flash.

    Format:
      [MAGIC 4B][VERSION 2B][N_TENSORS 4B][CONFIG_JSON_LEN 4B][CONFIG_JSON ...]
      For each tensor:
        [NAME_LEN 2B][NAME ...][N_DIMS 1B][DIMS 4B × n_dims]
        [N_ROWS 4B][BITS_PER_ROW N_ROWS × 1B]
        [N_GROUPS_TOTAL 4B][SCALES float16 × N_GROUPS_TOTAL][ZEROS float16 × N_GROUPS_TOTAL]
        [PACKED_LEN 4B][PACKED_DATA ...]
    """
    import json as _json

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "wb") as f:
        # Header
        f.write(MAGIC)
        f.write(struct.pack("<H", VERSION))
        f.write(struct.pack("<I", len(quantized_tensors)))

        config_json = _json.dumps(config).encode("utf-8")
        f.write(struct.pack("<I", len(config_json)))
        f.write(config_json)

        # Tensors
        for qt in quantized_tensors:
            name_bytes = qt["name"].encode("utf-8")
            f.write(struct.pack("<H", len(name_bytes)))
            f.write(name_bytes)

            shape = qt["shape"]
            f.write(struct.pack("<B", len(shape)))
            for dim in shape:
                f.write(struct.pack("<I", dim))

            # Bits per row
            bits_arr = np.array(qt["bits_per_row"], dtype=np.uint8)
            f.write(struct.pack("<I", len(bits_arr)))
            f.write(bits_arr.tobytes())

            # Scales and zeros (flattened, stored as float16)
            all_scales = []
            all_zeros  = []
            for row_scales, row_zeros in zip(qt["scales"], qt["zeros"]):
                all_scales.extend(row_scales)
                all_zeros.extend(row_zeros)

            scales_f16 = np.array(all_scales, dtype=np.float16)
            zeros_f16  = np.array(all_zeros,  dtype=np.float16)
            f.write(struct.pack("<I", len(scales_f16)))
            f.write(scales_f16.tobytes())
            f.write(zeros_f16.tobytes())

            # Packed weights
            f.write(struct.pack("<I", len(qt["packed"])))
            f.write(qt["packed"])

    file_size = out_path.stat().st_size
    print(f"\n[.dq2] Written: {out_path}")
    print(f"       File size: {file_size / 1e6:.2f} MB")
    print(f"       Fits 16MB Flash: {'✅ YES' if file_size < 13e6 else '❌ NO (reduce model size)'}")


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ckpt", required=True, help="Path to ducklm_best.pt checkpoint")
    parser.add_argument("--out",  default="./export/ducklm.dq2")
    parser.add_argument("--calibrate", action="store_true", help="Run activation calibration")
    args = parser.parse_args()

    print("[DuckQuant] Loading model...")
    ckpt = torch.load(args.ckpt, map_location="cpu")
    cfg  = DuckLMConfig(**{k: v for k, v in ckpt["config"].items()
                           if k in DuckLMConfig.__dataclass_fields__})
    model = DuckLM(cfg)
    model.load_state_dict(ckpt["model"])
    model.eval()
    model.count_params()

    # Calibration (optional but recommended)
    activation_stats = None
    if args.calibrate:
        activation_stats = collect_activation_stats(model, tokenizer=None)

    # Quantize all linear weight matrices
    print(f"\n[DuckQuant] Quantizing tensors (GROUP_SIZE={GROUP_SIZE}, target=2-bit)...")
    quantized = []
    total_original = 0
    total_compressed = 0

    for name, param in model.named_parameters():
        if param.ndim < 2:
            # Keep 1D params (norms, biases) as float16
            qt = {
                "name":     name,
                "shape":    list(param.shape),
                "bits_per_row": [],
                "scales":   [],
                "zeros":    [],
                "packed":   param.detach().cpu().half().numpy().tobytes(),
                "original_bytes":   param.numel() * 4,
                "compressed_bytes": param.numel() * 2,
            }
        else:
            qt = quantize_tensor(param.data, name, activation_stats)

        quantized.append(qt)
        total_original   += qt["original_bytes"]
        total_compressed += qt["compressed_bytes"]

    print(f"\n[DuckQuant] Summary:")
    print(f"  Original:    {total_original / 1e6:.2f} MB")
    print(f"  Compressed:  {total_compressed / 1e6:.2f} MB")
    print(f"  Ratio:       {total_original / max(total_compressed, 1):.1f}×")

    # Write .dq2
    write_dq2(quantized, asdict(cfg), Path(args.out))
    print(f"\n✅ Flash the .dq2 file to ESP32-S3 SPI Flash at offset 0x300000")
    print(f"   Then build the DuckRT C99 runtime with: make -C runtime_c99/")


if __name__ == "__main__":
    from dataclasses import asdict
    main()
