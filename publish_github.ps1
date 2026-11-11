param(
    [string]$RepositoryName = 'Team12-Nifty-Commodities-Return-Prediction',
    [ValidateSet('private','public')][string]$Visibility = 'private',
    [string]$ExistingRepositoryUrl = ''
)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
& gh auth status
if ($LASTEXITCODE -ne 0) { throw 'GitHub sign-in is required. Run gh auth login, then run this script again.' }
if ($ExistingRepositoryUrl) {
    if ($ExistingRepositoryUrl -notmatch '^https://github\.com/[^/]+/[^/]+(?:\.git)?$') { throw 'Use an HTTPS GitHub repository URL.' }
    $currentRemote = & git -C $projectRoot remote get-url origin 2>$null
    if ($LASTEXITCODE -eq 0) {
        if ($currentRemote -ne $ExistingRepositoryUrl) { throw 'An origin already exists with a different URL. Inspect it before publishing.' }
    } else {
        & git -C $projectRoot remote add origin $ExistingRepositoryUrl
        if ($LASTEXITCODE -ne 0) { throw 'Could not add origin.' }
    }
    & git -C $projectRoot push -u origin main
    if ($LASTEXITCODE -ne 0) { throw 'Push failed. Check repository access and remote history.' }
} else {
    & gh repo create $RepositoryName "--$Visibility" --source $projectRoot --remote origin --push --description 'Team 12 MLBD project comparing five frameworks on official Nifty Commodities returns'
    if ($LASTEXITCODE -ne 0) { throw 'Repository creation or push failed.' }
}
& gh repo view --json url --jq .url
