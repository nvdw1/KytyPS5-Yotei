# The scalability ladder for game version 2.002: findings so far (2026-11-13)

The fork ships "scalability ladder" memory mods for game version 1.512 only
(`src/launcher/mods/PPSA26344.json`: the game's own overload levels 4/8/11/15, measured by the fork at
+13% to +79% fps on its route). Version 2.002's catalog (`PPSA26344_02.002.000.json`) has no ladder mod.
This page records a hunt for the 2.002 equivalent, so nobody starts from zero.

## What was established (all measured against the live game on this PC)

1. **The loaded image is host-addressable at a fixed base.** The loader maps eboot.bin into the process
   and the game-patch system writes it through plain host pointers
   (`Loader::GamePatch::Translate`: `target = program.base_vaddr + source_address - source_base`).
   Guest VA = host VA for the image; `source_base` for this game is `0x100000`
   (logged: `Game cheat: matched eboot.bin with source base 0x100000`).
2. **`base_vaddr` for a live run can be recovered without symbols**: the applied Render-1080p mod leaves
   its `on` bytes (`b9 0f 00 00 00 90`) at `base + 0xde01ec`; scanning the process memory found it at
   `0x900de01ec`, giving **`base_vaddr = 0x900000000`** (this run; ASLR of the host mapping may move it
   between runs — re-derive it the same way).
3. **The eboot is a SELF on disk** (magic `4f 15 3d 1d`); in-memory it is decrypted, so byte searches must
   run against process memory, not the file. The image's layout (from VirtualQueryEx at the base):
   text `0x900000000-0x9017ec000` (RX, 24.9 MB), data `0x9017ec000-0x901eac000` (RW, 6.8 MB),
   a large RW block `0x90202c000-0x907180000` (81 MB, bss-like), then reservations.
4. **The ladder level variable was found: host VA `0x90044d5278`** (image RVA `0x44d5278`, inside the big
   RW block). Method: snapshots of every qword ≤ 15 in the RW blocks, taken in different scenes (heavy
   cinematic vs gameplay), diffed; the level read **13 in the heavy scene and 7 in gameplay** (the game's
   own overload logic lowered detail in the heavy scene — it self-manages on the emulator too). Two
   snapshots 5 minutes apart in one scene changed only 85 variables in total, so the diff is clean.
5. **The code around it matches the 1.512 ladder semantics**: two functions read it
   (`mov edx, [rip+…]` at RVA `0x295839` and `0x295902`), compare it with a reference global, emit a
   marker (a pointer + length **11** — consistent with the 11-character string "Scalability" — through a
   call), write the value back unchanged, and maintain a max tracker (a global 16 bytes below,
   `0x44d5268`, written only when the level exceeds it). A neighbor global sits at `0x44d5270`.
6. **There is no rip-relative init in 2.002** — unlike 1.512 (whose mod patches an explicit
   `mov qword [rip+…], 0`), the 2.002 variable lives in the zero-initialized block, so the 1.512-style
   init patch has no target.

## Experiments (documented negative results)

Patching the two read sites to load a constant (`mov edx, N` + `nop`, offsets `0x00395839` / `0x00395902`,
off `8b1539fa2304` / `8b1570f92304`, on `baN000000090`):

- **N=8**: the heavy cinematic scene jumped from ~300-630 draws/frame (self-managed level ~13) to
  **~4,950 draws/frame** at 4.5-6 fps. The constant broke the game's own down-scaling: the applied level
  ended near full quality. This proves the variable is the real ladder (the change was dramatic and
  immediate), but the read feeds the *adjustment* logic, not the applied level.
- **N=15**: same result (~4,900 draws, no improvement).

Conclusion: the level the renderer applies is written elsewhere — through a register holding a struct
base (no rip-relative access in the text), i.e. the setter could not be located by the rip-relative scans
used here.

## Next steps (concrete)

1. **Find the setter with a data breakpoint** on `0x44d5278` (x64dbg attached to `kyty_emulator.exe`,
   hardware write breakpoint, 4 bytes): every scene change hits the setter. The write instruction is
   expected to be `mov [reg+disp], reg32` — record the struct base and displacement.
2. **Force the level through the setter**: the write is 6 bytes (`89 90 disp32`-shape); a constant write
   needs 10 bytes (`c7 80 disp32 imm32`), which does not fit. Two ways that fit:
   - nop the setter's write and let the fork's game-patch system place the constant through a **code cave**
     (`Loader::GamePatch` already allocates cave pages — `ReleaseCaves` in its code);
   - or patch the value the setter stores: if the level is computed into `edx` from a measured signal
     (the doc's "resource ring usage"), clamp that measurement upstream instead.
3. **Validate** with the fork's own signature: draws per frame must drop at the same place (level 8 ≈ 3,747
   on the 1.512 route), fps must rise, and the live A/B must show equal draws in both phases for any
   comparison that claims a gain.

## Tools

- `tools/ladder-scan.py` (added by this hunt): process-memory snapshot/diff/write-search utility used for
  everything above. `python -I ladder_scan.py snapshot <out> <label>`, `diff <a> <b>`,
  `writes <snap> <va_hex>`. It reads the emulator's process memory only.
- The player's patch plan was restored to the verified 1080p-only state after the experiments
  (`_Patches/PPSA26344.json`).
