#!/usr/bin/env bash

# ==================================================
# RELATORIO BEDROCK AGENTCORE - OFICIAL
# ==================================================

# ---- CONFIGURACAO DO PERIODO (MENSAL) ----
START_DATE="2025-12-01"
END_DATE="2025-12-31"

# ---- IDENTIFICACAO DO AGENT ----
AGENT_NAME="geo-agent"

# ---- ARQUIVO TEMPORARIO DE FILTRO ----
FILTER_FILE="./agentcore-filter.json"

echo "=============================================="
echo " RELATORIO BEDROCK AGENTCORE (OFICIAL)"
echo " Periodo: $START_DATE -> $END_DATE"
echo " Granularity: MONTHLY"
echo "=============================================="
echo ""

# ==================================================
# 1) FILTRO SOMENTE PARA BEDROCK AGENTCORE
# ==================================================
cat > "$FILTER_FILE" <<EOF
{
  "Dimensions": {
    "Key": "SERVICE",
    "Values": [
      "Bedrock AgentCore",
      "Amazon Bedrock AgentCore"
    ]
  }
}
EOF

# ==================================================
# 2) CUSTO TOTAL DO BEDROCK AGENTCORE
# ==================================================
TOTAL_COST=$(aws ce get-cost-and-usage \
  --time-period Start=$START_DATE,End=$END_DATE \
  --granularity MONTHLY \
  --metrics UnblendedCost \
  --filter file://$FILTER_FILE \
  --query "ResultsByTime[0].Total.UnblendedCost.Amount" \
  --output text)

echo "TOTAL Bedrock AgentCore: $TOTAL_COST USD"
echo ""

# ==================================================
# 3) CUSTO POR RUNTIME (TAG Runtime)
# ==================================================
RUNTIME_JSON=$(aws ce get-cost-and-usage \
  --time-period Start=$START_DATE,End=$END_DATE \
  --granularity MONTHLY \
  --metrics UnblendedCost \
  --group-by Type=TAG,Key=Runtime \
  --filter file://$FILTER_FILE \
  --output json)

GROUP_COUNT=$(echo "$RUNTIME_JSON" | jq '.ResultsByTime[0].Groups | length')

echo "Custo por Runtime:"

# ==================================================
# 4) APRESENTACAO FINAL (SEM DUPLICACAO)
# ==================================================
if [ "$GROUP_COUNT" -eq 0 ]; then

  echo "Nenhum runtime consolidado ainda."

elif [ "$GROUP_COUNT" -eq 1 ] && \
     [ "$(echo "$RUNTIME_JSON" | jq -r '.ResultsByTime[0].Groups[0].Keys[0]')" = "Runtime$" ]; then

  COST=$(echo "$RUNTIME_JSON" | jq -r '.ResultsByTime[0].Groups[0].Metrics.UnblendedCost.Amount')

  printf "%-10s %s\n" "Runtime" "CostUSD"
  printf "%-10s %s\n" "-------" "-------"
  printf "%-10s %s\n" "$AGENT_NAME" "$COST"

else

  printf "%-20s %s\n" "Runtime" "CostUSD"
  printf "%-20s %s\n" "-------" "-------"

  echo "$RUNTIME_JSON" | jq -r '
    .ResultsByTime[0].Groups[] |
    "\(.Keys[0]) \(.Metrics.UnblendedCost.Amount)"
  ' | while read -r runtime cost; do
      printf "%-20s %s\n" "$runtime" "$cost"
    done
fi
