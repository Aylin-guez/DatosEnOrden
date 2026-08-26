[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeRoot = Join-Path $projectRoot 'data\tmp\ocr_runtime'
$downloadRoot = Join-Path $runtimeRoot 'downloads'
$installRoot = Join-Path $runtimeRoot 'tesseract'
$stagingRoot = Join-Path $runtimeRoot 'tesseract.pending'
$tesseract = Join-Path $installRoot 'tesseract.exe'
$tessdata = Join-Path $installRoot 'tessdata'
$spanishModel = Join-Path $tessdata 'spa.traineddata'

# This Windows build is the version and SHA-256 published in the corresponding
# Microsoft winget manifest. It is installed only below data/tmp.
$installerUrl = 'https://github.com/UB-Mannheim/tesseract/releases/download/v5.4.0.20240606/tesseract-ocr-w64-setup-5.4.0.20240606.exe'
$installerSha256 = 'C885FFF6998E0608BA4BB8AB51436E1C6775C2BAFC2559A19B423E18678B60C9'
$installer = Join-Path $downloadRoot 'tesseract-ocr-w64-setup-5.4.0.20240606.exe'

# The model is from the official Tesseract OCR tessdata_fast repository. The
# pinned SHA-256 is checked after every download; a source change fails closed.
$spanishModelUrl = 'https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/spa.traineddata'
$spanishModelSha256 = '6F2E04D02774A18F01BED44B1111F2CD7F3BA7AC9DC4373CD3F898A40EA6B464'

function Assert-FileHash([string]$Path, [string]$ExpectedSha256) {
    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    return ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash -eq $ExpectedSha256)
}

function Get-VerifiedDownload([string]$Url, [string]$Destination, [string]$ExpectedSha256) {
    if (Test-Path -LiteralPath $Destination) {
        if (Assert-FileHash $Destination $ExpectedSha256) { return }
        throw "Cached OCR dependency has an unexpected SHA-256: $Destination"
    }
    Invoke-WebRequest -Uri $Url -OutFile $Destination
    if (-not (Assert-FileHash $Destination $ExpectedSha256)) {
        throw "Downloaded OCR dependency failed SHA-256 verification: $Destination"
    }
}

New-Item -ItemType Directory -Force -Path $downloadRoot | Out-Null
Get-VerifiedDownload $installerUrl $installer $installerSha256

if (-not (Test-Path -LiteralPath $tesseract)) {
    if (Test-Path -LiteralPath $installRoot) {
        throw "Incomplete local OCR runtime exists at $installRoot. Refusing to overwrite it."
    }
    if (Test-Path -LiteralPath $stagingRoot) {
        throw "Incomplete OCR staging directory exists at $stagingRoot. Refusing to overwrite it."
    }
    $sevenZip = (Get-Command '7z.exe' -ErrorAction SilentlyContinue).Source
    if (-not $sevenZip) {
        $sevenZipCandidate = Join-Path $env:ProgramFiles '7-Zip\7z.exe'
        if (Test-Path -LiteralPath $sevenZipCandidate) { $sevenZip = $sevenZipCandidate }
    }
    if (-not $sevenZip) {
        throw '7-Zip is required only to unpack the verified local OCR payload; no installer was run.'
    }
    # Extract the verified Nullsoft payload rather than running its installer,
    # which prevents registry, Program Files and system-PATH mutations.
    & $sevenZip x $installer "-o$stagingRoot" -y | Out-Null
    if ($LASTEXITCODE -gt 1 -or -not (Test-Path -LiteralPath (Join-Path $stagingRoot 'tesseract.exe'))) {
        throw 'Could not unpack the verified local Tesseract payload.'
    }
    Move-Item -LiteralPath $stagingRoot -Destination $installRoot
}

Get-VerifiedDownload $spanishModelUrl (Join-Path $downloadRoot 'spa.traineddata') $spanishModelSha256
Copy-Item -LiteralPath (Join-Path $downloadRoot 'spa.traineddata') -Destination $spanishModel -Force
$env:TESSDATA_PREFIX = $tessdata
& $tesseract --version
if ($LASTEXITCODE -ne 0) { throw 'The local Tesseract executable failed verification.' }
$languages = (& $tesseract --list-langs) -join "`n"
if ($LASTEXITCODE -ne 0 -or $languages -notmatch '(?m)^(?:tessdata/)?spa$') {
    throw 'The local Tesseract runtime does not expose the Spanish language model.'
}

Write-Output "DEO OCR runtime ready: $tesseract"
