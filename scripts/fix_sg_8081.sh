#!/usr/bin/env bash
# Fix Tencent Cloud Security Group to allow inbound TCP 8081
# Usage: bash scripts/fix_sg_8081.sh <SecretId> <SecretKey> [Region]
# Example: bash scripts/fix_sg_8081.sh AKIDxxxxx xxxxxxxx ap-guangzhou

set -e

SECRET_ID="${1:-}"
SECRET_KEY="${2:-}"
REGION="${3:-ap-guangzhou}"

if [[ -z "$SECRET_ID" || -z "$SECRET_KEY" ]]; then
    echo "Usage: $0 <SecretId> <SecretKey> [Region]"
    echo "Example: $0 AKIDxxxxx xxxxxxxx ap-guangzhou"
    exit 1
fi

# Configure tccli
tccli configure set secretId "$SECRET_ID"
tccli configure set secretKey "$SECRET_KEY"
tccli configure set region "$REGION"

# Find security groups for this instance
# First try metadata (only works inside Tencent Cloud)
SGID=$(curl -s --connect-timeout 3 "http://metadata.tencentyun.com/latest/meta-data/security-groups" 2>/dev/null | head -1 || true)

if [[ -z "$SGID" ]]; then
    echo "Metadata not available, querying security groups via API..."
    SGID=$(tccli cvm DescribeSecurityGroups --region "$REGION" \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['SecurityGroupSet'][0]['SecurityGroupId'])")
fi

echo "Using SecurityGroup: $SGID"

# Authorize port 8081 inbound
tccli cvm CreateSecurityGroupPolicies \
    --region "$REGION" \
    --SecurityGroupId "$SGID" \
    --SecurityGroupPolicySet '{
        "Ingress": [{
            "PolicyIndex": 0,
            "Protocol": "tcp",
            "Port": "8081",
            "Action": "ACCEPT",
            "CidrBlock": "0.0.0.0/0",
            "PolicyDescription": "worker-bee gateway"
        }]
    }'

echo "Done. Port 8081 is now open on $SGID"
