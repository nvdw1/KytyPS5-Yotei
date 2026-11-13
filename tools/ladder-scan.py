# Ladder variable scanner v2 for KytyPS5-Yotei (Ghost of Yotei 2.002 ladder hunt).
# Usage:
#   python -I ladder_scan.py snapshot <out_file> <label>
#   python -I ladder_scan.py diff <file_a> <file_b>
#   python -I ladder_scan.py writes <snapshot> <candidate_va_hex>   # find in-memory RIP-relative writes
#
# Read-only: it only reads the emulator's process memory (guest memory is host-mapped).

import ctypes, ctypes.wintypes as wt, struct, sys, json, re

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
MEM_COMMIT = 0x1000
CHUNK = 32 * 1024 * 1024

k32 = ctypes.WinDLL("kernel32.dll", use_last_error=True)


class MBI64(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_uint64), ("AllocationBase", ctypes.c_uint64),
        ("AllocationProtect", wt.DWORD), ("__alignment1", wt.DWORD),
        ("RegionSize", ctypes.c_uint64), ("State", wt.DWORD),
        ("Protect", wt.DWORD), ("Type", wt.DWORD), ("__alignment2", wt.DWORD),
    ]


def find_pid(name="kyty_emulator.exe"):
    import subprocess
    out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {name}", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout
    for line in out.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if parts and parts[0].lower() == name.lower():
            return int(parts[1])
    return None


def committed_regions(handle):
    addr = 0
    mbi = MBI64()
    size = ctypes.sizeof(mbi)
    while addr < 0x7FFFFFFEFFFF:
        if not k32.VirtualQueryEx(handle, ctypes.c_void_p(addr), ctypes.byref(mbi), size):
            break
        if mbi.State == MEM_COMMIT and mbi.RegionSize >= 0x10000:
            yield mbi.BaseAddress, mbi.RegionSize
        addr = mbi.BaseAddress + mbi.RegionSize


def read(handle, address, size):
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t(0)
    if k32.ReadProcessMemory(handle, ctypes.c_void_p(address), buf, size, ctypes.byref(got)):
        return buf.raw[:got.value]
    return None


def find_images(handle):
    """Scan all committed memory for ELF64 images. Returns {va: {'phoff','phnum','segments':[...]}}."""
    images = {}
    ELF = b"\x7fELF"
    for base, size in committed_regions(handle):
        done = 0
        while done < size:
            n = min(CHUNK, size - done)
            data = read(handle, base + done, n)
            if data:
                pos = 0
                while True:
                    i = data.find(ELF, pos)
                    if i < 0:
                        break
                    va = base + done + i
                    if va not in images:
                        hdr = data[i:i + 64]
                        if len(hdr) >= 64 and hdr[4] == 2 and hdr[5] == 1:  # 64-bit LE
                            e_type, e_machine = struct.unpack_from("<HH", hdr, 16)
                            e_phoff, = struct.unpack_from("<Q", hdr, 32)
                            e_phentsize, e_phnum = struct.unpack_from("<HH", hdr, 42)
                            if e_machine == 0x3E and 1 <= e_phnum <= 32 and 0 < e_phoff < 0x1000:
                                ph = read(handle, va + e_phoff, e_phnum * e_phentsize)
                                segs = []
                                if ph and len(ph) == e_phnum * e_phentsize:
                                    for k in range(e_phnum):
                                        p = ph[k * e_phentsize:(k + 1) * e_phentsize]
                                        p_type, p_flags = struct.unpack_from("<II", p, 0)
                                        p_offset, p_vaddr, _, p_memsz = struct.unpack_from("<QQQQ", p, 8)
                                        if p_type == 1:  # PT_LOAD
                                            segs.append((p_vaddr, p_memsz, p_flags))
                                images[va] = {"type": e_type, "segs": segs}
                    pos = i + 4
            done += n
    return images


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    pid = find_pid()
    if pid is None:
        print("kyty_emulator.exe not running"); return 1
    handle = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not handle:
        print("cannot open process"); return 1
    if cmd == "snapshot":
        print("scanning for ELF images (this reads the whole committed space, ~15 GB)...", flush=True)
        images = find_images(handle)
        big = {va: info for va, info in images.items()
               if info["segs"] and max(v + m for v, m, f in info["segs"]) > 0x4000000}
        print(f"images found: {len(images)}, big (eboot-sized): {[hex(v) for v in big]}")
        label = sys.argv[3] if len(sys.argv) > 3 else ""
        out = {"label": label, "images": {f"{va:x}": info for va, info in big.items()}, "vars": {}}
        for va, info in big.items():
            for vaddr, memsz, flags in info["segs"]:
                if not (flags & 2):  # W flag only (data + bss)
                    continue
                done = 0
                while done < memsz:
                    n = min(CHUNK, memsz - done)
                    data = read(handle, va + vaddr + done, n)
                    if data:
                        for off in range(0, len(data) - 8, 8):
                            x = struct.unpack_from("<Q", data, off)[0]
                            if x <= 15:
                                out["vars"][f"{va + vaddr + done + off:x}"] = x
                    done += n
        with open(sys.argv[2], "w") as f:
            json.dump(out, f)
        print(f"snapshot '{label}': {len(out['vars'])} qword candidates (0..15) in writable segments")
        return 0
    if cmd == "diff":
        a = json.load(open(sys.argv[2])); b = json.load(open(sys.argv[3]))
        changed = [(k, a["vars"][k], b["vars"][k]) for k in a["vars"] if k in b["vars"] and a["vars"][k] != b["vars"][k]]
        changed.sort(key=lambda x: int(x[0], 16))
        for k, va, vb in changed:
            print(f"{k}: {va} -> {vb}")
        print(f"changed: {len(changed)}")
        return 0
    if cmd == "writes":
        snap = json.load(open(sys.argv[2]))
        target = int(sys.argv[3], 16)
        pid_img = None
        for va, info in snap["images"].items():
            for vaddr, memsz, flags in info["segs"]:
                if vaddr <= target - int(va, 16) < vaddr + memsz:
                    pid_img = (int(va, 16), info); break
            if pid_img: break
        if not pid_img:
            print("candidate not inside a known image"); return 1
        base, info = pid_img
        rva = target - base
        print(f"target rva = 0x{rva:x}")
        # scan the image's executable segments for RIP-relative writes: 48 c7 05 <disp32> <imm32>
        for vaddr, memsz, flags in info["segs"]:
            if not (flags & 1):  # X flag
                continue
            done = 0
            while done < memsz:
                n = min(CHUNK, memsz - done)
                data = read(handle, base + vaddr + done, n)
                if data:
                    for i in range(0, len(data) - 11):
                        if data[i] == 0x48 and data[i + 1] == 0xC7 and data[i + 2] == 0x05:
                            disp, = struct.unpack_from("<i", data, i + 3)
                            imm, = struct.unpack_from("<I", data, i + 7)
                            instr_va = base + vaddr + done + i
                            if instr_va + 11 + disp == target:
                                print(f"  mov qword [rip+0x{disp:x}], {imm}  at rva 0x{vaddr + done + i:x} "
                                      f"(bytes: {data[i:i + 11].hex()})")
                done += n
        return 0
    print("usage: snapshot <out> <label> | diff <a> <b> | writes <snap> <va_hex>"); return 1


if __name__ == "__main__":
    sys.exit(main())
