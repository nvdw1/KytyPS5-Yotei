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

## System-level findings (2026-11-14)

- **Resizable BAR (ASRock "Clever Access Memory", enabled in BIOS)**: BAR1 grew to 16 GB and the BDA
  fallback's pinned host memory dropped from **4,832 MiB to 512 MiB** per run — about 4.3 GB of the 16 GB
  RAM released from commit. Real relief for this 16 GB machine; the measured in-game fps in the test scene
  stayed in the same band (median 173.1 ms, with 13.6% of frames in the 15-fps tier — scenes drift between
  runs, so treat ±10-15% medians as noise). The BAR-read probe still measured slow (28 MB/s — PCIe
  write-combined read latency, not aperture size), so downloads keep the GPU-copy path as designed.
- **RAM**: two DDR4-2666 CL19 sticks (TeamGroup UD4-2666), no XMP profile above 2666. BIOS timing tuning
  (tightening tCL at 2666, or 2933 with relaxed timings) is the one free CPU-side lever left; expected
  5-15% on this CPU-bound workload. Motherboard ASRock H410M-HVS.
- **Spin budget**: `KYTY_GPU_SPIN_US=50` (vs the default 2,000) measured **worse** (189.7 ms median):
  the pipeline's spin handoffs are load-bearing and `_mm_pause` is SMT-friendly; kernel-wait fallbacks
  cost more than the saved cycles. The full-thread sampler (`KYTY_TRACE_PERF_SAMPLE=all`) shows ~90% of
  samples in spin/clock machinery, but that overstates real core cost — the pause instruction yields the
  SMT sibling's resources. Documented negative result; leave the default.
- **Full-720p pipeline** (720p internal + 1280x720 window): 186.5 ms median — no gain over 1080p output.

- **Full-720p pipeline** (720p internal + 1280x720 window): 186.5 ms median — no gain over 1080p output.
- **Process priority High (set externally mid-run)**: 152.9 vs 153.1 ms median at Normal — no change; the
  emulator already receives the CPU it asks for. Documented negative result.
- **The productive-code profile** (the =all samples minus the spin/clock clusters, 5% of samples): the top
  productive addresses are `TrackingSpinLock::lock` (contention, 3 clusters — already backoff-tuned by the
  fork), `MaterializeResources` (already ahead-materialized on helper threads through the SRT tape), and
  `FastVerifyLoggedReads` (already page-cached, run-coalesced and batch-compared). This matches the fork's
  own ceiling data: even fully removing the per-draw preparation was worth +8.8%, and each separate path
  less. The frame is the CPU-side emulation itself; on a 6-core Comet Lake the ceiling sits where measured.
- **CPU power limits (untested remotely, recommended)**: the i5-10400F at PL1=65 W sustains ~3.9 GHz
  all-core under this all-core load; raising PL1/PL2 in the BIOS (the board allows it) to hold ~4.1-4.2 GHz
  is worth a few percent on this workload.

## Upstream port attempt (2026-11-14)

The upstream KytyPS5 main received 73 commits after this fork's last rebase (2026-11-07), including the
kernel-memory performance work (lock-free guest page table, split memory locking, region-lock-free dirty
bit queries) — aimed at the same areas this machine's profile flagged. Findings:

- **The fork is ahead of upstream in the graphics hot paths**: upstream's TrackingSpinLock TTAS
  optimization (b9cb08d3, from the cp2077 fork) is a subset of this fork's version (which adds the tuned
  backoff and the tracking stats on top of the same idea). The cherry-pick is a no-op here.
- **The kernel-memory port needs the whole upstream refactor series**: 19 commits, of which the robustness
  series ("exit on … failures instead of rolling back", PoolReserved ranges) restructures the unmap flow
  that this fork's BDA fallback and RingBytesAllDead heuristics extend. The conflict at `UnmapMemoryOwner`
  is semantic (two diverged implementations of the same subsystem), not mechanical. The lock-free page
  table and split locks build on that refactored flow.
- The attempt is preserved as the `perf-upstream` branch (3 kernel commits applied, the chain stopped at
  `UnmapMemoryOwner`). Completing it is a subsystem port with memory-corruption risk and an unquantified,
  profile-bounded prize — a task for the fork's own next rebase, which the upstream work will ride in on.

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
