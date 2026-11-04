"""Fail-closed source/configuration and x64 object/link audit; never runs the binary.

This is an artifact gate for the declared MSVC 19.51 / GNU 13 Release profiles,
not a general x86 verifier or a runtime self-measurement. Unsupported codegen is
an audit failure, not evidence that the emitted program is numerically wrong.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import struct
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MSVC_NAMES = {
    "subtract": "??GVec3@pikapika@@QEBA?AU01@U01@@Z",
    "dot": "?dot@Vec3@pikapika@@QEBANU12@@Z",
    "length": "?length@Vec3@pikapika@@QEBANXZ",
}
GNU_NAMES = {
    "subtract": "_ZNK8pikapika4Vec3miES0_",
    "dot": "_ZNK8pikapika4Vec33dotES0_",
    "length": "_ZNK8pikapika4Vec36lengthEv",
}
SOURCE_PATHS = {
    "core/src/core.cpp", "core/include/pikapika/core.hpp",
    "core/src/dynamics.cpp", "core/include/pikapika/world_static_mesh_flight_guard.hpp",
    "core/src/world_static_mesh_flight_guard.cpp",
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def stamp(path):
    raw = path.read_bytes()
    return {"path": str(path.resolve()), "bytes": len(raw), "sha256": sha(raw)}


def strict_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate profile key: " + key)
            result[key] = value
        return result
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def write_json(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as out:
        json.dump(value, out, ensure_ascii=False, indent=2, allow_nan=False)
        out.write("\n")


class Runner:
    def __init__(self, directory):
        self.directory = directory
        self.commands = []

    def run(self, name, command):
        item = {"name": name, "argv": list(map(str, command)), "cwd": str(ROOT)}
        start = time.monotonic()
        try:
            p = subprocess.run(item["argv"], cwd=ROOT, capture_output=True, timeout=120)
            item.update(exitCode=p.returncode, elapsedSeconds=time.monotonic() - start)
            stdout, stderr = p.stdout, p.stderr
        except subprocess.TimeoutExpired as error:
            item.update(exitCode=None, elapsedSeconds=time.monotonic() - start,
                        exception=type(error).__name__ + ": " + str(error))
            stdout, stderr = error.stdout or b"", (error.stderr or b"") + str(error).encode("utf-8")
        except BaseException as error:
            item.update(exitCode=None, elapsedSeconds=time.monotonic() - start,
                        exception=type(error).__name__ + ": " + str(error))
            stdout, stderr = b"", str(error).encode("utf-8")
        for suffix, raw in (("stdout", stdout), ("stderr", stderr)):
            path = self.directory / (name + "." + suffix + ".txt")
            path.write_bytes(raw)
            item[suffix] = stamp(path)
        self.commands.append(item)
        write_json(self.directory / (name + ".command.json"), item)
        require(item["exitCode"] == 0, "Tool failed: " + name)
        # Dumpbin's instruction/symbol lines are ASCII even on localized systems.
        return stdout.decode("utf-8", errors="replace")


def check_profile(profile):
    require(type(profile.get("schema")) is int and profile["schema"] == 1, "Profile schema")
    require(type(profile.get("profile")) is int and profile["profile"] == 1,
            "Unsupported/unconfigured profile; no certified binding")
    require(profile.get("architecture") == "x64-sse2", "Architecture profile")
    require(profile.get("configuration") == "Release", "Release configuration required")
    require(re.fullmatch(r"[0-9a-f]{64}", profile.get("buildId", "")) is not None, "Build ID")
    require(profile.get("artifactAuditRequired") is True and isinstance(profile.get("scope"), str)
            and profile["scope"], "Artifact/configuration scope")
    compiler = profile["compiler"]
    family, version = compiler.get("id"), compiler.get("version", "")
    require(isinstance(version, str), "Compiler version type")
    require((family == "MSVC" and re.match(r"^19\.51(?:\.|$)", version)) or
            (family == "GNU" and re.match(r"^13(?:\.|$)", version)), "Unaudited compiler version")
    require(Path(compiler["path"]).is_file(), "Compiler file missing")
    sources = profile.get("sources")
    require(isinstance(sources, list) and len(sources) == 5, "Exactly five source/header stamps required")
    seen, checked = set(), []
    for entry in sources:
        relative = entry["path"].replace("\\", "/")
        require(relative in SOURCE_PATHS and relative not in seen, "Unexpected/duplicate source")
        seen.add(relative)
        path = ROOT / relative
        actual = stamp(path)
        require(actual["sha256"] == entry["sha256"], "Current source hash mismatch: " + relative)
        flags = entry["flags"]
        require(isinstance(flags, list) and all(isinstance(x, str) for x in flags), "Flags type")
        if relative.endswith(".hpp"):
            require(not flags, "Header flags must be empty")
        else:
            lowered = [x.lower() for x in flags]
            require(not any(re.search(r"(?:/gl$|/ltcg|/fp:fast|-flto(?:=|$)|-ffast-math|-ofast|"
                                      r"-funsafe-math|-fassociative-math|-mfpmath=387|-ffp-contract=fast)",
                                      x) for x in lowered), "Unsafe/LTO flag")
            if family == "MSVC":
                require("/fp:strict" in lowered, "Missing /fp:strict: " + relative)
            else:
                mandatory = {"-fno-fast-math", "-ffp-contract=off", "-frounding-math",
                             "-fexcess-precision=standard", "-mfpmath=sse", "-msse2", "-fno-lto"}
                require(mandatory <= set(lowered), "Missing GNU strict flags: " + relative)
        checked.append({**actual, "flags": flags})
    return family, checked


def cstring(raw, offset):
    end = raw.find(b"\0", offset)
    require(end >= offset, "Unterminated object string")
    return raw[offset:end].decode("ascii")


class Coff:
    def __init__(self, raw):
        require(len(raw) >= 20, "Short COFF")
        machine, count, _, symoff, nsyms, optional, _ = struct.unpack_from("<HHIIIHH", raw)
        require(machine == 0x8664 and optional == 0 and 0 < count < 65536, "Expected AMD64 COFF")
        self.raw, self.symbols, self.sections = raw, {}, []
        strings = symoff + 18 * nsyms
        require(strings + 4 <= len(raw), "COFF symbol strings")
        for i in range(count):
            base = 20 + 40 * i
            require(base + 40 <= len(raw), "COFF section header")
            _, _, _, size, offset, reloc, _, nreloc, _, characteristics = struct.unpack_from("<8sIIIIIIHHI", raw, base)
            require(offset + size <= len(raw), "COFF section extent")
            self.sections.append({"offset": offset, "size": size, "reloc": reloc,
                                  "nreloc": nreloc, "flags": characteristics})
        i = 0
        while i < nsyms:
            base = symoff + 18 * i
            require(base + 18 <= len(raw), "COFF symbol extent")
            name8, value, section, typ, storage, aux = struct.unpack_from("<8sIhHBB", raw, base)
            name = cstring(raw, strings + struct.unpack_from("<I", name8, 4)[0]) if name8[:4] == b"\0" * 4 else name8.rstrip(b"\0").decode("ascii")
            if storage == 2 and section > 0 and typ & 0x20:
                require(name not in self.symbols, "Duplicate COFF function: " + name)
                self.symbols[name] = (section - 1, value)
            i += 1 + aux

    def body(self, name):
        require(name in self.symbols, "Missing COFF function: " + name)
        section, value = self.symbols[name]
        info = self.sections[section]
        end = min([v for s, v in self.symbols.values() if s == section and v > value] + [info["size"]])
        require(info["flags"] & 0x20, "Function is not in a code section")
        return self.raw[info["offset"] + value:info["offset"] + end], value, info


class PE:
    def __init__(self, raw):
        require(raw[:2] == b"MZ" and len(raw) > 64, "Expected PE image")
        p = struct.unpack_from("<I", raw, 60)[0]
        require(raw[p:p + 4] == b"PE\0\0", "PE signature")
        machine, count, _, _, _, optional, _ = struct.unpack_from("<HHIIIHH", raw, p + 4)
        require(machine == 0x8664 and struct.unpack_from("<H", raw, p + 24)[0] == 0x20b, "Expected PE32+ AMD64")
        self.raw, self.imagebase, self.sections = raw, struct.unpack_from("<Q", raw, p + 48)[0], []
        for i in range(count):
            _, virtualsize, rva, size, offset, _, _, _, _, flags = struct.unpack_from("<8sIIIIIIHHI", raw, p + 24 + optional + i * 40)
            self.sections.append((rva, max(virtualsize, size), offset, size, flags))

    def at(self, va, size):
        rva = va - self.imagebase
        for base, extent, offset, rawsize, flags in self.sections:
            if base <= rva and rva + size <= base + min(extent, rawsize):
                require(flags & 0x20, "Mapped function not executable code")
                return self.raw[offset + rva - base:offset + rva - base + size]
        raise ValueError("Function VA outside image code")


class Elf:
    def __init__(self, raw):
        require(raw[:6] == b"\x7fELF\x02\x01", "Expected ELF64 little endian")
        require(struct.unpack_from("<H", raw, 18)[0] == 62, "Expected ELF x86-64")
        self.raw, self.kind, self.sections, self.symbols = raw, struct.unpack_from("<H", raw, 16)[0], [], {}
        self.symbol_bindings = {}
        self.symbol_diagnostics = {"localFunctionEntries": 0, "localNameCollisions": 0,
                                   "localCollisionExamples": [], "otherBindingFunctionEntries": 0}
        local_names = {}
        offset = struct.unpack_from("<Q", raw, 40)[0]
        stride, count = struct.unpack_from("<HH", raw, 58)
        require(stride == 64 and count > 0, "ELF section table")
        for i in range(count):
            name, typ, flags, address, start, size, link, _, _, entsize = struct.unpack_from("<IIQQQQIIQQ", raw, offset + i * stride)
            self.sections.append({"type": typ, "flags": flags, "address": address,
                                  "offset": start, "size": size, "link": link, "entsize": entsize})
        for section in self.sections:
            if section["type"] != 2:
                continue
            require(section["entsize"] == 24, "ELF symbol size")
            strings = self.sections[section["link"]]["offset"]
            for off in range(section["offset"], section["offset"] + section["size"], 24):
                name, info, _, index, value, size = struct.unpack_from("<IBBHQQ", raw, off)
                if info & 15 == 2 and 0 < index < len(self.sections) and size:
                    key = cstring(raw, strings + name)
                    binding = info >> 4
                    if binding == 0:
                        # gABI 5.2 permits identically named STB_LOCAL symbols in
                        # different input files. They cannot identify the external
                        # Vec3/bridge/contact targets checked by this auditor.
                        self.symbol_diagnostics["localFunctionEntries"] += 1
                        if key in local_names:
                            self.symbol_diagnostics["localNameCollisions"] += 1
                            if len(self.symbol_diagnostics["localCollisionExamples"]) < 8:
                                self.symbol_diagnostics["localCollisionExamples"].append(
                                    {"name": key, "first": local_names[key], "next": (index, value, size)})
                        else:
                            local_names[key] = (index, value, size)
                        continue
                    if binding not in (1, 2):
                        self.symbol_diagnostics["otherBindingFunctionEntries"] += 1
                        continue
                    require(key not in self.symbols or
                            (self.symbols[key] == (index, value, size) and self.symbol_bindings[key] == binding),
                            "ELF duplicate function: " + key + " (external binding conflict)")
                    self.symbols[key] = (index, value, size)
                    self.symbol_bindings[key] = binding

    def body(self, name):
        require(name in self.symbols, "Missing ELF function: " + name)
        index, value, size = self.symbols[name]
        s = self.sections[index]
        require(s["flags"] & 4, "ELF function not executable")
        start = s["offset"] + value - (s["address"] if self.kind != 1 else 0)
        require(start >= 0 and start + size <= len(self.raw), "ELF function extent")
        return self.raw[start:start + size], value, s


def instructions(text):
    result = []
    for line in text.splitlines():
        match = re.match(r"^\s*([0-9a-fA-F]+):\s+((?:[0-9a-fA-F]{2}\s+)+)([a-zA-Z][\w.]*)\s*(.*?)\s*$", line)
        if match:
            address, code, mnemonic, operands = match.groups()
            result.append((int(address, 16), bytes.fromhex(code), mnemonic.lower(), operands.strip()))
    return result


def functions(text):
    result, current = {}, None
    for line in text.splitlines():
        gnu = re.match(r"^[0-9a-fA-F]+ <(.+)>:$", line.strip())
        msvc = re.match(r"^(\S+)(?:\s+\(.*\))?:$", line)
        if gnu or msvc:
            current = (gnu or msvc).group(1)
            result.setdefault(current, [])
        elif current:
            result[current].extend(instructions(line))
    return result


def trim_function(items):
    require(items, "No disassembled function instructions")
    result = []
    for item in items:
        result.append(item)
        if item[2] in ("ret", "retq"):
            break
    require(result[-1][2] in ("ret", "retq"), "No straight-line return")
    for a, b in zip(result, result[1:]):
        require(a[0] + len(a[1]) == b[0], "Instruction bytes not contiguous")
    return result


def number(text):
    text = text.strip().lower()
    if text.endswith("h"):
        return int(text[:-1], 16)
    return int(text, 0) if text.startswith("0x") else int(text, 10)


def expression(op, a, b=None):
    if b is None:
        return (op, a)
    if op in ("mul", "add"):
        a, b = sorted((a, b), key=repr)
    return (op, a, b)


ZERO = ("zero",)


def dot(a, b):
    products = [expression("mul", x, y) for x, y in zip(a, b)]
    return expression("add", expression("add", products[0], products[1]), products[2])


class Dataflow:
    """Small explicit SSE2/VEX interpreter; unsupported instructions fail closed."""
    def __init__(self, family, kind, dot_targets):
        self.family, self.kind, self.dot_targets = family, kind, dot_targets
        self.reg, self.xmm, self.memory, self.stores = {}, {}, {}, {}
        a = [("a", i) for i in range(3)]
        b = [("b", i) for i in range(3)]
        for i in range(3):
            self.memory[("a", i * 8)] = a[i]
            self.memory[("b", i * 8)] = b[i]
        self.reg["rsp"] = ("stack", 0)
        if family == "MSVC":
            self.reg.update(rcx=("a", 0), rdx=("out" if kind == "subtract" else "b", 0), r8=("b", 0))
        else:
            self.reg.update(rdi=("out" if kind == "subtract" else "a", 0), rsi=("a", 0))
            if kind != "length":
                for i in range(3):
                    self.memory[("stack", 8 + i * 8)] = b[i]
        self.sqrt_count, self.dot_calls, self.equations = 0, 0, []

    def address(self, operand):
        match = re.search(r"\[([^\]]+)\]", operand.lower())
        require(match is not None, "Unsupported memory operand: " + operand)
        text = match.group(1).replace(" ", "")
        match = re.fullmatch(r"([a-z][a-z0-9]*)(?:([+-])((?:0x)?[0-9a-f]+h?))?", text)
        require(match is not None and match[1] in self.reg, "Unknown pointer: " + text)
        base, offset = self.reg[match[1]]
        if match[2]:
            offset += number(match[3]) * (1 if match[2] == "+" else -1)
        return base, offset

    def vector(self, operand, packed=False):
        operand = operand.strip().lower()
        if operand.startswith("xmm"):
            require(operand in self.xmm, "Uninitialized XMM register: " + operand)
            return self.xmm[operand]
        base, offset = self.address(operand)
        count = 2 if packed else 1
        values = []
        for i in range(count):
            require((base, offset + 8 * i) in self.memory, "Uninitialized/non-input memory")
            values.append(self.memory[(base, offset + 8 * i)])
        return values + ([ZERO] if not packed else [])

    def store(self, operand, values, packed=False):
        base, offset = self.address(operand)
        for i in range(2 if packed else 1):
            self.memory[(base, offset + i * 8)] = values[i]
            if base == "out":
                self.stores[offset + i * 8] = values[i]

    def execute(self, items):
        for _, _, op, raw in items:
            operands = [x.strip() for x in raw.split(";", 1)[0].split(",") if x.strip()]
            require(not re.search(r"(?:fma|fmadd|fmsub|fnm|rsqrt|^f(?:ld|st|add|mul|sqrt|sub|div))", op), "Forbidden fused/x87/approximate instruction")
            if op in ("ret", "retq", "nop", "nopl", "nopw", "endbr64"):
                continue
            if op in ("push", "pop"):
                base, off = self.reg["rsp"]
                if op == "push":
                    self.memory[(base, off - 8)] = ("saved-pointer", self.reg.get(operands[0].lower()))
                    self.reg["rsp"] = base, off - 8
                else:
                    saved = self.memory.get((base, off))
                    self.reg.pop(operands[0].lower(), None)
                    if saved and saved[0] == "saved-pointer" and saved[1] is not None:
                        self.reg[operands[0].lower()] = saved[1]
                    self.reg["rsp"] = base, off + 8
                continue
            if op in ("add", "sub") and operands[0].lower() == "rsp":
                base, off = self.reg["rsp"]
                self.reg["rsp"] = base, off + number(operands[1]) * (1 if op == "add" else -1)
                continue
            if op in ("mov", "lea"):
                dest, src = map(str.lower, operands)
                if op == "lea":
                    self.reg[dest] = self.address(src)
                elif src in self.reg and "[" not in dest:
                    self.reg[dest] = self.reg[src]
                elif "[" in dest and src in self.reg:
                    address = self.address(dest)
                    require(address[0] == "stack", "Integer write to non-stack input/output")
                    self.memory[address] = ("saved-pointer", self.reg[src])
                elif "[" in src:
                    # Restoring a callee-save pointer cannot influence a proven output.
                    self.reg.pop(dest, None)
                else:
                    raise ValueError("Unsupported integer move: " + raw)
                continue
            if op in ("call", "callq"):
                require(self.kind == "length", "Unexpected call inside core leaf")
                require(any(name in raw for name in self.dot_targets), "Length calls unknown/non-dot target: " + raw)
                if self.family == "MSVC":
                    ap, bp = self.reg.get("rcx"), self.reg.get("rdx")
                    require(ap and bp, "Missing dot call pointer arguments")
                    av = [self.memory.get((ap[0], ap[1] + 8 * i)) for i in range(3)]
                    bv = [self.memory.get((bp[0], bp[1] + 8 * i)) for i in range(3)]
                else:
                    ap, sp = self.reg.get("rdi"), self.reg["rsp"]
                    require(ap, "Missing dot this pointer")
                    av = [self.memory.get((ap[0], ap[1] + 8 * i)) for i in range(3)]
                    bv = [self.memory.get((sp[0], sp[1] + 8 * i)) for i in range(3)]
                require(None not in av + bv, "Unknown dot call inputs")
                self.xmm.clear()  # Do not reuse unproven caller-save lane values.
                self.xmm["xmm0"] = [dot(av, bv), ZERO]
                self.dot_calls += 1
                continue
            if op in ("xorps", "xorpd", "pxor", "vxorps", "vxorpd", "vpxor"):
                require(len(set(map(str.lower, operands))) == 1 or
                        (len(operands) == 3 and operands[1] == operands[2]), "Nonzero vector xor")
                self.xmm[operands[0].lower()] = [ZERO, ZERO]
                continue
            vex = op.startswith("v")
            baseop = op[1:] if vex else op
            if baseop in ("movsd", "movups", "movupd", "movaps", "movapd", "movdqu", "movdqa", "movq"):
                packed = baseop not in ("movsd", "movq")
                dest, src = operands[0].lower(), operands[-1]
                value = self.vector(src, packed)[:]
                if "[" in dest:
                    self.store(dest, value, packed)
                else:
                    if not packed and len(operands) == 3:
                        value[1] = self.vector(operands[1])[1]
                    elif not packed and src.strip().lower().startswith("xmm"):
                        value[1] = self.xmm.get(dest, [None, ("unknown-high", dest)])[1]
                    self.xmm[dest] = value[:]
                continue
            if baseop in ("mulsd", "addsd", "subsd", "mulpd", "addpd", "subpd"):
                packed = baseop.endswith("pd")
                dest = operands[0].lower()
                first = operands[1] if vex else dest
                second = operands[2] if vex else operands[1]
                a, b = self.vector(first, packed), self.vector(second, packed)
                operation = {"mul": "mul", "add": "add", "sub": "sub"}[baseop[:3]]
                value = a[:]
                for i in range(2 if packed else 1):
                    value[i] = expression(operation, a[i], b[i])
                self.xmm[dest] = value
                self.equations.append({"instruction": op + " " + raw, "value": repr(value)})
                continue
            if baseop == "sqrtsd":
                dest, src = operands[0].lower(), operands[-1]
                value = self.vector(src)
                self.xmm[dest] = [expression("sqrt", value[0]), value[1]]
                self.sqrt_count += 1
                continue
            if baseop in ("unpckhpd", "unpcklpd"):
                dest = operands[0].lower()
                a = self.vector(operands[1] if vex else dest, True)
                b = self.vector(operands[-1], True)
                i = 1 if baseop == "unpckhpd" else 0
                self.xmm[dest] = [a[i], b[i]]
                continue
            raise ValueError("Unsupported instruction in audited graph: " + op + " " + raw)
        a, b = [("a", i) for i in range(3)], [("b", i) for i in range(3)]
        if self.kind == "subtract":
            expected = {8 * i: expression("sub", a[i], b[i]) for i in range(3)}
            require(self.stores == expected and self.sqrt_count == 0 and self.dot_calls == 0,
                    "Three independent rounded coordinate subtractions not proven")
            output = self.stores
        else:
            expected = dot(a, b) if self.kind == "dot" else expression("sqrt", dot(a, a))
            require(self.xmm.get("xmm0", [None])[0] == expected, "Wrong product/add association or sqrt input/output")
            require(self.sqrt_count == (1 if self.kind == "length" else 0), "Hardware sqrt count")
            output = expected
        return {"kind": self.kind, "sqrtInstructions": self.sqrt_count, "directDotCalls": self.dot_calls,
                "expression": repr(output), "equations": self.equations}


def map_symbols(text, image):
    result = {}
    for line in text.splitlines():
        if re.match(r"\s*0000:", line):
            continue  # Discarded/absolute COMDAT records have no executable RVA.
        match = re.match(r"\s*[0-9A-Fa-f]{4}:[0-9A-Fa-f]{8,16}\s+(\S+)\s+([0-9A-Fa-f]{8,16})\s+(?:f\s+)?(?:i\s+)?(.+?)\s*$", line)
        if match:
            if match[1].startswith((".", "$")):
                continue  # Repeated linker section/pseudo-labels are not functions.
            # MSVC also emits discarded COMDATs with wrapped section offsets
            # (e.g. 0001:fffff000) and VA equal to ImageBase. Keep only entries
            # that actually map to a byte in an executable PE section.
            try:
                image.at(int(match[2], 16), 1)
            except ValueError:
                continue
            require(match[1] not in result, "Duplicate map symbol")
            result[match[1]] = {"address": int(match[2], 16), "owner": match[3]}
    return result


def source_body_check(sources):
    # The declared file hash is checked, and the exact caller AST is also pinned
    # in this audit. This does not replace the compiler and instruction gates.
    text = (ROOT / "core/src/dynamics.cpp").read_text(encoding="utf-8")
    compact = re.sub(r"\s+", "", text)
    for literal in (
        "constdoubledistance=plane.normal.dot(body.position)-plane.offset;",
        "if(distance<=body.radius+settings.contact_margin)",
        "constautodelta=other.position-body.position;constdoubledistance=delta.length(),radii=body.radius+other.radius;",
        "if(distance<=radii+settings.contact_margin)",
    ):
        require(literal in compact, "Changed dynamics predicate AST; needs a new audit contract")


def command_provenance(profile, objpath, binary, build_directory, compdb_path, output):
    """Capture actual build-system compiler records, separately from requested flags.

    The records are not a cryptographic compiler attestation. Their identities,
    the captured build receipts and independently read machine artifacts jointly
    form the gate; neither a profile JSON nor flags alone supplies the proof.
    """
    family = profile["compiler"]["id"]
    required = ["core/src/core.cpp", "core/src/dynamics.cpp", "core/src/world_static_mesh_flight_guard.cpp"]
    files, rows = [], []
    def capture(path, label):
        require(path.is_file(), "Actual compilation evidence missing: " + str(path))
        item = stamp(path)
        destination = output / label
        destination.write_bytes(path.read_bytes())
        require(stamp(destination)["sha256"] == item["sha256"], "Command evidence copy")
        files.append(item)
        return path.read_bytes()
    if family == "MSVC":
        project = build_directory / "pikapika_core.vcxproj"
        raw = capture(project, "compiler-project.vcxproj.txt")
        xml = ET.fromstring(raw)
        ns = {"m": "http://schemas.microsoft.com/developer/msbuild/2003"}
        entries = xml.findall(".//m:ClCompile", ns)
        tlogs = list((objpath.parent).rglob("CL.command.1.tlog"))
        require(len(tlogs) == 1, "Unique actual core compiler tlog required")
        raw = capture(tlogs[0], "compiler-command.tlog.txt")
        lines, records = raw.decode("utf-16").splitlines(), {}
        for i, line in enumerate(lines):
            if not line.startswith("^"):
                continue
            keys = line[1:].split("|")
            stop = next((j for j in range(i + 1, len(lines)) if lines[j].startswith("^")), len(lines))
            command = " ".join(lines[i + 1:stop]).strip()
            for key in keys:
                key = key.replace("/", "\\").casefold()
                require(key not in records, "Duplicate actual source compile record")
                records[key] = command
        for relative in required:
            source = ROOT / relative
            key = str(source.resolve()).replace("/", "\\").casefold()
            require(key in records, "Missing actual compiler command: " + relative)
            command = records[key]
            flags = re.findall(r"(?:^|\s)/fp:([a-z]+)(?=\s|$)", command, re.I)
            require(flags and all(x.lower() == "strict" for x in flags), "Actual command lacks exclusive strict FP")
            require(not re.search(r"(?:^|\s)/(?:GL|LTCG)(?=\s|:|$)", command, re.I), "Actual command enables GL/LTO")
            matches = [e for e in entries if e.get("Include", "").replace("/", "\\").casefold() == key]
            require(len(matches) == 1, "Unique source project item")
            strict = [x.text for x in matches[0].findall("m:FloatingPointModel", ns)
                      if "Release|x64" in x.get("Condition", "")]
            require(strict == ["Strict"], "Actual Release project FP mode")
            if relative != "core/src/dynamics.cpp":
                require("PIKAPIKA_WORLD_FLIGHT_AUDITED_PROFILE=1" in command and profile["buildId"] in command,
                        "Actual source command lacks profile/identity definitions")
            rows.append({"source": relative, "command": command, "strictFP": True, "noGL": True})
        target_directory = build_directory / (binary.stem + ".dir") / "Release"
        links = list(target_directory.rglob("link.command.1.tlog"))
        require(len(links) == 1, "Unique actual binary link tlog required")
        link = capture(links[0], "link-command.tlog.txt").decode("utf-16")
        require(not re.search(r"(?:^|\s)/(?:LTCG|GL)(?=\s|:|$)", link, re.I), "Actual link enables LTO")
        require(binary.name.casefold() in link.casefold(), "Link record binary mismatch")
        return {"scope": "Actual MSBuild project and compiler/link tlogs, plus separate artifact graph/identity gates; no compiler attestation claim",
                "files": files, "sourceCommands": rows, "noLinkTimeCodeGeneration": True}
    compdb = compdb_path or build_directory / "compile_commands.json"
    raw = capture(compdb, "compile_commands.json")
    entries = json.loads(raw)
    require(isinstance(entries, list), "Compile database type")
    for relative in required:
        source = (ROOT / relative).resolve()
        selected = []
        for entry in entries:
            path = Path(entry["file"])
            if not path.is_absolute():
                path = Path(entry["directory"]) / path
            if path.resolve() == source:
                selected.append(entry)
        require(len(selected) == 1, "Unique actual GNU source command: " + relative)
        entry = selected[0]
        argv = entry.get("arguments") or shlex.split(entry["command"])
        require(isinstance(argv, list) and all(isinstance(x, str) for x in argv), "Compile argv type")
        require(Path(argv[0]).resolve() == Path(profile["compiler"]["path"]).resolve(), "Compile compiler mismatch")
        lower = [x.lower() for x in argv]
        mandatory = {"-fno-fast-math", "-ffp-contract=off", "-frounding-math", "-fexcess-precision=standard",
                     "-mfpmath=sse", "-msse2", "-fno-lto"}
        require(mandatory <= set(lower), "Actual GNU strict flags")
        require(not any(re.match(r"(?:-flto(?:=|$)|-ffast-math$|-ofast$|-funsafe-math|-fassociative-math|-ffp-contract=fast$)", x)
                        for x in lower), "Actual GNU unsafe/LTO flag")
        if relative != "core/src/dynamics.cpp":
            require("-DPIKAPIKA_WORLD_FLIGHT_AUDITED_PROFILE=1" in argv and any(profile["buildId"] in x for x in argv),
                    "Actual GNU profile definitions")
        if relative == "core/src/core.cpp":
            require("-o" in argv and argv.index("-o") + 1 < len(argv), "Actual GNU object output")
            out = Path(argv[argv.index("-o") + 1])
            if not out.is_absolute():
                out = Path(entry["directory"]) / out
            require(out.resolve() == objpath.resolve(), "Actual GNU core object path")
        rows.append({"source": relative, "argv": argv, "directory": entry["directory"], "strictFP": True, "noLTO": True})
    links = list(build_directory.rglob("link.txt"))
    selected = []
    for path in links:
        text = path.read_text(encoding="utf-8")
        if binary.name in text and (binary.stem + ".dir") in str(path):
            selected.append(path)
    require(len(selected) == 1, "GNU actual link.txt required (Makefile generator); no inferred link flags")
    text = capture(selected[0], "link-command.txt").decode("utf-8")
    require(not any(re.match(r"-flto(?:=|$)", x) for x in shlex.split(text)), "GNU link LTO")
    return {"scope": "Actual CMake compile database and target link command plus artifact graph; no compiler attestation claim",
            "files": files, "sourceCommands": rows, "noLinkTimeCodeGeneration": True}


def dataflow_controls(family, original, targets):
    """Mutate decoded instruction records only; never patch an actual artifact."""
    rejected = []
    def check(label, kind, items):
        try:
            Dataflow(family, kind, targets).execute(items)
        except ValueError:
            rejected.append(label)
        else:
            raise ValueError("Auditor negative control accepted: " + label)
    length = original["length"]
    root_index = next((i for i, x in enumerate(length) if x[2] in ("sqrtsd", "vsqrtsd")), None)
    require(root_index is not None, "No root for controls")
    for label, mnemonic in (("approximate-root", "rsqrtss"), ("fused-root", "vfmadd132sd"),
                            ("missing-root", "movsd"), ("x87-root", "fsqrt"),
                            ("libm-call", "call")):
        items = length[:]
        a, code, _, operands = items[root_index]
        items[root_index] = a, code, mnemonic, ("sqrt" if mnemonic == "call" else operands)
        check(label, "length", items)
    dots = original["dot"]
    adds = [i for i, x in enumerate(dots) if x[2] in ("addsd", "vaddsd")]
    if len(adds) == 2 and all(dots[i][2] == "addsd" for i in adds):
        # Exchange the two right add operands: grouping with z first is different.
        items = dots[:]
        first, second = adds
        x, y = items[first], items[second]
        xops, yops = x[3].split(","), y[3].split(",")
        items[first] = x[:3] + (xops[0] + "," + yops[1],)
        items[second] = y[:3] + (yops[0] + "," + xops[1],)
        check("reassociated-dot", "dot", items)
    for kind in ("subtract", "dot"):
        items = original[kind][:]
        i = next(i for i, x in enumerate(items) if x[2].lstrip("v") in ("subsd", "subpd", "mulsd", "mulpd"))
        a, code, _, operands = items[i]
        items[i] = a, code, "addsd", operands
        check("wrong-" + kind + "-operation", kind, items)
    return {"kind": "Synthetic decoded-instruction mutations; not altered machine artifacts or C++ fault injection",
            "rejectedControls": len(rejected), "names": rejected}


def audit_msvc(profile, objpath, binary, mappath, runner):
    require(mappath and mappath.is_file(), "MSVC linker map required")
    tool = Path(profile["compiler"]["dumpbin"])
    require(tool.is_file(), "dumpbin missing")
    runner.run("tool-headers", [tool, "/nologo", "/headers", objpath])
    runner.run("object-symbols", [tool, "/nologo", "/symbols", objpath])
    disasm = runner.run("object-disassembly", [tool, "/nologo", "/disasm:bytes", objpath])
    coff, pe = Coff(objpath.read_bytes()), PE(binary.read_bytes())
    symbols = map_symbols(mappath.read_text(encoding="utf-8", errors="strict"), pe)
    decoded, proofs, original = functions(disasm), [], {}
    require(profile["buildId"].encode("ascii") in objpath.read_bytes(), "Object lacks profile identity")
    require(profile["buildId"].encode("ascii") in binary.read_bytes(), "Binary lacks profile identity")
    for kind, name in MSVC_NAMES.items():
        require(name in symbols and re.search(r"(?:^|[:\\/])core\.obj$", symbols[name]["owner"], re.I), "Map core.obj linkage: " + kind)
        body, offset, section = coff.body(name)
        items = trim_function(decoded.get(name, []))
        original[kind] = items
        require(items[0][0] == offset, "Object symbol/disassembly offset")
        size = items[-1][0] + len(items[-1][1]) - offset
        code = b"".join(x[1] for x in items)
        require(body[:size] == code, "Disassembler/object bytes disagree")
        va = symbols[name]["address"]
        linked = runner.run("linked-" + kind, [tool, "/nologo", "/disasm:bytes", f"/range:0x{va:x},0x{va + size - 1:x}", binary])
        linked_items = trim_function(instructions(linked))
        require(linked_items[0][0] == va, "Linked symbol address/disassembly")
        require(len(linked_items) == len(items), "Object/link instruction count")
        require(b"".join(x[1] for x in linked_items) == pe.at(va, size), "Linked disassembler/image bytes disagree")
        # Ordinary leaf code has no relocations. A length->dot call is allowed,
        # but both emitted rel32 targets must bind to the audited dot body.
        mutable = bytearray(code)
        linked_code = bytearray(pe.at(va, size))
        for source_item, actual in zip(items, linked_items):
            require(source_item[2] == actual[2] and len(source_item[1]) == len(actual[1]), "Object/link instruction shape changed")
            if source_item[2] == "call":
                require(kind == "length" and source_item[1][:1] == b"\xe8" and len(source_item[1]) == 5, "Unexpected relocated call")
                target = actual[0] + 5 + struct.unpack_from("<i", actual[1], 1)[0]
                require(target == symbols[MSVC_NAMES["dot"]]["address"], "Length call does not bind audited dot")
                start = source_item[0] - offset + 1
                mutable[start:start + 4] = linked_code[start:start + 4]
        require(mutable == linked_code, "Object core body differs from linked function bytes")
        proof = Dataflow("MSVC", kind, [MSVC_NAMES["dot"], f"{symbols[MSVC_NAMES['dot']]['address']:X}", f"{symbols[MSVC_NAMES['dot']]['address']:x}"]).execute(items)
        proofs.append({**proof, "symbol": name, "map": symbols[name], "objectCodeBytes": size,
                       "objectCodeSha256": sha(code), "linkedCodeSha256": sha(bytes(linked_code)),
                       "relocationAdjustedIdentity": mutable == linked_code})
    bridges = [name for name in symbols if "world_predicate_binding_" in name and "@detail@pikapika@@" in name]
    require(len(bridges) == 2 and all(name in coff.symbols and re.search(r"(?:^|[:\\/])core\.obj$", symbols[name]["owner"], re.I) for name in bridges), "Both private bridges must link from actual core.obj")
    callers = [name for name in symbols if name.startswith("?solve_contacts_at_current_state@detail@dynamics@pikapika@@")]
    require(len(callers) == 1, "Unique actual dynamics contact routine required")
    name = callers[0]
    require(re.search(r"(?:^|[:\\/])dynamics\.obj$", symbols[name]["owner"], re.I), "Contact routine map ownership")
    va = symbols[name]["address"]
    end = min([entry["address"] for entry in symbols.values() if entry["address"] > va] + [va + 262144])
    require(0 < end - va <= 262144, "Bounded contact disassembly extent")
    caller = runner.run("linked-dynamics-predicates", [tool, "/nologo", "/disasm:bytes", f"/range:0x{va:x},0x{end - 1:x}", binary])
    calls = set()
    for address, code, mnemonic, operands in instructions(caller):
        require(not re.search(r"(?:fma|fmadd|fmsub|fnm|rsqrt|^f(?:ld|st|add|mul|sqrt|sub|div))", mnemonic), "Fused/x87 contact routine")
        if mnemonic == "call" and len(code) == 5 and code[0] == 0xe8:
            calls.add(address + 5 + struct.unpack_from("<i", code, 1)[0])
    require(all(symbols[name]["address"] in calls for name in MSVC_NAMES.values()), "Contact routine lacks direct audited subtraction/dot/length calls")
    controls = dataflow_controls("MSVC", original, [MSVC_NAMES["dot"]])
    return {"functions": proofs, "bridges": {name: symbols[name] for name in bridges},
            "caller": {"symbol": name, "map": symbols[name], "directAuditedCalls": True},
            "dataflowControls": controls,
            "tool": stamp(tool)}


def audit_gnu(profile, objpath, binary, runner):
    tool = Path(profile["compiler"]["objdump"])
    require(tool.is_file(), "objdump missing")
    version = runner.run("tool-version", [tool, "--version"])
    require("GNU objdump" in version, "GNU objdump required")
    runner.run("object-symbols", [tool, "-t", objpath])
    od = runner.run("object-disassembly", [tool, "-drw", "-Mintel", "--insn-width=16", objpath])
    bd = runner.run("linked-disassembly", [tool, "-dw", "-Mintel", "--insn-width=16", binary])
    runner.run("object-demangled-disassembly", [tool, "-drwC", "-Mintel", "--insn-width=16", objpath])
    obj, image, decoded, linked = Elf(objpath.read_bytes()), Elf(binary.read_bytes()), functions(od), functions(bd)
    require(obj.kind == 1 and image.kind in (2, 3), "ELF relocatable/image kinds")
    require(profile["buildId"].encode("ascii") in obj.raw and profile["buildId"].encode("ascii") in image.raw, "ELF profile identity missing")
    proofs = []
    for kind, name in GNU_NAMES.items():
        body, value, _ = obj.body(name)
        actual, va, _ = image.body(name)
        items, linked_items = trim_function(decoded.get(name, [])), trim_function(linked.get(name, []))
        size = items[-1][0] + len(items[-1][1]) - items[0][0]
        code = b"".join(x[1] for x in items)
        require(code == body[:size], "GNU object/disassembly bytes disagree")
        actual_code = b"".join(x[1] for x in linked_items)
        require(len(items) == len(linked_items), "GNU object/link instruction count")
        require(actual_code == actual[:len(actual_code)] and len(actual_code) == size, "GNU linked extent/bytes")
        patched = bytearray(code)
        for a, b in zip(items, linked_items):
            require(a[2] == b[2] and len(a[1]) == len(b[1]), "GNU object/link instruction shape")
            if a[2] in ("call", "callq"):
                require(kind == "length" and a[1][0] == 0xe8 and len(a[1]) == 5, "Unexpected GNU call")
                target = b[0] + 5 + struct.unpack_from("<i", b[1], 1)[0]
                require(target == image.symbols[GNU_NAMES["dot"]][1], "GNU dot call linkage")
                off = a[0] - items[0][0] + 1
                patched[off:off + 4] = b[1][1:]
        require(bytes(patched) == actual_code, "GNU object/link function identity")
        # Object call relocations are printed on the same line by -w. Analyze
        # the linked spelling instead so each call has its actual named target.
        proof = Dataflow("GNU", kind, [GNU_NAMES["dot"]]).execute(linked_items)
        proofs.append({**proof, "symbol": name, "objectCodeBytes": size,
                       "objectCodeSha256": sha(code), "linkedCodeSha256": sha(actual_code),
                       "relocationAdjustedIdentity": True})
    bridges = [name for name in image.symbols if "world_predicate_binding_" in name]
    require(len(bridges) == 2 and all(name in obj.symbols for name in bridges), "GNU private core bridge linkage")
    callers = [name for name in image.symbols if name.startswith("_ZN") and "solve_contacts_at_current_state" in name and not name.endswith(".cold")]
    require(len(callers) == 1, "Unique GNU dynamics contact routine")
    calls = set()
    for address, code, op, operands in linked.get(callers[0], []):
        require(not re.search(r"(?:fma|fmadd|fmsub|fnm|rsqrt|^f(?:ld|st|add|mul|sqrt|sub|div))", op), "GNU fused/x87 caller")
        if op in ("call", "callq") and len(code) == 5 and code[0] == 0xe8:
            calls.add(address + 5 + struct.unpack_from("<i", code, 1)[0])
    require(all(image.symbols[name][1] in calls for name in GNU_NAMES.values()), "GNU contact routine audited calls")
    return {"functions": proofs, "bridges": bridges, "caller": callers[0], "tool": stamp(tool),
            "symbolTables": {"object": obj.symbol_diagnostics, "linked": image.symbol_diagnostics},
            "symbolLookupScope": "Defined nonlocal GLOBAL/WEAK functions only; local names cannot satisfy required external targets, conflicting nonlocal bindings/extents remain rejected."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--object", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--map", type=Path)
    parser.add_argument("--build-directory", type=Path, help="Actual CMake build directory; defaults to profile parent")
    parser.add_argument("--compile-commands", type=Path, help="GNU compile database override; actual link.txt also required")
    parser.add_argument("--output", type=Path, required=True, help="New evidence directory; must not exist")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "audit-script.py.txt").write_bytes(Path(__file__).read_bytes())
    write_json(args.output / "invocation.json", {"argv": sys.argv, "cwd": str(Path.cwd())})
    runner, result, before = Runner(args.output), {"schema": 1, "status": "FAIL"}, {}
    sources, tools_before = [], {}
    command_files = []
    recipe_before = stamp(Path(__file__))
    paths = {"profile": args.profile, "object": args.object, "binary": args.binary}
    if args.map:
        paths["map"] = args.map
    try:
        before = {key: stamp(path) for key, path in paths.items()}
        write_json(args.output / "inputs-before.json", before)
        copies = {}
        for key in ("profile", "map"):
            if key in paths:
                copied = args.output / (key + (".json" if key == "profile" else ".txt"))
                copied.write_bytes(paths[key].read_bytes())
                copies[key] = stamp(copied)
        result["inputCopies"] = copies
        profile = strict_json(args.profile)
        family, sources = check_profile(profile)
        write_json(args.output / "sources-before.json", sources)
        tools_before = {key: stamp(Path(profile["compiler"][key])) for key in
                        ("path", "dumpbin" if family == "MSVC" else "objdump")}
        write_json(args.output / "tools-before.json", tools_before)
        source_body_check(sources)
        proof = audit_msvc(profile, args.object, args.binary, args.map, runner) if family == "MSVC" else audit_gnu(profile, args.object, args.binary, runner)
        commands = command_provenance(profile, args.object, args.binary,
                                      args.build_directory or args.profile.parent, args.compile_commands, args.output)
        command_files = commands["files"]
        after = {key: stamp(path) for key, path in paths.items()}
        require(before == after, "Input artifacts changed during audit")
        require(all(stamp(Path(x["path"]))["sha256"] == x["sha256"] for x in sources), "Source changed during audit")
        result.update(status="PASS", profile=profile, inputs=before, sources=sources, proof=proof,
                      compilationProvenance=commands,
                      scope="Declared x64 compiler/configuration, three audited Vec3 leaf object/link dataflow graphs and caller target/fused-x87 checks; no binary execution, World advance or all-target proof.",
                      callerAssociation={"machineChecked": "Direct calls to the three audited leaves and absence of fused/x87 instructions in the selected contact routine",
                                         "sourceStrictInference": "Plane dot-offset/threshold/comparison and left-associated (rA+rB)+margin follow the reviewed literal source AST plus actual strict non-LTO compiler-command contract",
                                         "entireCallerSymbolicallyProved": False},
                      binaryExecuted=False, runtimeSelfIntrospection=False)
    except BaseException as error:
        result.update(error=type(error).__name__ + ": " + str(error), inputsBefore=before,
                      binaryExecuted=False)
    finally:
        try:
            result["inputsAfter"] = {key: stamp(path) for key, path in paths.items() if path.is_file()}
            result["sourcesAfter"] = [stamp(Path(x["path"])) for x in sources]
            result["toolsAfter"] = {key: stamp(Path(item["path"])) for key, item in tools_before.items()}
            result["compilationFilesAfter"] = [stamp(Path(x["path"])) for x in command_files]
            result["artifactsStable"] = before == result["inputsAfter"]
            result["sourcesStable"] = all(a["sha256"] == b["sha256"] for a, b in zip(sources, result["sourcesAfter"]))
            result["toolsStable"] = tools_before == result["toolsAfter"]
            result["recipeStable"] = recipe_before == stamp(Path(__file__))
            result["compilationFilesStable"] = command_files == result["compilationFilesAfter"]
            require(all(result[x] for x in ("artifactsStable", "sourcesStable", "toolsStable", "recipeStable", "compilationFilesStable")), "Audit inputs changed")
        except BaseException as error:
            result["status"] = "FAIL"
            result["stabilityError"] = type(error).__name__ + ": " + str(error)
        result["commands"] = runner.commands
        result["recipe"] = stamp(Path(__file__))
        write_json(args.output / "audit.json", result)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
