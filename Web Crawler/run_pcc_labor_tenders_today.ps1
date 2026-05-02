$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = 'C:\Users\tim\AppData\Local\Programs\Python\Python312\python.exe'
$pythonScript = Join-Path $scriptDir 'export_pcc_labor_tenders.py'
$outputFile = Join-Path $scriptDir 'pcc_labor_tenders_today.xlsx'

function Pause-ForExit {
    Write-Host ''
    Read-Host 'Press Enter to exit'
}

Set-Location -LiteralPath $scriptDir

if (-not (Test-Path -LiteralPath $pythonExe)) {
    Write-Host "Python not found: $pythonExe" -ForegroundColor Red
    Pause-ForExit
    exit 1
}

if (-not (Test-Path -LiteralPath $pythonScript)) {
    Write-Host "Export script not found: $pythonScript" -ForegroundColor Red
    Pause-ForExit
    exit 1
}

Write-Host 'Starting PCC tender export...' -ForegroundColor Cyan
Write-Host "Working directory: $scriptDir"
Write-Host "Output file: $outputFile"
Write-Host ''

& $pythonExe $pythonScript --date today --output $outputFile
$exitCode = $LASTEXITCODE

Write-Host ''
if ($exitCode -ne 0) {
    Write-Host "Export failed with exit code: $exitCode" -ForegroundColor Red
    Pause-ForExit
    exit $exitCode
}

if (-not (Test-Path -LiteralPath $outputFile)) {
    Write-Host "Export finished but output file was not found: $outputFile" -ForegroundColor Red
    Pause-ForExit
    exit 1
}

Write-Host 'Export completed.' -ForegroundColor Green
Write-Host "Excel file: $outputFile" -ForegroundColor Green
Pause-ForExit
exit 0
