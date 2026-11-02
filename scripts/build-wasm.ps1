param([string]$Clang = 'clang++')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$compiler = Get-Command $Clang -ErrorAction SilentlyContinue
if (-not $compiler) { throw 'clang++ with a WebAssembly backend and wasm-ld is required. No toolchain is installed by this script.' }
$outputDirectory = Join-Path $projectRoot 'build/wasm'
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
$source = Join-Path $projectRoot 'core/src/portable.cpp'
$include = Join-Path $projectRoot 'core/include'
$output = Join-Path $outputDirectory 'pikapika-core.wasm'
& $compiler.Source --target=wasm32 -std=c++20 -O2 -nostdlib -fno-exceptions -fno-rtti "-I$include" $source '-Wl,--no-entry' '-Wl,--export=pp_sweep_fraction' '-Wl,--export=pp_direct_delay' '-Wl,--export=pp_direct_pressure_gain' '-Wl,--export=pp_integrate_velocity' -o $output
if ($LASTEXITCODE -ne 0) { throw 'WASM compilation failed.' }
Write-Output $output
