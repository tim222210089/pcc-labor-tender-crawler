# TWSE Stock Crawler

TWSE stock data crawler with both command-line and GUI launch flows.

## Install

```powershell
pip install -e .
```

## CLI Usage

Run the CLI module directly:

```powershell
python -m src.main --stock 2330 --month 2026-04
```

Or use the installed console script:

```powershell
stock-crawler --stock 2330 --month 2026-04
```

Example JSON export:

```powershell
stock-crawler --stock 2317 --month 2026-04 --format json
```

### CLI Options

```text
--stock    Stock code, for example 2330
--month    Month in YYYY-MM format
--dataset  Dataset name: daily or average
--format   Output format: csv or json
--output   Output file path
```

## GUI Usage

The package also exposes a GUI launcher that targets `src.gui:main`.

After installation, start the GUI with:

```powershell
stock-crawler-gui
```

If you prefer running the module entry file directly and `src/gui.py` exists in your checkout:

```powershell
python -m src.gui
```

## Windows Executable Build

Install PyInstaller first:

```powershell
pip install pyinstaller
```

Build the executable:

```powershell
.\build_exe.ps1
```

Behavior:

- If `src\gui.py` exists, the script builds a windowed GUI executable named `stock-crawler-gui.exe`.
- Otherwise, it falls back to the CLI entry file and builds `stock-crawler.exe`.

Built files are written under `dist\`.

## Tests

```powershell
python -m unittest discover -s tests
```
