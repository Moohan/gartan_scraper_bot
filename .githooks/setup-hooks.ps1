# PowerShell script to setup git hooks on Windows
# Setup script for git hooks

Write-Host "🔧 Setting up git hooks for Gartan Scraper Bot..." -ForegroundColor Green

# Check if we're in a git repository
if (-not (Test-Path ".git")) {
    Write-Host "❌ Error: Not in a git repository" -ForegroundColor Red
    exit 1
}

# Create hooks directory if it doesn't exist
if (-not (Test-Path ".git/hooks")) {
    New-Item -ItemType Directory -Path ".git/hooks" -Force
}

# Copy hooks
$hooks = @("pre-commit", "pre-push")

foreach ($hook in $hooks) {
    $sourcePath = ".githooks/$hook"
    $targetPath = ".git/hooks/$hook"
    
    if (Test-Path $sourcePath) {
        Copy-Item $sourcePath $targetPath -Force
        Write-Host "✅ Installed $hook hook" -ForegroundColor Green
    } else {
        Write-Host "❌ Hook file not found: $sourcePath" -ForegroundColor Red
        exit 1
    }
}

# Configure git to use the hooks directory
git config core.hooksPath .githooks

Write-Host "🎉 Git hooks setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Hooks installed:" -ForegroundColor Yellow
Write-Host "  - pre-commit: Runs syntax checks, tests, and validations" -ForegroundColor Gray
Write-Host "  - pre-push: Runs comprehensive tests and Docker build" -ForegroundColor Gray
Write-Host ""
Write-Host "To bypass hooks temporarily, use:" -ForegroundColor Yellow
Write-Host "  git commit --no-verify" -ForegroundColor Gray
Write-Host "  git push --no-verify" -ForegroundColor Gray
