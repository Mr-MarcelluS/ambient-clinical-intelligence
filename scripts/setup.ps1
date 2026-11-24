$ErrorActionPreference = "Stop"
py -3.12 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "Python 3.12 is required" }
& .\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed" }
if (!(Test-Path .env)) { Copy-Item .env.example .env }
Write-Host "Run: .\.venv\Scripts\python.exe -m streamlit run app/main.py"
