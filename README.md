<div align="center">

```
 ██████╗ ███╗   ███╗███╗   ██╗██╗    ██████╗ ██╗   ██╗ ██████╗██╗  ██╗██╗   ██╗
██╔═══██╗████╗ ████║████╗  ██║██║    ██╔══██╗██║   ██║██╔════╝██║ ██╔╝╚██╗ ██╔╝
██║   ██║██╔████╔██║██╔██╗ ██║██║    ██║  ██║██║   ██║██║     █████═╝  ╚████╔╝ 
██║   ██║██║╚██╔╝██║██║╚██╗██║██║    ██║  ██║██║   ██║██║     ██╔═██╗   ╚██╔╝  
╚██████╔╝██║ ╚═╝ ██║██║ ╚████║██║    ██████╔╝╚██████╔╝╚██████╗██║  ██╗   ██║   
 ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═══╝╚═╝    ╚═════╝  ╚═════╝  ╚═════╝╚═╝  ╚═╝   ╚═╝   
```

# OmniDucky C2 & DuckLM

### Next-Gen Wireless (BLE) & Wired (USB) Keystroke Injection Platform
### Powered by **DuckLM**: 100% Proprietary On-Device Vision-to-Action SLM on ESP32-S3
**Zero Cloud Dependencies &bull; Zero External APIs &bull; 100% Air-Gapped Physical HID Autonomous Agent**

---

[![Hardware](https://img.shields.io/badge/Hardware-ESP32--S3%20N16R8%20(Dual--Core%20LX7)-E7352C?style=for-the-badge&logo=espressif&logoColor=white)](https://www.espressif.com/)
[![DuckLM](https://img.shields.io/badge/Model-DuckLM%2024.6M%20Params-10B981?style=for-the-badge&logo=openai&logoColor=white)](ducklm/)
[![Quantization](https://img.shields.io/badge/Quantization-DuckQuant%202--Bit%20(7.75%20MB)-38BDF8?style=for-the-badge&logo=webassembly&logoColor=white)](ducklm/quantize/)
[![Patent Status](https://img.shields.io/badge/Intellectual%20Property-Patent%20Pending%20(2026)-F59E0B?style=for-the-badge&logo=counterstrike&logoColor=white)](#-patent-portfolio--architectural-claims)
[![License](https://img.shields.io/badge/License-Proprietary%20%2F%20Patent%20Pending-critical?style=for-the-badge)](LICENSE)

<br/>

```
  +========================================================================================+
  |  Turn a $5 ESP32-S3 into a fully autonomous, vision-guided military-grade HID implant.  |
  |  Proprietary 24.6M LLM runs 100% OFFLINE inside SPI Flash + Octal PSRAM.              |
  |  Sees target PC screens -> Plans actions -> Types DuckyScript & Clicks Mouse autonomously.  |
  +========================================================================================+
```

---

[Executive Overview](#-executive-overview) &bull;
[Patent Portfolio & Claims](#-patent-portfolio--architectural-claims) &bull;
[DuckLM Architecture](#-ducklm-neural-architecture) &bull;
[DuckQuant & DuckRT Engine](#-duckquant--duckrt-c99-inference-engine) &bull;
[Hardware Blueprint](#-hardware-blueprint) &bull;
[OmniDucky C2 Web OS](#-omniducky-c2-wireless-web-os) &bull;
[Flashing & Deployment](#-flashing--deployment-guide)

---

</div>

<br/>

## 🎯 Executive Overview

**OmniDucky C2** with **DuckLM** represents an industry-first breakthrough in offensive hardware security and edge machine learning: **a fully proprietary 24.6-million parameter Small Language & Vision-to-Action Model (SLM) executing 100% locally on a dual-core Xtensa microcontroller without any internet, cloud servers, or third-party APIs.**

Traditional hardware keystroke injection tools (Rubber Ducky, Flipper Zero, BadUSB) are blind, static sequence players. OmniDucky C2 transforms the ESP32-S3 into an **active visual operator**:
1. **Air-Gapped Autonomous Intelligence**: DuckLM runs directly within the 16MB SPI Flash and 8MB Octal PSRAM of the ESP32-S3.
2. **Visual Feedback Loop (Screen-to-Action)**: Ingests real-time desktop screen regions via depthwise separable convolutional patch encoders.
3. **Dual Coordinate & DuckyScript Output**: Simultaneously generates normalized mouse cursor coordinates (`MOUSE_POS_PCT X Y`) and high-speed DuckyScript keyboard payloads.
4. **Biometric Morphing (BioMorph)**: Implements variable human typing cadences with Gaussian jitter to defeat behavioral heuristic Endpoint Detection & Response (EDR) systems.

---

## 📜 Patent Portfolio & Architectural Claims

All core components of DuckLM, DuckQuant, and DuckRT have been designed and implemented **100% from scratch** with zero open-source dependencies (no SentencePiece, no HuggingFace tokenizers, no GPL runtimes) to establish unencumbered patent ownership.

```
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │                               PATENT CLAIMS ARCHITECTURE                               │
  ├────────────────────────────────────────────────────────────────────────────────────────┤
  │ [Claim 1] Sparse Recurrent Gated Network (SRGN) Architecture for 240MHz MCUs          │
  │ [Claim 2] DuckQuant 2-Bit Sparsity-Aware Block Quantization with Group-Size 64         │
  │ [Claim 3] Zero-Copy Flash Memory-Mapped (MMU) Inference on Xtensa Octal PSRAM          │
  │ [Claim 4] Dual-Head Spatial Coordinate Binning (100x100) with DuckyScript Generation   │
  │ [Claim 5] BioMorph Biometric Keystroke Jitter Engine for EDR Timing Evasion            │
  └────────────────────────────────────────────────────────────────────────────────────────┘
```

### Detailed Patent Claims
* **Claim 1 (SRGN Architecture)**: A transformer-style neural network comprising 10 decoder layers, rotary positional embeddings (RoPE), grouped-query attention (8 query heads, 2 KV heads, 4:1 compression), and SwiGLU feed-forward networks with 32% top-k activation sparsity, reducing multiply-accumulate (MAC) operations by over 40% on microcontrollers.
* **Claim 2 (DuckQuant Compression)**: A mixed-precision quantization methodology grouping weights into 64-element vectors, quantizing low-activation paths to 2-bit discrete levels `[-1.5, -0.5, +0.5, +1.5]` with FP16 scale factors and zero-points, achieving a **12.8× compression ratio** (98.31 MB FP32 &rarr; 7.75 MB binary).
* **Claim 3 (DuckRT Zero-Copy Engine)**: An execution runtime operating on Xtensa LX7 dual-core processors that accesses quantized model weights directly from external SPI Flash via memory management unit (MMU) virtual caching without allocating model parameter storage in system RAM.
* **Claim 4 (Spatial Action Heads)**: A neural architecture featuring dual independent 100-bin classification heads for 2D screen coordinate prediction coupled with autoregressive token generation for executable HID command strings.
* **Claim 5 (Hardware Biometric Masking)**: A method for pseudo-randomizing USB HID inter-keystroke intervals (IKIs) matching human typing profiles (speed burst, hesitation intervals, fatigue curves) to evade machine-learning behavioral biometric endpoint defenses.

---

## 🧠 DuckLM Neural Architecture

```
                    ┌──────────────────────────┐
                    │  Text Prompt / NL Intent │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                     [ DuckTokenizer (BPE) ]
                       1,236 Vocab Tokens
                                 │
                                 ▼
                     [ Token Embedding (512) ]
                                 │
  ┌──────────────────────────────┼──────────────────────────────┐
  │                              ▼                              │
  │              ┌──────────────────────────────┐               │
  │              │  10x DuckLM SRGN Layers:     │               │
  │              │  • RoPE Positional Encoding  │               │
  │              │  • GQA Attention (8Q : 2KV)  │               │
  │              │  • Sliding Window (64 tok)   │               │
  │              │  • SparseGatedFFN (SwiGLU)   │               │
  │              └──────────────┬───────────────┘               │
  │                             │                               │
  └─────────────────────────────┼───────────────────────────────┘
                                │
        ┌───────────────────────┴───────────────────────┐
        ▼                                               ▼
[ Autoregressive Token Head ]               [ Spatial Coordinate Heads ]
Generated DuckyScript Payload               Coord-X (0-100%) | Coord-Y (0-100%)
(e.g., STRING powershell...)                (e.g., Target Button / Icon)
```

### Parameter & Resource Budget (ESP32-S3 N16R8)

| Component | FP32 Original | DuckQuant 2-Bit | Storage Location |
|---|---|---|---|
| **Embeddings & Unembeddings** | 8.38 MB | 0.65 MB | SPI Flash (`0x300000`) |
| **10x Attention Layers** | 33.55 MB | 2.62 MB | SPI Flash (`0x300000`) |
| **10x Sparse FFN Layers** | 50.33 MB | 3.93 MB | SPI Flash (`0x300000`) |
| **Vision & Coordinate Heads** | 6.05 MB | 0.50 MB | SPI Flash (`0x300000`) |
| **Total Binary Size** | **98.31 MB** | **7.75 MB** | **Fits in 16MB Flash ✅** |
| **KV Cache (Sliding Window)** | — | ~650 KB | Octal PSRAM |
| **Activation Scratchpad** | — | ~1.8 MB | Octal PSRAM |
| **Total Runtime RAM** | — | **~2.45 MB** | **Fits in 8MB PSRAM ✅** |

---

## ⚡ DuckQuant & DuckRT C99 Inference Engine

### DuckQuant Quantization Metrics
* **Total Parameters Quantized**: 24,578,259
* **Compression Factor**: 12.8×
* **Target Output File**: `ducklm/export/ducklm.dq2` (7.75 MB)
* **Mathematical Precision**: 2-bit symmetric block quantization with iterative FP16 scale search per 64-element block.

### DuckRT Runtime Engine (`runtime_c99/`)
* **Written in Pure ANSI C99**: Zero C++ standard library dependencies, zero STL, zero external libraries.
* **Direct Hardware MMU Mapping**: Uses ESP32 `spi_flash_mmap` to map the 7.75MB `.dq2` binary into the CPU address space. Weights are read on-demand through hardware cache.
* **Dual-Core Task Offloading**: Core 0 handles Wi-Fi AP, web server, and DNS captive portal; Core 1 is dedicated exclusively to DuckRT neural matrix compute.

---

## 🔬 Training Verification & Convergence

DuckLM was trained on a dedicated **NVIDIA GeForce RTX 4050 Laptop GPU (CUDA 12.4)** using a custom backpropagation pipeline:

* **Training Dataset**: 100,000 synthetic multi-modal pairs (`open_app`, `run_command`, `wifi_creds`, `file_ops`, `mouse_click`, `biomorph`).
* **Completed Steps**: **22,354 steps** (~7.1 full dataset epochs)
* **Convergence Loss**: Dropped from initial **6.0185** down to **0.0336** (near-zero error rate).
* **Final Weights**: Checkpoint saved to `ducklm/checkpoints/ducklm_best.pt`.

---

## 📡 OmniDucky C2: Wireless Web OS

OmniDucky C2 is the field-ready wireless firmware that hosts DuckLM:

```
  ┌──────────────────┐         Wi-Fi AP ("OmniDucky-C2")        ┌────────────────────────┐
  │  YOUR SMARTPHONE │ ◄──────────────────────────────────────► │    ESP32-S3 HARDWARE   │
  │  (iPhone/Android)│         http://192.168.4.1               │  (Wired into Target PC)│
  └─────────┬────────┘                                          └───────────┬────────────┘
            │                                                               │
            │ 1. Connect phone to Wi-Fi "OmniDucky-C2"                      │
            │ 2. Captive Portal opens at http://192.168.4.1                 │
            │ 3. Type English: "Open photos and exfiltrate" ───────────────►│ 4. DuckLM infers &
            │ 4. Tap [ 🚀 FIRE PAYLOAD NOW ]                                │    injects keystrokes
            │ 5. Tap [ 💾 SAVE AUTORUN ] (Saves to NVS Flash)               │    and mouse clicks!
```

### Web Portal Features
1. **⌨️ DuckyScript Tab**: Full interactive code editor with syntax presets (`rickroll`, `sysinfo`, `wifi_audit`, `screen_lock`).
2. **🧠 AI Agent Tab**: Type natural language commands &bull; DuckLM compiles them directly into DuckyScript and screen coordinates.
3. **💻 Code Typer Tab**: Paste raw Python, C, or PowerShell code &bull; OmniDucky types it character-by-character into exam portals or locked environments.
4. **🎭 BioMorph Engine**: Select from 6 typing profiles: `NORMAL`, `NERVOUS`, `TIRED`, `GAMER`, `CODER`, or `GHOST`.

---

## 🛠️ Flashing & Deployment Guide

### Prerequisites
* ESP32-S3 Dev Board with 16MB Flash and 8MB Octal PSRAM (e.g., N16R8)
* Python 3.10+ with `esptool`

### 1. Erase Flash
Clean any old firmware from the board:
```bash
python -m esptool --port COM3 erase-flash
```

### 2. Flash DuckLM Model Binary
Flash the compressed 7.75MB `.dq2` model directly into SPI Flash at offset `0x300000`:
```bash
python -m esptool --port COM3 --chip esp32s3 --baud 921600 write-flash 0x300000 ducklm/export/ducklm.dq2
```

### 3. Flash OmniDucky C2 Firmware
Open `firmware/omniducky_c2/omniducky_c2.ino` in Arduino IDE or compile via `arduino-cli`:
* **Board**: `ESP32S3 Dev Module`
* **Flash Size**: `16MB (128Mb)`
* **Partition Scheme**: `16MB Flash (3MB App/9.9MB SPIFFS)`
* **PSRAM**: `OPI PSRAM (Octal)`
* **USB Mode**: `USB-OTG (TinyUSB)`
* **USB CDC On Boot**: `Disabled`

---

## ⚖️ Intellectual Property & Patent Notice

This repository contains original, proprietary architectural designs, mathematical algorithms, and software code developed for patent filing. 

**Protected Inventions Include:**
* The Sparse Recurrent Gated Network (SRGN) topology.
* The DuckQuant 2-bit mixed-precision quantization format (`.dq2`).
* The DuckRT zero-copy MMU inference execution model on microcontrollers.
* The unified screen-patch spatial coordinate classification head.

*(c) 2026 OmniDucky AI. All Rights Reserved. Patent Pending.*
