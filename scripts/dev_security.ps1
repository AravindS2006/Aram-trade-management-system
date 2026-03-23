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

Write-Host "Running Bandit security scan..." -ForegroundColor Cyan
Invoke-Step { uv run bandit -c pyproject.toml -r src scripts }

Write-Host "Running dependency vulnerability audit..." -ForegroundColor Cyan
Invoke-Step { uv run pip-audit }

Write-Host "Security checks completed." -ForegroundColor Green
