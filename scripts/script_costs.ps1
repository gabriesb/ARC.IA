# ==================================================
# RELATORIO BEDROCK AGENTCORE - OFICIAL
# ==================================================

# ---- CONFIGURACAO DO PERIODO (MENSAL) ----
$StartDate = "2025-12-01"
$EndDate   = "2025-12-31"

# ---- IDENTIFICACAO DO AGENT ----
$AgentName = "geo-agent"

# ---- ARQUIVO TEMPORARIO DE FILTRO ----
$FilterFile = "$PSScriptRoot\agentcore-filter.json"

Write-Host "=============================================="
Write-Host " RELATORIO BEDROCK AGENTCORE (OFICIAL)"
Write-Host " Periodo: $StartDate -> $EndDate"
Write-Host " Granularity: MONTHLY"
Write-Host "=============================================="
Write-Host ""

# ==================================================
# 1) FILTRO SOMENTE PARA BEDROCK AGENTCORE
# ==================================================
$Filter = @{
  Dimensions = @{
    Key    = "SERVICE"
    Values = @(
      "Bedrock AgentCore",
      "Amazon Bedrock AgentCore"
    )
  }
}

$FilterJson = $Filter | ConvertTo-Json -Depth 5

# Gravar JSON SEM BOM (obrigatorio para AWS CLI)
[System.IO.File]::WriteAllText(
  $FilterFile,
  $FilterJson,
  [System.Text.UTF8Encoding]::new($false)
)

# ==================================================
# 2) CUSTO TOTAL DO BEDROCK AGENTCORE
# ==================================================
$totalCost = aws ce get-cost-and-usage `
  --time-period Start=$StartDate,End=$EndDate `
  --granularity MONTHLY `
  --metrics UnblendedCost `
  --filter file://$FilterFile `
  --output json | ConvertFrom-Json

$totalAmount = $totalCost.ResultsByTime[0].Total.UnblendedCost.Amount

Write-Host "TOTAL Bedrock AgentCore: $totalAmount USD"
Write-Host ""

# ==================================================
# 3) CUSTO POR RUNTIME (TAG Runtime)
# ==================================================
$runtimeCost = aws ce get-cost-and-usage `
  --time-period Start=$StartDate,End=$EndDate `
  --granularity MONTHLY `
  --metrics UnblendedCost `
  --group-by Type=TAG,Key=Runtime `
  --filter file://$FilterFile `
  --output json | ConvertFrom-Json

$groups = $runtimeCost.ResultsByTime[0].Groups

# ==================================================
# 4) APRESENTACAO FINAL (SEM DUPLICACAO)
# ==================================================
if ($groups.Count -eq 0) {

  Write-Host "Custo por Runtime:"
  Write-Host "Nenhum runtime consolidado ainda."

}
elseif ($groups.Count -eq 1 -and $groups[0].Keys[0] -eq "Runtime$") {

  Write-Host "Custo por Runtime:"
  [PSCustomObject]@{
    Runtime = $AgentName
    CostUSD = $groups[0].Metrics.UnblendedCost.Amount
  } | Format-Table -AutoSize

}
else {

  Write-Host "Custo por Runtime:"
  $groups | ForEach-Object {
    [PSCustomObject]@{
      Runtime = $_.Keys[0]
      CostUSD = $_.Metrics.UnblendedCost.Amount
    }
  } | Format-Table -AutoSize

}
