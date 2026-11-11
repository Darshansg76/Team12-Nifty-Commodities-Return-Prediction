param([string]$PythonExecutable = '')
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
if (-not $PythonExecutable) {
    $bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $bundledPython) { $PythonExecutable = $bundledPython }
    else {
        $PythonExecutable = (& py -3.12 -c 'import sys; print(sys.executable)')
        if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 or pass -PythonExecutable with its absolute path.' }
    }
}
$projectPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    & $PythonExecutable -m venv (Join-Path $projectRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Environment creation failed.' }
}
& $projectPython -m pip install -r (Join-Path $projectRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
Write-Host 'Environment ready. Run .\run_all.ps1 to reproduce the experiment.'

