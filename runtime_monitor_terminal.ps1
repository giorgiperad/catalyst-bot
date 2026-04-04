param(
    [string]$ApiUrl = "http://127.0.0.1:5000/api/diagnostics/runtime"
)

$Host.UI.RawUI.WindowTitle = "Chia Market Maker Runtime Monitor"

function Format-Value {
    param([object]$Value)
    if ($null -eq $Value -or $Value -eq "") { return "-" }
    return [string]$Value
}

function Format-Ago {
    param([object]$Value)
    if ($null -eq $Value -or $Value -eq "") { return "-" }
    try {
        $num = [double]$Value
        return ("{0:N1}s ago" -f $num)
    } catch {
        return [string]$Value
    }
}

function Write-Line {
    param(
        [string]$Label,
        [string]$Value,
        [ConsoleColor]$Color = [ConsoleColor]::Gray
    )
    Write-Host ($Label.PadRight(18)) -NoNewline -ForegroundColor DarkGray
    Write-Host $Value -ForegroundColor $Color
}

Write-Host ""
Write-Host "Chia Market Maker Runtime Monitor" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to close this monitor window." -ForegroundColor DarkGray

while ($true) {
    try {
        $data = Invoke-RestMethod -Uri $ApiUrl -TimeoutSec 8
        Clear-Host

        $status = Format-Value $data.status
        $statusColor = switch ($status) {
            "healthy" { [ConsoleColor]::Green }
            "warning" { [ConsoleColor]::Yellow }
            "warming_up" { [ConsoleColor]::Yellow }
            "critical" { [ConsoleColor]::Red }
            "error" { [ConsoleColor]::Red }
            default { [ConsoleColor]::Cyan }
        }

        Write-Host "Chia Market Maker Runtime Monitor" -ForegroundColor Cyan
        Write-Host ("Updated {0}" -f (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")) -ForegroundColor DarkGray
        Write-Host ""

        Write-Line "Status" $status $statusColor
        Write-Line "Note" (Format-Value $data.note) White
        Write-Line "Poll" ("{0}s" -f (Format-Value $data.poll_interval_secs)) DarkCyan
        Write-Host ""

        $market = $data.market
        $coins = $data.coins
        $bot = $data.bot
        $perf = $data.performance

        Write-Host "Market Alignment" -ForegroundColor White
        Write-Line "Wallet" ("{0} / {1}" -f (Format-Value $market.wallet_buy), (Format-Value $market.wallet_sell)) White
        Write-Line "DB" ("{0} / {1}" -f (Format-Value $market.db_buy), (Format-Value $market.db_sell)) White
        Write-Line "Dexie" ("{0} / {1}" -f (Format-Value $market.dexie_our_buy), (Format-Value $market.dexie_our_sell)) White
        Write-Line "Dexie Total" ("{0} / {1}" -f (Format-Value $market.dexie_total_buy), (Format-Value $market.dexie_total_sell)) Gray
        Write-Line "Best Bid" (Format-Value $market.best_competitor_bid) DarkCyan
        Write-Line "Best Ask" (Format-Value $market.best_competitor_ask) DarkCyan
        Write-Line "Bid Gap" ("{0} bps" -f (Format-Value $market.our_bid_gap_bps)) Gray
        Write-Line "Ask Gap" ("{0} bps" -f (Format-Value $market.our_ask_gap_bps)) Gray
        Write-Line "Book Age" ("{0}s" -f (Format-Value $market.orderbook_age_secs)) Gray
        Write-Host ""

        Write-Host "Coin State" -ForegroundColor White
        Write-Line "XCH Free" (Format-Value $coins.xch_free) Green
        Write-Line "CAT Free" (Format-Value $coins.cat_free) Green
        Write-Line "XCH Locked" (Format-Value $coins.xch_locked) Yellow
        Write-Line "CAT Locked" (Format-Value $coins.cat_locked) Yellow
        Write-Line "Coin Prep" ($(if ($coins.prep_running) { "Running" } else { "Idle" })) Gray
        Write-Line "Top-Up" ($(if ($coins.topup_running) { "Running" } else { "Idle" })) Gray
        Write-Host ""

        Write-Host "Bot Activity" -ForegroundColor White
        Write-Line "Loop Count" (Format-Value $bot.loop_count) White
        Write-Line "Loop Time" ("{0}s" -f (Format-Value $bot.loop_duration_secs)) White
        Write-Line "Mid Price" (Format-Value $bot.mid_price) DarkCyan
        Write-Line "Last Post" (Format-Ago $bot.last_post_activity_secs_ago) Gray
        Write-Line "Last Fill" (Format-Ago $bot.last_fill_activity_secs_ago) Gray
        Write-Line "Slow Calls" (Format-Value (($perf.active_methods | Measure-Object).Count)) Yellow
        Write-Host ""

        Write-Host "Active Conditions" -ForegroundColor White
        if ($data.active_conditions -and $data.active_conditions.Count -gt 0) {
            foreach ($cond in $data.active_conditions) {
                Write-Host (" - {0}" -f (Format-Value $cond.message)) -ForegroundColor Yellow
            }
        } else {
            Write-Host " - No active warnings" -ForegroundColor Green
        }
        Write-Host ""

        Write-Host "Recent Findings" -ForegroundColor White
        if ($data.recent_findings -and $data.recent_findings.Count -gt 0) {
            foreach ($row in ($data.recent_findings | Select-Object -First 5)) {
                Write-Host (" - [{0}] {1}" -f (Format-Value $row.severity).ToUpper(), (Format-Value $row.message)) -ForegroundColor Gray
            }
        } else {
            Write-Host " - None" -ForegroundColor DarkGray
        }
        Write-Host ""

        Write-Host "Recent Actions" -ForegroundColor White
        if ($data.recent_actions -and $data.recent_actions.Count -gt 0) {
            foreach ($row in ($data.recent_actions | Select-Object -First 6)) {
                Write-Host (" - [{0}] {1}: {2}" -f (Format-Value $row.severity).ToUpper(), (Format-Value $row.event_type), (Format-Value $row.message)) -ForegroundColor Gray
            }
        } else {
            Write-Host " - None yet" -ForegroundColor DarkGray
        }
    } catch {
        Clear-Host
        Write-Host "Chia Market Maker Runtime Monitor" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Could not reach the runtime diagnostics endpoint." -ForegroundColor Red
        Write-Host ("URL: {0}" -f $ApiUrl) -ForegroundColor DarkGray
        Write-Host ("Error: {0}" -f $_.Exception.Message) -ForegroundColor DarkGray
        Write-Host ""
        Write-Host "Retrying..." -ForegroundColor Yellow
    }

    Start-Sleep -Seconds 2
}
