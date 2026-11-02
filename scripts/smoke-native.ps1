param([string]$Configuration = 'Release', [string]$Scene = '')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$buildDirectory = Join-Path $projectRoot 'build/native'
$executable = Join-Path $buildDirectory "$Configuration/pikapika-viewer.exe"
if (-not (Test-Path -LiteralPath $executable)) { throw 'Build first: ./scripts/build-native.ps1' }
$arguments = @('--smoke-test')
if ($Scene) {
    $sceneFile = (Resolve-Path -LiteralPath $Scene).Path
    $arguments += @('--scene', ('"' + $sceneFile + '"'))
}
$errorReport = Join-Path $buildDirectory 'native-smoke-error.txt'
if (Test-Path -LiteralPath $errorReport) { Remove-Item -LiteralPath $errorReport }
$viewerProcess = Start-Process -FilePath $executable -ArgumentList $arguments -WorkingDirectory $buildDirectory -WindowStyle Hidden -PassThru
if (-not $viewerProcess.WaitForExit(30000)) { $viewerProcess.Kill(); throw 'DirectX 12 smoke test exceeded 30 seconds.' }
if ($viewerProcess.ExitCode -ne 0) {
    if (Test-Path -LiteralPath $errorReport) { Get-Content -LiteralPath $errorReport }
    throw "DirectX 12 smoke test failed: exit $($viewerProcess.ExitCode)"
}
Get-Content -LiteralPath (Join-Path $buildDirectory 'native-smoke.json')
Write-Output "GPU readback image: $(Join-Path $buildDirectory 'native-smoke.bmp')"
Write-Output "Raw loop timing: $(Join-Path $buildDirectory 'native-frames.csv')"
