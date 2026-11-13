# Benchmarks: measured results and protocol (2026-11-13)

Numbers come from real runs on the target PC (see HARDWARE-PROFILE.md). Nothing is extrapolated or
fabricated; scene names are as accurate as the logs allow.

## Protocol

- **Live A/B in one run** (the fork's own method): `KYTY_LIVE_AB=<switch>` flips the switch every
  `KYTY_LIVE_AB_PERIOD_MS` inside one run, so both phases share the scene, the caches and the CPU state.
  Report `PERF live_ab summary` lines (fps mean/SD/pooled, frame-time median, busy/fence-wait per frame)
  and check `draws_per_frame` equality — a phase that draws less is reading stale data, and its gain is not
  a gain.
- **Stability runs** without the harness: plain `kyty_emulator.exe --game <eboot> --game-patch <plan>`,
  bounded by wall time, judged by the run log (no `FATAL`, clean exit).
- Scene-to-scene comparisons across separate runs are **not** used for fps claims (the fork's own rule:
  single test places, < 2% is noise). Cross-run numbers below are recorded as context only.

## In-game baseline and resolution experiments (2026-11-13, evening)

Correction to the first pass: the 27-30 fps scenes above are the menus and loading. **Real gameplay** (entered
through the fork's test pad script: Cross in the main menu, then X through the intro prompts) measures:

- **baseline (Render-1080p mod, as shipped): frame-time median 159.3 ms = 6.3 fps** (781 in-game frames,
  mean 162.0 ms, p95 186.6 ms — zero frames in the 15-fps tier).
- **dynamic resolution unlocked (Render-1080p off): 4.8 fps** — worse. The game's GPU timer reads host GPU
  busy time and keeps a high internal size on its own (the emulator's GPU is not saturated at 46-70%);
  removing the lock only lets cutscenes go up to 4K.
- **Render-720p (the table-entry rewrite, new mod): 6.6 fps (median 152.6 ms, +2-5%)** — kept as an
  optional mod (`render720` in the 2.002 catalog), not a default: the frame is CPU-side-bound, not
  pixel-bound.

Reading: in gameplay the frame is dominated by the emulator's CPU-side work (the fork's own #1 open lead,
"the execution thread's per-draw work"), not by pixels or draw count — the game already self-manages its
scalability ladder to level 13 here. The 15 fps target needs the ladder force (a setter found by a data
breakpoint, see LADDER-HUNT.md) plus the fork's own future CPU-side work, or a stronger CPU; on the fork's
hardware-scaled expectation this PC's open world is ~10-15 fps and towns less.

## Automated gameplay entry (the test pad script)

`KYTY_TEST_PAD_SCRIPT` (the fork's unattended-run tool, controller.cpp): Cross = button mask 0x4000. The
shipped automation (now a catalog mod `autoCross`, and enabled in the player's patch plan as an env
entry): presses Cross at frames 500-920 (the main menu), then every 1,000 frames up to 12,000, which
covers the game's "press X" prompts about five minutes in; extra presses are harmless. Verified:
the game reaches gameplay unattended in ~2.5-5 minutes.

## Baseline (the fork as shipped, v0.1.6 + the 2026-11-13 fix, this PC)

Measured 2026-11-13, gameplay area shortly after a new game's start (the intro world; ~40-65 draws/frame,
245-350 dispatches/frame, `KYTY_LIVE_AB=KYTY_PERF_DIRECT_RANGES`, 20 s phases):

| Metric | phase off (default) | phase on |
|---|---|---|
| fps mean (SD) | 29.42 (0.78) | 27.21 (1.75) |
| fps pooled | 29.42 | 27.25 |
| frame-time median | 33.3 ms | 33.3 ms |
| GPU-thread busy | 14.8 ms/frame | 14.7 ms/frame |
| fence wait | 3.7 ms/frame | 3.9 ms/frame |

Reading: the direct-ranges read path (the switch under test) is worth ~1-2 fps here at most and the median
frame time does not move — consistent with the fork's own +1% measurement at its test place. **The default
(off? on?) stays as shipped**: `KYTY_PERF_DIRECT_RANGES` default is 1; the A/B compares 0 vs 1, and the on
phase's slightly lower mean came with scene drift (the heavy scene entered mid-run), medians equal.

Context (same build, same session, scene changes inside one run — not A/B-comparable):

- Gameplay scene: 26.9-30.0 fps, frame-time median 33.3-34.2 ms.
- Heavy cinematic scene (~300-630 draws/frame, ~1200-1570 dispatches/frame): 8-9.3 fps, median 109-116 ms —
  the fork's documented cutscene cost (the author measures 11-12 fps there on a 9800X3D + RTX 5070 Ti, so the
  6-core CPU is the difference, not a defect of this build).

## Stability

- Clean run (no measurement switches), 45+ minutes through gameplay and the heavy cinematic scene, ending in
  a clean exit (`PLAY_EXIT=0`), zero `FATAL` lines. Two earlier sessions that crashed (the fatal fixed in
  commit `ca53297`) both ran with the live A/B harness active; the fixed paths are reachable only while a
  deferred callback flips the direct-range switch — normal play keeps the mode constant.

## Precompile cost (one-time)

- Hints import: 11,969/11,969 shaders found in the dump, scan of 23.5 GB in 962 s.
- Precompile: 20,174/20,174 jobs (15,447 shaders/pipelines) in 2,872 s on the 6-core CPU; driver pipeline
  cache saved (1.36 GB). Later starts reuse it (`PRECOMPILE_DONE saved=1`, journal 0 records to redo).

## Open (not yet measured on this PC)

- The frame-start GPU→CPU dependency (the fork's doc: 8-9 ms per frame on the dev PC) — needs a
  `KYTY_TRACE_SYNC_TIMELINE=1` run here before any work on it.
- The game's scalability ladder for version 2.002: the 1.512 memory offsets do not transfer (the two known
  .text anchors shifted differently, +0x81EB0 for render1080 vs a different shift at the ladder site; the
  bytes at the shifted ladder guess are unrelated code). A runtime memory scan for the level variable is the
  planned approach (see COMPATIBILITY.md). Gains measured by the fork on 1.512: +13% (level 4) to +79%
  (level 15) on its route, at the cost of the game's own plainer detail.
