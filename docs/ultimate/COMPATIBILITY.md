# Compatibility report: verified vs unverified (2026-11-13)

The rule this project works by: a launch is not compatibility, and unverified areas are reported as
unverified. Nothing below is claimed beyond the evidence named next to it.

## Verified on this PC (evidence)

| Area | Evidence |
|---|---|
| Game boots to the intro world (new game) | two runs, window "Ghost of Yōtei, PPSA26344, 02.002.000", 6,000+ frames each |
| Gameplay rendering in the intro world | live A/B logs: 40-65 draws/frame, 245-350 dispatches/frame, frame-time median 33.3 ms |
| Audio, input, save menu presence | not individually driven by an automated input script — **unverified** beyond "the run kept going with no errors" |
| Shader precompile (one-time) | 20,174/20,174 jobs, cache saved, later starts reuse it |
| 45+ minute session stability | clean exit 0, zero fatal lines |
| The 2026-11-13 fatal fix | both crash paths closed; see docs/FIXES.md and commit `ca53297` |
| Render-1080p mod on 2.002 | shipped default in the fork's catalog (byte patterns verified against this dump's eboot) |
| Direct-ranges switch on this PC | live A/B: no fps change beyond noise at the test place (median 33.3 ms both phases) |

## Known-broken / costly areas (from the fork's own docs, version 2.002 in play here)

- Heavy in-engine cutscenes run at a fraction of play speed (8-9 fps here; 11-12 fps on the dev PC's better
  hardware). Parts of the Snake fight (fire scenes) drop similarly.
- Checkered shadows after a shader-compile stutter (fork issue #11): quit to the main menu and load the save.
- Graphics memory grows over a long session; on this 10 GB card watch the F2 "Vulkan budget", save + reload
  when it nears the limit.
- Quality mode's internal-resolution flicker — bypassed by the default Render-1080p mod, not fixed
  (`KYTY_FIX_IMAGE_MEMORY_OWNER=1` is exact but costs 10-15% fps).

## Unverified (honesty first)

- **Full-game progression.** No automated playthrough exists: combat, quests, save/load round-trips, later
  areas and the ending were not driven by this project. The fork's own v0.1.6 hints cover shaders "from the
  start to the Snake fight, the open world and much further" — areas beyond the hints compile shaders during
  play (first-visit stutter).
- **PlayStation-specific peripherals** (DualSense features, touchpad beyond the F6 mouse mode).
- **AMD/Intel GPUs** — irrelevant for this PC, noted for completeness.
- **Version 1.512 and other game versions** — this dump is 02.002.000; other versions are untested here.

## The game dump

`E:\ps5\PPSA26344` was read during preparation (hints import scans its shader packs) and by the running
emulator. It was never modified; the launcher's writes (shader caches, saves) go next to the emulator.
