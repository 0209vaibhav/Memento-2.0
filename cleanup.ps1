# Cleanup script for MEMENTO repository
Write-Host "Starting MEMENTO repository cleanup..." -ForegroundColor Green

# Function to safely remove directories
function Remove-DirectoryIfExists {
    param (
        [string]$Path
    )
    if (Test-Path $Path) {
        Write-Host "Removing $Path..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force $Path
    }
}

# Function to safely remove files
function Remove-FileIfExists {
    param (
        [string]$Path
    )
    if (Test-Path $Path) {
        Write-Host "Removing $Path..." -ForegroundColor Yellow
        Remove-Item -Force $Path
    }
}

# Remove unnecessary directories
Remove-DirectoryIfExists "venv"
Remove-DirectoryIfExists ".venv"
Remove-DirectoryIfExists "node_modules"
Remove-DirectoryIfExists ".firebase"

# Remove duplicate JSON files
Remove-FileIfExists "memento_categories_keyword.json"
Remove-FileIfExists "memento_tags_keyword.json"

# Remove temporary files
Remove-FileIfExists "firebase-setup.txt"
Remove-FileIfExists "event_list_lines.txt"

# Keep only one version of categories and tags
if (Test-Path "memento_categories_combined.json") {
    Remove-FileIfExists "memento_categories.json"
    Rename-Item "memento_categories_combined.json" "memento_categories.json"
}

if (Test-Path "memento_tags_combined.json") {
    Remove-FileIfExists "memento_tags.json"
    Rename-Item "memento_tags_combined.json" "memento_tags.json"
}

Write-Host "Cleanup completed successfully!" -ForegroundColor Green
Write-Host "Please run 'npm install' to reinstall dependencies if needed." -ForegroundColor Cyan 