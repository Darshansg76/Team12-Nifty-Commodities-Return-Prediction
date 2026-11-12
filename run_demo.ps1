param([switch]$All, [string]$Date = '')
$ErrorActionPreference = 'Stop'
$projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) { throw 'Run .\setup.ps1 first.' }
$demoArguments = @((Join-Path $PSScriptRoot 'src\demo.py'))
if ($All) { $demoArguments += '--all' }
if ($Date) { $demoArguments += @('--date', $Date) }
& $projectPython @demoArguments
if ($LASTEXITCODE -ne 0) { throw 'Historical demo failed.' }
