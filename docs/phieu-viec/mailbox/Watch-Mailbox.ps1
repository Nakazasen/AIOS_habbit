# Watch-Mailbox.ps1 (v2)
# Poll mailbox Muse<->OMP tren GitHub moi ~90 giay.
#  - Gap ticket `moi` moi: popup + luu prompt.md thanh _ticket-moi.md.
#  - Ticket `moi` qua 15 phut khong ai nhan: popup nhac lai.
#  - OMP bao `xong-cho-duyet`: popup (Muse poll 5 phut se review ngay).
#  - `dang-lam` qua 20 phut khong tien trien (ghi_chu/commit dung yen):
#    popup canh bao co ve ket.
#  - Trang thai `xong`: popup bao het viec, vong lap ket thuc.
#
# Cai dat: xem HUONG-DAN-WATCHER.md cung thu muc.

$ErrorActionPreference = "SilentlyContinue"

$owner          = "Nakazasen"
$repo           = "AIOS_habbit"
$branch         = "phieu-viec/rag-fix1"
$pollSeconds    = 90
$moiWarnMinutes = 15
$stuckMinutes   = 20
$stateFile      = Join-Path $PSScriptRoot "watcher_state.json"
$ticketFile     = Join-Path $PSScriptRoot "_ticket-moi.md"
$logFile        = Join-Path $PSScriptRoot "watcher.log"
# Muon poll moi 60 giay: tao token fine-grained (chi can quyen Contents: read),
# roi bo comment dong duoi va dan token vao. KHONG commit token len git.
# $token = "DAN_TOKEN_VAO_DAY"

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

function Parse-Field {
    param([string]$text, [string]$pattern)
    if ($text -match $pattern) { return $Matches[1].Trim() }
    return ""
}

$st = @{}
if (Test-Path $stateFile) {
    try { $st = Get-Content $stateFile -Raw | ConvertFrom-Json } catch {}
}
function St-Get($k, $d) { if ($st.PSObject.Properties.Name -contains $k) { return $st.$k } else { return $d } }

$lastStatus   = St-Get "status" ""
$lastTicket   = St-Get "ticket" ""
$lastSig      = St-Get "sig" ""
$sigTime      = St-Get "sigTime" ""
$firstSeenMoi = St-Get "firstSeenMoi" ""
$warnedMoi    = [bool](St-Get "warnedMoi" $false)
$warnedStuck  = [bool](St-Get "warnedStuck" $false)

while ($true) {
    try {
        $text   = Get-MailboxFile "docs/phieu-viec/mailbox/trang-thai.md"
        $status = Parse-Field $text 'Trạng thái:\s*`([^`]+)`'
        $ticket = Parse-Field $text 'Ticket hiện tại:\s*([^\r\n]+)'
        $note   = Parse-Field $text '(?m)^\s*-\s*[Gg]hi ch[uú][:\s]`?([^`\r\n]+)'
        $commit = Parse-Field $text '[Cc]ommit[^:0-9a-f]*`?([0-9a-f]{7,40})`?'
        $sig    = "$status|$ticket|$note|$commit"
        $now    = Get-Date

        if ($sig -ne $lastSig) {
            $lastSig = $sig; $sigTime = $now.ToString("s"); $warnedStuck = $false
        }

        if ($status -eq "moi") {
            if ($ticket -ne $lastTicket -or $lastStatus -ne "moi") {
                try {
                    $prompt = Get-MailboxFile "docs/phieu-viec/mailbox/prompt.md"
                    $prompt | Out-File -FilePath $ticketFile -Encoding utf8
                } catch {}
                Show-Popup "Mailbox: ticket moi" ("Co ticket moi cho OMP:`n$ticket`n`nDa luu ban local: _ticket-moi.md`nBao OMP doc va lam theo prompt.")
                $firstSeenMoi = $now.ToString("s"); $warnedMoi = $false
            } elseif (-not $warnedMoi -and $firstSeenMoi -ne "") {
                $age = $now - [datetime]$firstSeenMoi
                if ($age.TotalMinutes -ge $moiWarnMinutes) {
                    Show-Popup "Mailbox: ticket treo" ("Ticket moi da hon $moiWarnMinutes phut chua ai nhan:`n$ticket`n`nNhac OMP: git pull origin $branch roi doc mailbox.")
                    $warnedMoi = $true
                }
            }
        }
        elseif ($status -eq "xong-cho-duyet" -and $status -ne $lastStatus) {
            Show-Popup "Mailbox: OMP bao xong" "OMP da bao xong-cho-duyet. Muse poll moi 5 phut se review ngay."
        }
        elseif ($status -eq "dang-lam" -and -not $warnedStuck -and $sigTime -ne "") {
            $idle = $now - [datetime]$sigTime
            if ($idle.TotalMinutes -ge $stuckMinutes) {
                Show-Popup "Mailbox: co ve ket" ("OMP dang-lam ticket nay hon $stuckMinutes phut khong tien trien:`n$ticket`n`nKiem tra terminal OMP xem co bi treo/khong.")
                $warnedStuck = $true
            }
        }
        elseif ($status -eq "xong" -and $status -ne $lastStatus) {
            Show-Popup "Mailbox: het viec" "Khong con ticket nao. Vong lap khep kin ket thuc."
        }

        $lastStatus = $status; $lastTicket = $ticket
        @{
            status = $status; ticket = $ticket; sig = $sig; sigTime = $sigTime
            firstSeenMoi = $firstSeenMoi; warnedMoi = $warnedMoi; warnedStuck = $warnedStuck
            updated = $now.ToString("s")
        } | ConvertTo-Json | Out-File $stateFile -Encoding utf8
    } catch {
        ("[{0}] loi: {1}" -f (Get-Date).ToString("s"), $_.Exception.Message) | Out-File $logFile -Append -Encoding utf8
    }
    Start-Sleep -Seconds $pollSeconds
}
