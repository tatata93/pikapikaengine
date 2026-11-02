# Native hardware profile follow-up

`native-profile.json` and `native-profile-frames.csv` are a separate follow-up run
at 2026-11-03 02:19 JST (2026-11-02T17:19:21.591Z). The earlier renderer and typed
scene reports remain unchanged. The input is `native-types/typed.scene`: first
camera `[0,18,65]`, three drawable geometry entities, plus source and listener.
The DX12 smoke test submitted 120 frames and exited successfully.

The selected DXGI adapter reports **NVIDIA GeForce GTX 1060 6GB**, PCI vendor 4318
(0x10DE), device 7171 (0x1C03), and 6321864704 bytes dedicated video memory. The
process reports an Intel Core i5-6500 at 3.20 GHz, four logical processors,
17119289344 bytes physical RAM, and Windows 10.0.19045. These data came from DXGI,
CPU identification, and Windows OS/memory APIs; WMI was not used.

The target is 1280 by 720. This smoke window is hidden, so these measurements
describe the CPU loop and submission/present/wait path, not visible presentation
cadence. GPU timestamps remain unavailable. p95 is 18.3555 ms, p99 19.6892 ms,
maximum 23.698 ms, and 56 of 120 intervals exceed 1000/60 ms. This run does not
verify the 60fps requirement or representative gameplay performance.

The executable embeds revision base
`5fa9e4ec919f9db3b3609ed711655c9cdd3f9f3f` and records that the working tree was
dirty when CMake configured the build. It therefore does not claim that this
report came from that clean commit. Embedded SHA256 values identify the exact
viewer and core source contents used; both were compared to the source files
after execution and matched. CMake regenerates those values when either source
changes. Revision base, source hashes, timestamp, adapter information, target,
and limitations are recorded directly in the JSON.
