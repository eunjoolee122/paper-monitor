function Mask($v) {
    if ($v) { 'set len=' + $v.Length + ' prefix=' + $v.Substring(0,[Math]::Min(7,$v.Length)) + '...' }
    else { 'NOT set' }
}
Write-Host ('User    : ' + (Mask ([Environment]::GetEnvironmentVariable('ANTHROPIC_API_KEY','User'))))
Write-Host ('Machine : ' + (Mask ([Environment]::GetEnvironmentVariable('ANTHROPIC_API_KEY','Machine'))))
Write-Host ('Process : ' + (Mask $env:ANTHROPIC_API_KEY))
