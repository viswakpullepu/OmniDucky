/**
 * @file duckrt.h
 * @brief DuckRT — Proprietary Ultra-Low-Footprint C99 Inference Engine
 * @copyright (c) 2026 OmniDucky AI. All Rights Reserved.
 *
 * Designed exclusively for ESP32-S3 (Xtensa Dual-Core LX7 + Octal PSRAM).
 * Memory-maps DuckQuant .dq2 models directly from SPI Flash at 0x300000.
 * Pure C99, zero open-source dependencies (patent-ready architecture).
 */

#ifndef DUCKRT_H
#define DUCKRT_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Architecture Hyperparameters */
#define DUCKRT_VOCAB_SIZE       1236
#define DUCKRT_D_MODEL          512
#define DUCKRT_N_LAYERS         10
#define DUCKRT_N_HEADS          8
#define DUCKRT_N_KV_HEADS       2
#define DUCKRT_HEAD_DIM         64
#define DUCKRT_D_FFN            1024
#define DUCKRT_MAX_SEQ_LEN      256
#define DUCKRT_SLIDING_WINDOW   64
#define DUCKRT_COORD_BINS       100

/* Flash Memory Mapping Offset */
#define DUCKRT_FLASH_ADDR       0x00300000

/* Runtime Status Codes */
typedef enum {
    DUCKRT_OK = 0,
    DUCKRT_ERR_FLASH_MAP = -1,
    DUCKRT_ERR_MAGIC = -2,
    DUCKRT_ERR_PSRAM_ALLOC = -3,
    DUCKRT_ERR_TOKENIZE = -4,
    DUCKRT_ERR_INFERENCE = -5
} duckrt_status_t;

/* Inference Context */
typedef struct {
    const uint8_t* model_flash_ptr;   /* MMU mapped address */
    float*         kv_cache_psram;    /* KV Cache allocated in Octal PSRAM */
    float*         activation_buf;    /* Activation scratchpad in PSRAM */
    int            curr_seq_len;
    bool           initialized;
} duckrt_ctx_t;

/* Public API */

/**
 * @brief Initialize DuckRT runtime and map .dq2 model from SPI Flash into ESP32 MMU.
 * @param ctx Pointer to runtime context.
 * @return DUCKRT_OK on success, negative error code otherwise.
 */
duckrt_status_t duckrt_init(duckrt_ctx_t* ctx);

/**
 * @brief Run end-to-end natural language to HID action inference.
 * @param ctx Runtime context.
 * @param prompt Input user prompt (e.g., "open powershell and steal wifi passwords").
 * @param out_script Output buffer for generated DuckyScript commands.
 * @param max_script_len Capacity of out_script buffer.
 * @param out_mouse_x Output normalized screen coordinate X (0-100%, -1 if not applicable).
 * @param out_mouse_y Output normalized screen coordinate Y (0-100%, -1 if not applicable).
 * @return DUCKRT_OK on success.
 */
duckrt_status_t duckrt_infer(duckrt_ctx_t* ctx,
                             const char*   prompt,
                             char*         out_script,
                             size_t        max_script_len,
                             int*          out_mouse_x,
                             int*          out_mouse_y);

/**
 * @brief Free PSRAM buffers and unmap SPI flash regions.
 */
void duckrt_free(duckrt_ctx_t* ctx);

#ifdef __cplusplus
}
#endif

#endif /* DUCKRT_H */
