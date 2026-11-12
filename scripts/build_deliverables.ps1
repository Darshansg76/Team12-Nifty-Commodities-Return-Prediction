# Rebuild every presentation/report artifact from the same saved experiment.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$projectPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
$runtimeRoot = $env:CODEX_PRIMARY_RUNTIME_DEPENDENCIES
if (-not $runtimeRoot) { $runtimeRoot = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies' }
$skillsRoot = Join-Path $env:USERPROFILE '.codex\plugins\cache\openai-primary-runtime'
$slidesSkill = $env:PRESENTATIONS_SKILL_DIR
if (-not $slidesSkill) { $slidesSkill = Join-Path $skillsRoot 'presentations\26.1111.10930\skills\presentations' }
$documentsSkill = $env:DOCUMENTS_SKILL_DIR
if (-not $documentsSkill) { $documentsSkill = Join-Path $skillsRoot 'documents\26.1111.10930\skills\documents' }
$pdfSkill = $env:PDF_SKILL_DIR
if (-not $pdfSkill) { $pdfSkill = Join-Path $skillsRoot 'pdf\26.1111.10930\skills\pdf' }
$runtimeNode = Join-Path $runtimeRoot 'node\bin\node.exe'
$runtimePython = Join-Path $runtimeRoot 'python\python.exe'
foreach ($required in @($runtimeNode, $runtimePython, (Join-Path $documentsSkill 'render_docx.py'), (Join-Path $slidesSkill 'container_tools\artifact_tool_utils.mjs'))) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw 'Full report/slide authoring needs the prepared Codex runtime. Use .\run_all.ps1 -ResultsOnly for training and notebook only; finished reports and PPT are already included.'
    }
}

& $runtimeNode (Join-Path $documentsSkill 'container_tools\mark_artifact_operation_started.mjs') --operation-kind edit --expected-output-count 1 --output-format docx
if ($LASTEXITCODE -ne 0) { throw 'Word authoring initialization failed.' }
& $projectPython (Join-Path $PSScriptRoot 'build_report.py')
if ($LASTEXITCODE -ne 0) { throw 'Word report generation failed.' }

& $runtimeNode (Join-Path $pdfSkill 'container_tools\mark_artifact_operation_started.mjs') --operation-kind edit --expected-output-count 1 --output-format pdf
if ($LASTEXITCODE -ne 0) { throw 'PDF authoring initialization failed.' }
$originalPath = $env:PATH
try {
    # The packaged renderer uses native LibreOffice on Windows and bundled Poppler.
    $env:PATH = "C:\Program Files\LibreOffice\program;$(Join-Path $runtimeRoot 'native\poppler\Library\bin');$originalPath"
    $renderFolder = Join-Path $projectRoot '.build\report_final'
    & $runtimePython (Join-Path $documentsSkill 'render_docx.py') (Join-Path $projectRoot 'deliverables\Team_12_Project_Report.docx') --output_dir $renderFolder --emit_pdf
    if ($LASTEXITCODE -ne 0) { throw 'Report PDF rendering failed.' }
    Copy-Item -LiteralPath (Join-Path $renderFolder 'Team_12_Project_Report.pdf') -Destination (Join-Path $projectRoot 'deliverables\Team_12_Project_Report.pdf') -Force
} finally { $env:PATH = $originalPath }

& $runtimeNode (Join-Path $slidesSkill 'container_tools\mark_artifact_operation_started.mjs') --operation-kind edit --expected-output-count 1 --output-format pptx
if ($LASTEXITCODE -ne 0) { throw 'Presentation authoring initialization failed.' }
& $runtimeNode (Join-Path $PSScriptRoot 'build_slides.mjs')
if ($LASTEXITCODE -ne 0) { throw 'PowerPoint generation failed.' }
& $projectPython (Join-Path $PSScriptRoot 'prepare_release.py')
if ($LASTEXITCODE -ne 0) { throw 'Submission packaging failed.' }
