# Watch-Mailbox.ps1
# Poll mailbox Muse<->OMP tren GitHub moi ~90 giay.
# Gap ticket moi (trang thai `moi`): hien popup nhac + luu prompt.md thanh
# _ticket-moi.md ngay trong thu muc nay de OMP doc.
# Gap trang thai `xong`: popup bao het viec (vong lap ket thuc).
#
# Cai dat: copy file nay vao D:\Sandbox\AIOS_habbit\docs\phieu-viec\mailbox\
# roi tao shortcut trong shell:startup de tu chay moi khi mo may.
# Chi tiet: xem HUONG-DAN-WATCHER.md cung thu muc.

$ErrorActionPreference = "SilentlyContinue"

$owner       = "Nakazasen"
$repo        = "AIOS_habbit"
$branch      = "phieu-viec/rag-fix1"
$pollSeconds = 90
$stateFile   = Join-Path $PSScriptRoot "watcher_state.json"
$ticketFile  = Join-Path $PSScriptRoot "_ticket-moi.md"
$logFile     = Join-Path $PSScriptRoot "watcher.log"
# Muon poll moi 60 giay: tao token fine-grained (chi can quyen Contents: read),
# roi bo comment dong duoi va dan token vao. KHONG commit token len git.
# $token = "DAN_TOKEN_VAO_DAY"

# Chong chay 2 ban cung luc
$mutex = New-Object System.Threading.Mutex($false, "Global\MailboxWatcher")
if (-not $mutex.WaitOne(0)) { exit }

function Get-MailboxFile {
    param([string]$path)
    $url = "https://api.github.com/repos/$owner/$repo/contents/$path?ref=" + [uri]::EscapeDataString($branch)
    $headers = @{"Accept" = "application/vnd.github+json"; "User-Agent" = "mailbox-watcher"}
    if ($token) { $headers["Authorization"] = "Bearer $token" }
    $data = Invoke-RestMethod -Uri $url -Headers $headers -TimeoutSec 30
    return [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($data.content))
}

function Show-Popup {
    param([string]$title, [string]$msg)
    (New-Object -ComObject Wscript.Shell).Popup($msg, 20, $title, 64) | Out-Null
}

$lastStatus = ""; $lastTicket = ""
if (Test-Path $stateFile) {
    try {
        $st = Get-Content $stateFile -Raw | ConvertFrom-Json
        $lastStatus = $st.status; $lastTicket = $st.ticket
    } catch {}
}

while ($true) {
    try {
        $text = Get-MailboxFile "docs/phieu-viec/mailbox/trang-thai.md"
        $status = ""; $ticket = ""
        if ($text -match 'Trạng thái:\s*`([^`]+)`') { $status = $Matches[1].Trim() }
        if ($text -match 'Ticket hiện tại:\s*([^\r\n]+)') { $ticket = $Matches[1].Trim() }

        if ($status -eq "moi" -and ($status -ne $lastStatus -or $ticket -ne $lastTicket)) {
            try {
                $prompt = Get-MailboxFile "docs/phieu-viec/mailbox/prompt.md"
                $prompt | Out-File -FilePath $ticketFile -Encoding utf8
            } catch {}
            Show-Popup "Mailbox: ticket moi" ("Co ticket moi cho OMP:`n$ticket`n`nDa luu ban local: _ticket-moi.md`nBao OMP doc va lam theo prompt.")
        }
        elseif ($status -eq "xong" -and $status -ne $lastStatus) {
            Show-Popup "Mailbox: het viec" "Khong con ticket nao. Vong lap khep kin ket thuc."
        }

        $lastStatus = $status; $lastTicket = $ticket
        @{status = $status; ticket = $ticket; updated = (Get-Date).ToString("s") } | ConvertTo-Json | Out-File $stateFile -Encoding utf8
    } catch {
        ("[{0}] loi: {1}" -f (Get-Date).ToString("s"), $_.Exception.Message) | Out-File $logFile -Append -Encoding utf8
    }
    Start-Sleep -Seconds $pollSeconds
}
