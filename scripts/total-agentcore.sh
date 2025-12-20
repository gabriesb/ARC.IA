#!/usr/bin/env bash

REGION="us-west-2"

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
echo " BEDROCK AGENTCORE - TOTAL GASTO NA CONTA"
echo " Região: $REGION"
echo " Período: $START_DATE → $END_DATE"
echo "=============================================="
echo ""

DATA=$(aws ce get-cost-and-usage \
  --time-period Start=$START_DATE,End=$END_DATE \
  --granularity MONTHLY \
  --metrics UnblendedCost \
  --filter file://$FILTER_FILE \
  --output json)

TOTAL=$(echo "$DATA" | jq '
  [
    .ResultsByTime[].Total.UnblendedCost.Amount
    | select(. != null)
    | tonumber
  ] | add // 0
')

printf "TOTAL AgentCore: %.6f USD\n" "$TOTAL"
