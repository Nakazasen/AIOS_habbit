$scriptPath = "C:\Users\Admin\teamwork_projects\c_drive_cleanup\Clean-CDrive.ps1"

Write-Host "=== INDEPENDENT AUDITOR VERIFICATION ===" -ForegroundColor Cyan

# Test 1: Live Simulation (-WhatIf -PassThru)
Write-Host "--- Test 1: Live Simulation (-WhatIf) ---"
$liveSim = & $scriptPath -WhatIf -Quiet -PassThru
Write-Host "Discovered $($liveSim.DetailedResults.Count) targets on system."
Write-Host "Total potential space: $($liveSim.TotalFreedFormatted) ($($liveSim.TotalFreedBytes) bytes)"
Write-Host "Simulated files to clean: $($liveSim.TotalDeletedFiles)"
Write-Host "IsWhatIf flag: $($liveSim.IsWhatIf)"

if ($liveSim.IsWhatIf -ne $true) { throw "Test 1 Failed: IsWhatIf flag not set" }

# Test 2: Independent Sandbox & Downloads preservation
Write-Host "--- Test 2: Downloads Preservation in Isolated Sandbox ---"
$sandbox = Join-Path $env:TEMP "Auditor_Sandbox_$(Get-Random)"
$sandboxTemp = Join-Path $sandbox "MockTemp"
$sandboxDownloads = Join-Path $sandbox "MockUser\Downloads"
New-Item -ItemType Directory -Path $sandboxTemp -Force | Out-Null
New-Item -ItemType Directory -Path $sandboxDownloads -Force | Out-Null

$tempFile = Join-Path $sandboxTemp "junk_temp.dat"
$dlFile = Join-Path $sandboxDownloads "critical_download.zip"
[System.IO.File]::WriteAllBytes($tempFile, (New-Object byte[] 2048))
[System.IO.File]::WriteAllBytes($dlFile, (New-Object byte[] 10240))

$cleanResult = & $scriptPath -Targets @($sandboxTemp, $sandboxDownloads) -Quiet -PassThru

$tempExists = Test-Path $tempFile
$dlExists = Test-Path $dlFile

Write-Host "Temp file deleted: $(-not $tempExists)"
Write-Host "Downloads file preserved: $dlExists"
Write-Host "Freed bytes: $($cleanResult.TotalFreedBytes) (Expected: 2048)"
Write-Host "Protected skipped: $($cleanResult.TotalProtectedSkipped)"

if ($tempExists) { throw "Test 2 Failed: Temp file was not cleaned" }
if (-not $dlExists) { throw "Test 2 Failed: Downloads file was deleted!" }
if ($cleanResult.TotalFreedBytes -ne 2048) { throw "Test 2 Failed: Incorrect freed bytes ($($cleanResult.TotalFreedBytes))" }

# Test 3: Locked File Graceful Recovery
Write-Host "--- Test 3: In-Use / Locked File Handling ---"
$lockedDir = Join-Path $sandbox "LockedDir"
New-Item -ItemType Directory -Path $lockedDir -Force | Out-Null
$lockedFile = Join-Path $lockedDir "locked.log"
$normalFile = Join-Path $lockedDir "normal.tmp"
[System.IO.File]::WriteAllBytes($lockedFile, (New-Object byte[] 4096))
[System.IO.File]::WriteAllBytes($normalFile, (New-Object byte[] 4096))

$lockStream = [System.IO.File]::Open($lockedFile, [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
try {
    $lockRes = & $scriptPath -Targets @($lockedDir) -Quiet -PassThru
    Write-Host "Deleted files: $($lockRes.TotalDeletedFiles) (Expected: 1)"
    Write-Host "Skipped files: $($lockRes.TotalSkippedFiles) (Expected: 1)"
    Write-Host "Normal file deleted: $(-not (Test-Path $normalFile))"
    Write-Host "Locked file preserved: $(Test-Path $lockedFile)"

    if ($lockRes.TotalDeletedFiles -ne 1 -or $lockRes.TotalSkippedFiles -ne 1) {
        throw "Test 3 Failed: Locked file handling mismatch"
    }
} finally {
    $lockStream.Close()
    $lockStream.Dispose()
}

# Cleanup sandbox
Remove-Item -LiteralPath $sandbox -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "=== ALL INDEPENDENT AUDITOR TESTS PASSED SUCCESSFULLY ===" -ForegroundColor Green
