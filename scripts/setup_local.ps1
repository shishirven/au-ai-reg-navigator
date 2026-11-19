# One-command local setup for Windows (PowerShell). Run from the repo root:
#   powershell -ExecutionPolicy Bypass -File scripts\setup_local.ps1
$ErrorActionPreference = "Stop"
$GenModel = if ($env:GEN_MODEL) { $env:GEN_MODEL } else { "qwen3:4b" }
$JudgeModel = if ($env:JUDGE_MODEL) { $env:JUDGE_MODEL } else { "gemma3:4b" }

Write-Host "==> 1/6 uv"
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}
Write-Host "==> 2/6 Python dependencies"
uv sync --frozen

Write-Host "==> 3/6 Ollama"
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
  Write-Host "Install Ollama for Windows from https://ollama.com/download, start it, then re-run."
  exit 1
}

Write-Host "==> 4/6 Models: $GenModel and $JudgeModel"
ollama pull $GenModel
ollama pull $JudgeModel

Write-Host "==> 5/6 .env and index"
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
uv run python -m regnav.cli ingest --config configs/local_stratified.yaml

Write-Host "==> 6/6 Smoke test (1-3 min on CPU)"
uv run python -m regnav.cli ask --config configs/local_stratified.yaml --model $GenModel --sector bank "What do we need to do before engaging a third-party AI vendor?"
