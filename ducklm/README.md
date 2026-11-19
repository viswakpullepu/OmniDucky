# DuckLM — Proprietary On-Device VLA Model for OmniDucky
> © 2026 — All Rights Reserved. Proprietary and Confidential.

A custom ultra-small Vision-Language-Action model that runs entirely on
**ESP32-S3 N16R8** (16MB Flash, 8MB PSRAM) with zero internet connection.

## Architecture: Sparse Rotary Gated Network (SRGN)
- 28M parameters × 2-bit DuckQuant = **~7 MB Flash**
- KV cache (sliding window + GQA 4:1) = **~650 KB PSRAM**
- Speed: **~1.5–2 tokens/sec** on ESP32-S3 @ 240MHz
- Input: text command + optional 224×224 screenshot
- Output: JSON action → `{ tool, script, mouse_x_pct, mouse_y_pct }`

## Quick Start

```bash
pip install -r requirements.txt

# 1. Generate training data
python train/generate_data.py --n 50000 --out ./data

# 2. Train tokenizer (4096-BPE)
python train/train_tokenizer.py --corpus ./data/tokenizer_corpus.txt

# 3. Train model (~6-10h on A100)
python train/pretrain.py --data ./data/sft_pairs.jsonl --steps 20000

# 4. Quantize to 2-bit .dq2 format
python quantize/duckquant.py --ckpt ./checkpoints/ducklm_best.pt --calibrate

# 5. Flash to ESP32-S3
# Flash ducklm.dq2 at offset 0x300000 using esptool.py
esptool.py --chip esp32s3 write_flash 0x300000 export/ducklm.dq2
```

## Model Sanity Check

```bash
python model/architecture.py
```

## Patentable Claims
1. SRGN architecture (GQA 4:1 + ReLU²-sparse FFN + SwiGLU in sub-30M VLA)
2. DuckQuant (sparsity-aware 2-bit + mixed 4-bit hot paths)
3. Domain 4K-BPE vocabulary co-designed with hardware constraints
4. Grammar-masked constrained decoding (JSON schema enforcement at logits)
5. ScreenPatch spatial coordinate bias (novel vision→coordinate pathway)
6. AI_EXEC DuckyScript primitive (NL-to-HID as single embedded command)

## Directory Structure
```
ducklm/
├── model/
│   └── architecture.py     ← SRGN model (PyTorch)
├── train/
│   ├── generate_data.py    ← Synthetic SFT data generator
│   ├── train_tokenizer.py  ← BPE-4096 tokenizer training
│   └── pretrain.py         ← Training loop
├── quantize/
│   └── duckquant.py        ← 2-bit DuckQuant compression
├── runtime_c99/            ← (next) C99 DuckRT inference engine
└── requirements.txt
```
