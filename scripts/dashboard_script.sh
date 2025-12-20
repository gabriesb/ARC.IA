#!/usr/bin/env bash

REGION="us-west-2"

# Limite real do Cost Explorer (13 meses completos)
START_DATE=$(date -d "$(date +%Y-%m-01) -13 months" +%Y-%m-01)
END_DATE=$(date +%Y-%m-%d)

FILTER_FILE="./agentcore-filter.json"

cat > "$FILTER_FILE" <<EOF
{
  "Dimensions": {
    "Key": "SERVICE",
    "Values": [
      "Amazon Bedrock AgentCore",
      "Bedrock AgentCore"
    ]
  }
}
EOF

echo "=============================================="
echo " BEDROCK AGENTCORE - CUSTO"
echo " RegiÃ£o: $REGION"
echo " PerÃ­odo: $START_DATE â†’ $END_DATE"
echo "=============================================="
echo ""

DATA=$(aws ce get-cost-and-usage \
  --time-period Start=$START_DATE,End=$END_DATE \
  --granularity MONTHLY \
  --metrics UnblendedCost \
  --group-by Type=TAG,Key=Runtime \
  --filter file://$FILTER_FILE \
  --output json)

# --------------------------------------------------
# TOTAL REAL = SOMA DOS GRUPOS
# --------------------------------------------------
TOTAL=$(echo "$DATA" | jq '
  [
    .ResultsByTime[].Groups[].Metrics.UnblendedCost.Amount
    | select(. != null)
    | tonumber
  ] | add // 0
')

printf "í²° TOTAL AgentCore: %.6f USD\n\n" "$TOTAL"

printf "%-20s %s\n" "Runtime" "Cost USD"
printf "%-20s %s\n" "-------" "--------"

echo "$DATA" | jq -r '
  .ResultsByTime[].Groups[] |
  select(.Metrics.UnblendedCost.Amount != null) |
  "\(.Keys[0]) \(.Metrics.UnblendedCost.Amount)"
' | sort | uniq | while read -r runtime cost; do
    printf "%-20s %.6f\n" "$runtime" "$cost"
done
