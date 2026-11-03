# Compiled WebAssembly runtime notices

The engine's dynamics, hydrostatics, geometry and C ABI are authored in this
repository. `assets/pikapika-simulation.mjs` is generated Emscripten glue;
`assets/pikapika-simulation.wasm` also contains linked C/C++ standard runtime
code, allocator, compiler builtins and exception support. These files are not
entirely original engine code. No third-party game physics solver is linked.

Official SDK: https://github.com/emscripten-core/emsdk

- SDK 6.0.13, emsdk revision `d7b4130688bfa348392b921ab04015aa15c4f154`.
- Official release build `eb132757325583b787fe9414b09afea9442b72ad`.
- Emscripten source revision `e13ee988ce3d87a738dd8f3661d02223308c412a`.
- Emscripten generated runtime: MIT / University of Illinois NCSA notices in
  `EMSCRIPTEN-LICENSE.txt`, including the listed incorporated portions.
- libc++ / libc++abi / libunwind / compiler-rt: respective full license files
  here, including Apache-2.0 WITH LLVM-exception and legacy component notices.
- musl libc: `MUSL-COPYRIGHT.txt`; linked math per-file notices, including Sun
  Microsystems permission notices, in `MUSL-MATH-NOTICES.txt`.

Preserve these notices with redistributed generated artifacts. The exact linked
archive members, artifact/source SHA-256 values and notice hashes are recorded
in `assets/pikapika-simulation.build.json`. `scripts/build-simulation.mjs`
copies the notices from the installed official SDK and records the link map.
Compiler, SDK tools, SDK Node/Python and link maps remain in ignored `build/`;
they are not shipped to browsers. `-sFILESYSTEM=0`, no npm runtime dependency,
no CDN, no threads. The separate 650-byte freestanding module has its own
provenance and does not contain this standard runtime.

The license for original engine code is still undecided. These third-party
notices do not license the whole project or declare an engine copyright owner.
