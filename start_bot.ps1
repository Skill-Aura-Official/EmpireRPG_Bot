while ($true) {
    Write-Host "--------------------------------------------------"
    Write-Host "Starting MythicRPG Bot at $(Get-Date)..."
    Write-Host "--------------------------------------------------"
    python -m MythicRPG
    Write-Host "--------------------------------------------------"
    Write-Host "Bot stopped or crashed at $(Get-Date)."
    Write-Host "Restarting in 10 seconds... (Press Ctrl+C to stop the loop)"
    Write-Host "--------------------------------------------------"
    Start-Sleep -Seconds 10
}
