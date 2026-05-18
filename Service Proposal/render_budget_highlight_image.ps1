param(
    [string]$InputPath = ".\經費概估.xlsx",
    [string]$SheetName = "經費概估",
    [string]$OutputPath = ".\經費概估_重點標註.png"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -AssemblyName System.Drawing

function Read-ZipEntryText {
    param(
        [System.IO.Compression.ZipArchive]$Zip,
        [string]$Name
    )
    $entry = $Zip.GetEntry($Name)
    if (-not $entry) { return $null }
    $reader = [System.IO.StreamReader]::new($entry.Open())
    try { return $reader.ReadToEnd() } finally { $reader.Close() }
}

function New-NsManager {
    param([xml]$Xml)
    $ns = [System.Xml.XmlNamespaceManager]::new($Xml.NameTable)
    [void]$ns.AddNamespace("x", "http://schemas.openxmlformats.org/spreadsheetml/2006/main")
    [void]$ns.AddNamespace("r", "http://schemas.openxmlformats.org/officeDocument/2006/relationships")
    return ,$ns
}

function Get-ColNumber {
    param([string]$CellRef)
    if ($CellRef -notmatch "^([A-Z]+)") { return 0 }
    $letters = $Matches[1]
    $n = 0
    foreach ($ch in $letters.ToCharArray()) {
        $n = ($n * 26) + ([int][char]$ch - [int][char]'A' + 1)
    }
    return $n
}

function Format-CellValue {
    param(
        [string]$Value,
        [int]$Column,
        [int]$Row
    )
    if ([string]::IsNullOrWhiteSpace($Value)) { return "" }
    $clean = (($Value -replace "`r|`n", " ") -replace "\s+", " ").Trim()
    $number = 0.0
    if ([double]::TryParse($clean, [System.Globalization.NumberStyles]::Any, [System.Globalization.CultureInfo]::InvariantCulture, [ref]$number)) {
        if ($Column -in @(4, 5, 6)) {
            if (($Column -eq 6 -and $Row -in @(16, 30, 31, 37, 41)) -or ($Row -eq 39 -and $Column -in @(5, 6))) {
                return $number.ToString("#,##0", [System.Globalization.CultureInfo]::InvariantCulture)
            }
            return $number.ToString("#,##0.00", [System.Globalization.CultureInfo]::InvariantCulture)
        }
        if ($Column -eq 3 -and [Math]::Abs($number) -ge 1000) {
            return $number.ToString("#,##0", [System.Globalization.CultureInfo]::InvariantCulture)
        }
    }
    if ($Column -eq 2) {
        $clean = $clean -replace "\.~", "~"
        $clean = $clean -replace "\.小計", "小計"
        if ($Row -eq 41) { $clean = "壹~參 合計" }
    }
    return $clean
}

function Measure-WrappedLines {
    param(
        [System.Drawing.Graphics]$Graphics,
        [string]$Text,
        [System.Drawing.Font]$Font,
        [int]$Width
    )
    if ([string]::IsNullOrWhiteSpace($Text)) { return 1 }
    $words = $Text.ToCharArray()
    $lines = 1
    $line = ""
    foreach ($word in $words) {
        $candidate = $line + $word
        $size = $Graphics.MeasureString($candidate, $Font)
        if ($size.Width -gt $Width -and $line.Length -gt 0) {
            $lines++
            $line = [string]$word
        } else {
            $line = $candidate
        }
    }
    return [Math]::Max(1, $lines)
}

function Draw-WrappedText {
    param(
        [System.Drawing.Graphics]$Graphics,
        [string]$Text,
        [System.Drawing.Font]$Font,
        [System.Drawing.Brush]$Brush,
        [System.Drawing.RectangleF]$Rect,
        [System.Drawing.StringFormat]$Format
    )
    $Graphics.DrawString($Text, $Font, $Brush, $Rect, $Format)
}

$resolvedInput = (Resolve-Path $InputPath).Path
$resolvedOutput = Join-Path (Resolve-Path (Split-Path $OutputPath -Parent -ErrorAction SilentlyContinue)).Path (Split-Path $OutputPath -Leaf)
if ([string]::IsNullOrWhiteSpace((Split-Path $OutputPath -Parent))) {
    $resolvedOutput = Join-Path (Get-Location).Path $OutputPath
}

$zip = [System.IO.Compression.ZipFile]::OpenRead($resolvedInput)
try {
    [xml]$workbook = Read-ZipEntryText $zip "xl/workbook.xml"
    [xml]$rels = Read-ZipEntryText $zip "xl/_rels/workbook.xml.rels"
    [xml]$styles = Read-ZipEntryText $zip "xl/styles.xml"
    $wbNs = New-NsManager $workbook
    $styleNs = New-NsManager $styles

    $sharedStrings = @()
    $sstText = Read-ZipEntryText $zip "xl/sharedStrings.xml"
    if ($sstText) {
        [xml]$sst = $sstText
        $sstNs = New-NsManager $sst
        foreach ($si in $sst.DocumentElement.SelectNodes("//x:si", $sstNs)) {
            $parts = @()
            foreach ($t in $si.SelectNodes(".//x:t", $sstNs)) { $parts += $t.InnerText }
            $sharedStrings += ($parts -join "")
        }
    }

    $fontColors = @{}
    $fonts = $styles.DocumentElement.SelectNodes("//x:fonts/x:font", $styleNs)
    for ($i = 0; $i -lt $fonts.Count; $i++) {
        $color = $fonts[$i].SelectSingleNode("x:color", $styleNs)
        if ($color) {
            $rgb = $color.GetAttribute("rgb")
            if (-not [string]::IsNullOrWhiteSpace($rgb)) { $fontColors[$i] = [string]$rgb }
        }
    }

    $redStyleIds = [System.Collections.Generic.HashSet[int]]::new()
    $xfs = $styles.DocumentElement.SelectNodes("//x:cellXfs/x:xf", $styleNs)
    for ($i = 0; $i -lt $xfs.Count; $i++) {
        $fontId = [int]$xfs[$i].GetAttribute("fontId")
        if ($fontColors.ContainsKey($fontId) -and $fontColors[$fontId] -match "FFFF0000|FF0000") {
            [void]$redStyleIds.Add($i)
        }
    }

    $relMap = @{}
    foreach ($rel in $rels.Relationships.Relationship) { $relMap[$rel.Id] = $rel.Target }
    $sheet = $workbook.DocumentElement.SelectSingleNode("//x:sheet[@name='$SheetName']", $wbNs)
    if (-not $sheet) { throw "Cannot find worksheet: $SheetName" }
    $rid = $sheet.GetAttribute("id", "http://schemas.openxmlformats.org/officeDocument/2006/relationships")
    $sheetPath = "xl/" + ([string]$relMap[$rid]).TrimStart("/")
    [xml]$sheetXml = Read-ZipEntryText $zip $sheetPath
    $sheetNs = New-NsManager $sheetXml

    $rows = @()
    $highlightRows = [System.Collections.Generic.HashSet[int]]::new()
    foreach ($rowNode in $sheetXml.DocumentElement.SelectNodes("//x:sheetData/x:row", $sheetNs)) {
        $rowIndex = [int]$rowNode.GetAttribute("r")
        if ($rowIndex -lt 1 -or $rowIndex -gt 41) { continue }
        $cells = @{}
        foreach ($cellNode in $rowNode.SelectNodes("x:c", $sheetNs)) {
            $cellRef = $cellNode.GetAttribute("r")
            $col = Get-ColNumber $cellRef
            if ($col -lt 1 -or $col -gt 7) { continue }
            $value = ""
            $valueNode = $cellNode.SelectSingleNode("x:v", $sheetNs)
            $inlineNode = $cellNode.SelectSingleNode("x:is", $sheetNs)
            $cellType = $cellNode.GetAttribute("t")
            if ($cellType -eq "s" -and $valueNode) {
                $value = $sharedStrings[[int]$valueNode.InnerText]
            } elseif ($cellType -eq "inlineStr" -and $inlineNode) {
                $parts = @()
                foreach ($t in $inlineNode.SelectNodes(".//x:t", $sheetNs)) { $parts += $t.InnerText }
                $value = $parts -join ""
            } elseif ($valueNode) {
                $value = $valueNode.InnerText
            }
            $cells[$col] = Format-CellValue $value $col $rowIndex
            $styleId = $cellNode.GetAttribute("s")
            if (-not [string]::IsNullOrWhiteSpace($styleId) -and $redStyleIds.Contains([int]$styleId)) {
                [void]$highlightRows.Add($rowIndex)
            }
        }
        if ($cells.Count -gt 0) {
            $rows += [pscustomobject]@{ Index = $rowIndex; Cells = $cells }
        }
    }
} finally {
    $zip.Dispose()
}

$fontFamily = "Microsoft JhengHei"
$headerFont = [System.Drawing.Font]::new($fontFamily, 15, [System.Drawing.FontStyle]::Bold)
$cellFont = [System.Drawing.Font]::new($fontFamily, 12, [System.Drawing.FontStyle]::Bold)
$boldFont = [System.Drawing.Font]::new($fontFamily, 12, [System.Drawing.FontStyle]::Bold)
$smallFont = [System.Drawing.Font]::new($fontFamily, 10.5, [System.Drawing.FontStyle]::Bold)

$colWidths = @(72, 685, 70, 92, 124, 134, 245)
$left = 2
$top = 2
$paddingX = 5
$paddingY = 3
$tableWidth = ($colWidths | Measure-Object -Sum).Sum
$width = [int]($left + $tableWidth + 2)

$measureBmp = [System.Drawing.Bitmap]::new(10, 10)
$measureG = [System.Drawing.Graphics]::FromImage($measureBmp)
$measureG.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit

$rowHeights = @{}
foreach ($row in $rows) {
    $maxLines = 1
    for ($c = 1; $c -le 7; $c++) {
        $text = if ($row.Cells.ContainsKey($c)) { [string]$row.Cells[$c] } else { "" }
        $available = $colWidths[$c - 1] - ($paddingX * 2)
        $font = if ($row.Index -eq 1 -or $row.Index -in @(2, 3, 16, 17, 30, 31, 37, 38, 39, 41)) { $boldFont } else { $cellFont }
        $maxLines = [Math]::Max($maxLines, (Measure-WrappedLines $measureG $text $font $available))
    }
    $baseHeight = if ($row.Index -eq 1) { 40 } elseif ($row.Index -in @(16, 30, 31, 37, 39, 41)) { 38 } else { 34 }
    $rowHeights[$row.Index] = [Math]::Max($baseHeight, ($maxLines * 20) + ($paddingY * 2))
}
$measureG.Dispose()
$measureBmp.Dispose()

$tableHeight = 0
foreach ($row in $rows) { $tableHeight += $rowHeights[$row.Index] }
$height = [int]($top + $tableHeight + 2)

$bmp = [System.Drawing.Bitmap]::new($width, $height)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit
$g.Clear([System.Drawing.Color]::White)

$brushText = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(20, 20, 20))
$brushHeader = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(16, 54, 103))
$brushHeaderText = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::White)
$brushSection = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(248, 248, 248))
$brushSubtotal = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(255, 244, 230))
$brushRedText = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(255, 0, 0))
$brushBlueText = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(0, 45, 255))
$penGrid = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(145, 145, 145), 1)
$penOrange = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(229, 126, 38), 1.4)
$penOuter = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(100, 100, 100), 1.4)

$fmtLeft = [System.Drawing.StringFormat]::new()
$fmtLeft.Alignment = [System.Drawing.StringAlignment]::Near
$fmtLeft.LineAlignment = [System.Drawing.StringAlignment]::Center
$fmtLeft.Trimming = [System.Drawing.StringTrimming]::EllipsisCharacter
$fmtCenter = [System.Drawing.StringFormat]::new()
$fmtCenter.Alignment = [System.Drawing.StringAlignment]::Center
$fmtCenter.LineAlignment = [System.Drawing.StringAlignment]::Center
$fmtRight = [System.Drawing.StringFormat]::new()
$fmtRight.Alignment = [System.Drawing.StringAlignment]::Far
$fmtRight.LineAlignment = [System.Drawing.StringAlignment]::Center

$y = $top
foreach ($row in $rows) {
    $h = $rowHeights[$row.Index]
    $isHeader = $row.Index -eq 1
    $isSubtotal = $row.Index -in @(16, 30, 39)
    $isTotal = $row.Index -in @(31, 37, 41)
    $isSection = $row.Index -in @(2, 3, 17, 38)

    if ($isHeader) {
        $g.FillRectangle($brushHeader, $left, $y, $tableWidth, $h)
    } elseif ($isSubtotal) {
        $g.FillRectangle($brushSubtotal, $left, $y, $tableWidth, $h)
    } elseif ($isTotal) {
        $g.FillRectangle($brushSection, $left, $y, $tableWidth, $h)
    }

    $x = $left
    for ($c = 1; $c -le 7; $c++) {
        $w = $colWidths[$c - 1]
        $rect = [System.Drawing.RectangleF]::new($x + $paddingX, $y + $paddingY, $w - ($paddingX * 2), $h - ($paddingY * 2))
        $text = if ($row.Cells.ContainsKey($c)) { [string]$row.Cells[$c] } else { "" }
        $font = if ($isHeader) { $headerFont } elseif ($isTotal -or $isSection) { $boldFont } else { $cellFont }
        if ($row.Index -eq 39 -and $c -in @(5, 6)) {
            $brush = $brushBlueText
            $font = $boldFont
        } elseif (($row.Index -in @(16, 30, 31) -and $c -eq 6) -or ($row.Index -in @(16, 30, 39) -and $c -eq 7)) {
            $brush = $brushRedText
            $font = $boldFont
        } elseif ($isHeader) {
            $brush = $brushHeaderText
        } else {
            $brush = $brushText
        }
        $fmt = if ($c -in @(4, 5, 6)) { $fmtRight } elseif ($c -eq 3) { $fmtCenter } else { $fmtLeft }
        Draw-WrappedText $g $text $font $brush $rect $fmt
        $g.DrawRectangle($penGrid, $x, $y, $w, $h)
        $x += $w
    }
    if ($isSubtotal) {
        $g.DrawRectangle($penOrange, $left, $y, $tableWidth, $h)
    }
    $y += $h
}

$g.DrawRectangle($penOuter, $left, $top, $tableWidth, $tableHeight)

$outDir = Split-Path $resolvedOutput -Parent
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
$bmp.Save($resolvedOutput, [System.Drawing.Imaging.ImageFormat]::Png)

$fmtLeft.Dispose()
$fmtCenter.Dispose()
$fmtRight.Dispose()
$g.Dispose()
$bmp.Dispose()
$headerFont.Dispose()
$cellFont.Dispose()
$boldFont.Dispose()
$smallFont.Dispose()
$brushText.Dispose()
$brushHeader.Dispose()
$brushHeaderText.Dispose()
$brushSection.Dispose()
$brushSubtotal.Dispose()
$brushRedText.Dispose()
$brushBlueText.Dispose()
$penGrid.Dispose()
$penOrange.Dispose()
$penOuter.Dispose()

Write-Output $resolvedOutput
