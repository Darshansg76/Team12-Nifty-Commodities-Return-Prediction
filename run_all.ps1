param([switch]$RefreshData)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$projectPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) { throw 'Run .\setup.ps1 first.' }
if ($RefreshData) {
    & $projectPython (Join-Path $projectRoot 'src\download_data.py')
    if ($LASTEXITCODE -ne 0) { throw 'Data download failed.' }
}
& $projectPython (Join-Path $projectRoot 'src\pipeline.py')
if ($LASTEXITCODE -ne 0) { throw 'Training failed.' }
& $projectPython -m unittest discover -s (Join-Path $projectRoot 'tests') -v
if ($LASTEXITCODE -ne 0) { throw 'Validation failed.' }
& $projectPython (Join-Path $projectRoot 'scripts\build_notebook.py')
if ($LASTEXITCODE -ne 0) { throw 'Notebook execution failed.' }
& $projectPython (Join-Path $projectRoot 'scripts\build_report.py')
if ($LASTEXITCODE -ne 0) { throw 'Report generation failed.' }
Write-Host 'Experiment, tests, notebook and Word report regenerated. See docs/REPRODUCIBILITY.md for slide and PDF rendering.'

