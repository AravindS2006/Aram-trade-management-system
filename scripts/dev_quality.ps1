param(
    [switch]$Fix
)

$ErrorActionPreference = "Stop"

function Invoke-Step {
    param(
        [scriptblock]$Command
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if ($Fix) {
    Write-Host "Running Ruff auto-fixes..." -ForegroundColor Cyan
    Invoke-Step { uv run ruff check src tests --fix }
    Invoke-Step { uv run ruff format src tests }
}
else {
    Write-Host "Running Ruff lint checks..." -ForegroundColor Cyan
    Invoke-Step { uv run ruff check src tests }
    Invoke-Step { uv run ruff format --check src tests }
}

Write-Host "Running mypy type checks..." -ForegroundColor Cyan
Invoke-Step { uv run mypy src }

Write-Host "Running pytest suite..." -ForegroundColor Cyan
Invoke-Step { uv run pytest }

Write-Host "All quality checks completed." -ForegroundColor Green
