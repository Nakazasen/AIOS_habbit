# PLAN.md — teamwork_preview_reviewer (Round 2)

## Plan of Action

1. **Root Junction Reparse Isolation**:
   - In `Get-SafeFileSystemEntries`: Check whether `$RootPath` itself is a ReparsePoint (junction/symlink). If so, do not traverse it; treat it as an isolated reparse point.
   - In `Test-IsProtectedPath`: Resolve link targets (`.Target` / `LinkType`) to check if any symlink/junction points to Downloads or protected system folders.

2. **Drive Root and Format Protection**:
   - In `Test-IsProtectedPath`: Guard against bare drive paths (`C:`, `C:\`, `D:\`) using regex `^[a-zA-Z]:[\\/]?$`.
   - Strip leading/trailing quotes and spaces.

3. **Browser Channel and Profile Discovery (Open Issue 2)**:
   - Include EdgeCore, Chrome SxS/Canary, Edge Canary, Dev, Beta, WebView2.
   - Expand cache directory heuristics to include `blob_storage`, `BrowserMetrics`, `DawnWebGPUCache`, `GraphiteDawnCache`, and crash dumps.
   - Expand custom profile discovery heuristics.

4. **Multi-User / Non-Elevated Permission Handling (Open Issue 3)**:
   - In `Get-SafeFileSystemEntries`: Collect inaccessible directories when encountering `UnauthorizedAccessException`.
   - In `Invoke-FolderCleanup`: Record meaningful warnings into `Errors` and warn users if elevation is required.

5. **Locked Directory & Child Items Robustness (Open Issue 1)**:
   - Clear read-only attributes on files and directories before attempting removal.
   - Fallback file deletion to `[System.IO.File]::Delete` inside try/catch.
   - Ensure bottom-up folder cleanup safely skips folders holding locked items.

6. **Pipeline Support & Output Formatting**:
   - Support pipeline input objects (`FileInfo`, `DirectoryInfo`, strings) smoothly.
   - Add Exabyte (EB) formatting in `Format-ByteSize`.

7. **Test Suite Expansion**:
   - Add unit and integration tests in `Clean-CDrive.Tests.ps1` for:
     - Root junction target isolation
     - Drive root rejection
     - Piped input processing
     - Non-elevated directory warning logging
     - Chromium multi-channel cache targets
     - Read-only directory deletion
     - Exabyte formatting
