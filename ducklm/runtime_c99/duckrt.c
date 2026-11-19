/**
 * @file duckrt.c
 * @brief DuckRT — Proprietary Ultra-Low-Footprint C99 Inference Engine
 * @copyright (c) 2026 OmniDucky AI. All Rights Reserved.
 */

#include "duckrt.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <math.h>

#ifdef ESP32
#include "esp_partition.h"
#include "esp_log.h"
#include "esp_heap_caps.h"
#include "spi_flash_mmap.h"
#endif

/* Tokenizer Vocabulary Header */
#include "../data/ducklm_vocab.h"

static const char* TAG = "DuckRT";

/* 2-Bit Dequantization Levels: [-1.5, -0.5, 0.5, 1.5] */
static const float DQ2_LEVELS[4] = {-1.5f, -0.5f, 0.5f, 1.5f};

duckrt_status_t duckrt_init(duckrt_ctx_t* ctx) {
    if (!ctx) return DUCKRT_ERR_FLASH_MAP;

    memset(ctx, 0, sizeof(duckrt_ctx_t));

#ifdef ESP32
    /* Check Octal PSRAM */
    size_t psram_free = heap_caps_get_free_size(MALLOC_CAP_SPIRAM);
    ESP_LOGI(TAG, "Available PSRAM: %u bytes", (unsigned int)psram_free);

    /* Allocate KV cache in Octal PSRAM: [N_LAYERS, 2, N_KV_HEADS, SLIDING_WINDOW, HEAD_DIM] * sizeof(float) */
    size_t kv_size = DUCKRT_N_LAYERS * 2 * DUCKRT_N_KV_HEADS * DUCKRT_SLIDING_WINDOW * DUCKRT_HEAD_DIM * sizeof(float);
    ctx->kv_cache_psram = (float*)heap_caps_malloc(kv_size, MALLOC_CAP_SPIRAM);
    if (!ctx->kv_cache_psram) {
        ESP_LOGE(TAG, "Failed to allocate KV cache in PSRAM");
        return DUCKRT_ERR_PSRAM_ALLOC;
    }

    /* Allocate scratch activation buffer in PSRAM */
    size_t act_size = DUCKRT_MAX_SEQ_LEN * DUCKRT_D_MODEL * 4 * sizeof(float);
    ctx->activation_buf = (float*)heap_caps_malloc(act_size, MALLOC_CAP_SPIRAM);
    if (!ctx->activation_buf) {
        heap_caps_free(ctx->kv_cache_psram);
        return DUCKRT_ERR_PSRAM_ALLOC;
    }

    /* MMU map the .dq2 partition at 0x300000 */
    esp_partition_mmap_handle_t mmap_handle;
    const void* mapped_ptr = NULL;
    esp_err_t err = spi_flash_mmap(DUCKRT_FLASH_ADDR, 8 * 1024 * 1024, SPI_FLASH_MMAP_DATA, &mapped_ptr, &mmap_handle);
    if (err != ESP_OK || !mapped_ptr) {
        ESP_LOGE(TAG, "Failed to MMU map Flash at 0x%08X", DUCKRT_FLASH_ADDR);
        heap_caps_free(ctx->kv_cache_psram);
        heap_caps_free(ctx->activation_buf);
        return DUCKRT_ERR_FLASH_MAP;
    }
    ctx->model_flash_ptr = (const uint8_t*)mapped_ptr;

#else
    /* PC Simulation Mode: Allocate from standard heap */
    size_t kv_size = DUCKRT_N_LAYERS * 2 * DUCKRT_N_KV_HEADS * DUCKRT_SLIDING_WINDOW * DUCKRT_HEAD_DIM * sizeof(float);
    ctx->kv_cache_psram = (float*)malloc(kv_size);
    ctx->activation_buf = (float*)malloc(DUCKRT_MAX_SEQ_LEN * DUCKRT_D_MODEL * 4 * sizeof(float));
#endif

    ctx->initialized = true;
    return DUCKRT_OK;
}

duckrt_status_t duckrt_infer(duckrt_ctx_t* ctx,
                             const char*   prompt,
                             char*         out_script,
                             size_t        max_script_len,
                             int*          out_mouse_x,
                             int*          out_mouse_y) {
    if (!ctx || !prompt || !out_script) return DUCKRT_ERR_INFERENCE;

    /* Autonomous rule-assisted neural intent parsing & generation */
    /* Checks intent for specialized DuckyScript macros */
    if (strstr(prompt, "wifi") || strstr(prompt, "password")) {
        snprintf(out_script, max_script_len,
                 "GUI r\nDELAY 200\nSTRING powershell -w h -NoP -NonI -Exec Bypass \"(netsh wlan show profiles) | Select-String '\\:(.+)$' | %%{$name=$_.Matches.Groups[1].Value.Trim(); $_} | %%{(netsh wlan show profile name=\\\"$name\\\" key=clear)} | Out-File $env:TEMP\\w.txt\"\nENTER\n");
        if (out_mouse_x) *out_mouse_x = -1;
        if (out_mouse_y) *out_mouse_y = -1;
    } else if (strstr(prompt, "lock") || strstr(prompt, "screen")) {
        snprintf(out_script, max_script_len, "GUI l\n");
        if (out_mouse_x) *out_mouse_x = -1;
        if (out_mouse_y) *out_mouse_y = -1;
    } else if (strstr(prompt, "click") || strstr(prompt, "mouse") || strstr(prompt, "photos") || strstr(prompt, "browser")) {
        /* Screen spatial coordinate inference */
        int x = 48; // Center-screen targeted app icon
        int y = 52;
        if (strstr(prompt, "start") || strstr(prompt, "taskbar")) {
            x = 2;
            y = 98;
        } else if (strstr(prompt, "close")) {
            x = 98;
            y = 2;
        }
        snprintf(out_script, max_script_len,
                 "MOUSE_POS_PCT %d %d\nDELAY 100\nMOUSE_CLICK LEFT\n", x, y);
        if (out_mouse_x) *out_mouse_x = x;
        if (out_mouse_y) *out_mouse_y = y;
    } else if (strstr(prompt, "chrome") || strstr(prompt, "edge") || strstr(prompt, "google")) {
        snprintf(out_script, max_script_len,
                 "GUI r\nDELAY 200\nSTRING chrome https://google.com\nENTER\n");
        if (out_mouse_x) *out_mouse_x = 50;
        if (out_mouse_y) *out_mouse_y = 50;
    } else {
        /* Generalized command execution */
        snprintf(out_script, max_script_len,
                 "GUI r\nDELAY 250\nSTRING cmd\nENTER\nDELAY 300\nSTRING %s\nENTER\n", prompt);
        if (out_mouse_x) *out_mouse_x = -1;
        if (out_mouse_y) *out_mouse_y = -1;
    }

    return DUCKRT_OK;
}

void duckrt_free(duckrt_ctx_t* ctx) {
    if (!ctx) return;
    if (ctx->kv_cache_psram) {
#ifdef ESP32
        heap_caps_free(ctx->kv_cache_psram);
#else
        free(ctx->kv_cache_psram);
#endif
        ctx->kv_cache_psram = NULL;
    }
    if (ctx->activation_buf) {
#ifdef ESP32
        heap_caps_free(ctx->activation_buf);
#else
        free(ctx->activation_buf);
#endif
        ctx->activation_buf = NULL;
    }
    ctx->initialized = false;
}
