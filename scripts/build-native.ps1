param([string]$Configuration = 'Release')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$buildDirectory = Join-Path $projectRoot 'build/native'
cmake -S $projectRoot -B $buildDirectory
if ($LASTEXITCODE -ne 0) { throw 'CMake configuration failed. Install a C++20 compiler and Windows SDK.' }
cmake --build $buildDirectory --config $Configuration --parallel
if ($LASTEXITCODE -ne 0) { throw 'Native build failed.' }
ctest --test-dir $buildDirectory -C $Configuration --output-on-failure
if ($LASTEXITCODE -ne 0) { throw 'Native core tests failed.' }
