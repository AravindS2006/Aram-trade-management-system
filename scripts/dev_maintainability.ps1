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

Write-Host "Running Vulture dead code scan..." -ForegroundColor Cyan
Invoke-Step { uv run vulture src scripts }

Write-Host "Running Radon complexity scan..." -ForegroundColor Cyan
Invoke-Step { uv run radon cc src -s -a }

Write-Host "Running Interrogate docstring coverage..." -ForegroundColor Cyan
Invoke-Step { uv run interrogate src }

Write-Host "Maintainability checks completed." -ForegroundColor Green
