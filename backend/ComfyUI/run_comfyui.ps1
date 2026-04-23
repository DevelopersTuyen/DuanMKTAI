$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPath = Join-Path $scriptDir ".venv"
$pythonExe = Join-Path $venvPath "Scripts\\python.exe"
$requirements = Join-Path $scriptDir "requirements.txt"
$markerFile = Join-Path $venvPath ".requirements_installed"
$torchMarkerFile = Join-Path $venvPath ".torch_variant"

Set-Location $scriptDir

if (-not (Test-Path $venvPath)) {
    Write-Host "[ComfyUI] Tao moi moi truong ao..." -ForegroundColor Cyan
    python -m venv $venvPath
}

if (-not (Test-Path $pythonExe)) {
    throw "Khong tim thay Python trong .venv cua ComfyUI."
}

$hasNvidia = $false
try {
    $null = & nvidia-smi
    if ($LASTEXITCODE -eq 0) {
        $hasNvidia = $true
    }
} catch {
    $hasNvidia = $false
}

$desiredTorchVariant = if ($hasNvidia) { "cu126" } else { "cpu" }
$installedTorchVariant = ""

if (Test-Path $torchMarkerFile) {
    $installedTorchVariant = (Get-Content $torchMarkerFile -Raw).Trim()
}

$torchNeedsInstall = $desiredTorchVariant -ne $installedTorchVariant

if (-not $torchNeedsInstall) {
    try {
        $torchCheck = & $pythonExe -c "import torch; print((torch.version.cuda or 'cpu').strip())"
        if ($desiredTorchVariant -eq "cu126" -and $torchCheck -eq "cpu") {
            $torchNeedsInstall = $true
        }
    } catch {
        $torchNeedsInstall = $true
    }
}

if ($torchNeedsInstall) {
    if ($desiredTorchVariant -eq "cu126") {
        Write-Host "[ComfyUI] Cai lai torch ban CUDA (cu126)..." -ForegroundColor Cyan
        & $pythonExe -m pip uninstall -y torch torchvision torchaudio
        & $pythonExe -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
    } else {
        Write-Host "[ComfyUI] Cai torch ban CPU..." -ForegroundColor Cyan
        & $pythonExe -m pip uninstall -y torch torchvision torchaudio
        & $pythonExe -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
    }
    Set-Content -LiteralPath $torchMarkerFile -Value $desiredTorchVariant -Encoding ASCII
}

$requirementsHash = (Get-FileHash $requirements -Algorithm SHA256).Hash
$installedHash = ""

if (Test-Path $markerFile) {
    $installedHash = (Get-Content $markerFile -Raw).Trim()
}

if ($requirementsHash -ne $installedHash) {
    Write-Host "[ComfyUI] Cai dat dependencies..." -ForegroundColor Cyan
    & $pythonExe -m pip install --upgrade pip
    & $pythonExe -m pip install -r $requirements
    Set-Content -LiteralPath $markerFile -Value $requirementsHash -Encoding ASCII
}

Write-Host "[ComfyUI] Dang chay tai http://127.0.0.1:8188" -ForegroundColor Green
if ($hasNvidia) {
    & $pythonExe main.py --listen 127.0.0.1 --port 8188
} else {
    & $pythonExe main.py --cpu --listen 127.0.0.1 --port 8188
}
