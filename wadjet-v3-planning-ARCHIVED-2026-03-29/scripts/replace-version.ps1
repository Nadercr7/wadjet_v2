# Wadjet Version Replacement Script
# Run ONLY when you explicitly decide to replace the original v2 with v3-beta
# This archives v2 and promotes v3-beta to the main folder

$originalPath = "D:\Personal attachements\Projects\Wadjet"
$betaPath = "D:\Personal attachements\Projects\Wadjet-v3-beta"
$archivePath = "D:\Personal attachements\Projects\Wadjet-v2-archive"

Write-Host "=== Wadjet Version Replacement ===" -ForegroundColor Yellow
Write-Host "This will:" -ForegroundColor Cyan
Write-Host "  1. Archive current Wadjet/ -> Wadjet-v2-archive/"
Write-Host "  2. Copy Wadjet-v3-beta/ -> Wadjet/"
Write-Host ""

# Safety checks
if (-not (Test-Path $betaPath)) {
    Write-Host "ERROR: Beta path not found: $betaPath" -ForegroundColor Red
    exit 1
}

if (Test-Path $archivePath) {
    Write-Host "ERROR: Archive path already exists: $archivePath" -ForegroundColor Red
    Write-Host "Remove or rename it first." -ForegroundColor Red
    exit 1
}

$confirm = Read-Host "Are you sure? (type 'yes' to confirm)"
if ($confirm -ne "yes") {
    Write-Host "Cancelled." -ForegroundColor Red
    exit
}

# Archive original
if (Test-Path $originalPath) {
    Write-Host "Archiving v2..." -ForegroundColor Cyan
    Rename-Item $originalPath $archivePath
    Write-Host "  Renamed Wadjet/ -> Wadjet-v2-archive/" -ForegroundColor DarkGray
} else {
    Write-Host "  No original Wadjet/ found, skipping archive step." -ForegroundColor DarkGray
}

# Copy v3-beta as main (excluding dev artifacts)
Write-Host "Promoting v3-beta to main..." -ForegroundColor Cyan
$excludeDirs = @('.git', 'node_modules', '__pycache__', '.pytest_cache', 'wadjet-v3-planning')

# Use robocopy for efficient copy with exclusions
$excludeArgs = $excludeDirs | ForEach-Object { "/XD", $_ }
& robocopy $betaPath $originalPath /E /XF "*.db" "*.pyc" @excludeArgs /NFL /NDL /NJH /NJS /NC /NS /NP

Write-Host ""
Write-Host "Done! Wadjet v3 is now the main version." -ForegroundColor Green
Write-Host "Original v2 archived at: $archivePath" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. cd '$originalPath'"
Write-Host "  2. python -m venv .venv"
Write-Host "  3. .venv\Scripts\Activate.ps1"
Write-Host "  4. pip install -r requirements.txt"
Write-Host "  5. npm install"
Write-Host "  6. npm run build"
Write-Host "  7. python -m uvicorn app.main:app --reload"
