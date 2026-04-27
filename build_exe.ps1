$ErrorActionPreference = "Stop"

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Error "PyInstaller is not installed. Run: pip install pyinstaller"
}

$guiEntry = "src\gui.py"
$cliEntry = "src\main.py"

if (Test-Path $guiEntry) {
    pyinstaller `
        --onefile `
        --windowed `
        --name stock-crawler-gui `
        --clean `
        $guiEntry
}
else {
    Write-Host "GUI entry file not found at $guiEntry. Falling back to CLI build."

    pyinstaller `
        --onefile `
        --name stock-crawler `
        --clean `
        $cliEntry
}
