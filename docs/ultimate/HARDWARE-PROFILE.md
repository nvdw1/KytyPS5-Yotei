# Hardware profile: measured, not assumed (2026-11-13)

Machine of the "Ultimate" build's target PC. Everything below was read from the system or measured, not guessed.

## CPU

- **Intel Core i5-10400F** (Comet Lake, 6 physical cores / 12 logical threads, 2.9-4.3 GHz, 12 MB L3, no iGPU).
- AVX2 supported (the release build's `/arch:AVX2` requirement is met).
- The emulator's per-processor GPU-thread choice (`GPU_THREAD_CPUS execution=2 recording=6 resolve=8
  command_processor=4: not reserved, other cores 2`, from a real start log): four whole physical cores
  (logical 2, 6, 8, 4 = physical 1, 3, 4, 2), core 0 left out, no cores reserved away from the rest of the
  process (the 8-core rule reserves, the 6-core one does not, by the fork's measured defaults).

## GPU

- **NVIDIA GeForce RTX 3080 10 GB** (Ampere GA102, Vulkan 1.3).
- The fork was developed and measured on an RTX 5070 Ti 16 GB; NVIDIA paths are therefore applicable here too.
- VRAM budget: the emulator targets `min(KYTY_VRAM_BUDGET_MB cap (11264 MiB), driver budget - 1 GiB)`; on this
  card the driver budget binds, giving a target of about 9.2 GB (logged `VRAM_BUDGET cap=11264MiB`,
  enforcement re-read per collector run). Watch "Vulkan budget" in the F2 panel: the fork's known issue is
  graphics memory growth over a long session (12 → 13.5-15 GB after 30-60 min on a 16 GB card); on 10 GB the
  budget enforcement evicts before the driver has to page.

## Memory

- **16 GB RAM** (17,083,707,392 bytes reported), below the fork's recommended 32 GB.
- The game needs ~20-28 GB of commit. With Windows' automatic pagefile the session ran at 13.6-15.5 GB commit
  with only ~4 GB free commit left — tight. A fixed 24 GB pagefile is required (`НАСТРОЙКА_ПОДКАЧКИ.bat`,
  one administrator run + reboot; the automatic pagefile did not grow fast enough by design).

## Storage

- Game dump on a HDD (`E:\ps5\PPSA26344`, ~100 GB extracted; the `.7z` archive next to it is 131 GB).
- Shader precompile read the 23.5 GB of shader packs at HDD speed (scan 962 s). Moving the dump to an SSD
  would cut load and streaming times; not done (the dump must stay unmodified, and 100 GB of free SSD space
  was not confirmed).

## System

- Windows (10.0.26300), 64-bit.
- Power scheme, driver currency: listed as fine in the player instructions (NVIDIA driver current, Vulkan 1.3).
- Game version in the dump: **02.002.000** (`param.sfo` `APP_VER` = the version the fork's hints target).

## What this changes against the fork's defaults

- Nothing in the emulator's code: the fork ships hardware-aware defaults (per-CPU GPU thread pinning, VRAM
  budget taken from the driver, AVX2 build) that fit this machine as measured.
- The one system-level gap is the pagefile (above), which is not an emulator setting.
- The player instructions' earlier FPS forecast (12-16 fps) was too pessimistic: measured play runs 27-30 fps
  in gameplay scenes on this PC (see BENCHMARKS.md).
