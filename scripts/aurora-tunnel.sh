#!/bin/bash
# Aurora SSM Tunnel Helper Script
# Usage: ./scripts/aurora-tunnel.sh

set -e

echo "🔌 Starting SSM tunnel to Aurora (dev environment)..."
echo ""
echo "Instance: i-0dab21bdf83ce9aaf (rag-chatbot bastion)"
echo "Local port: 3307"
echo "Remote: Aurora cluster"
echo ""
echo "⚠️  This will run in FOREGROUND. Open a new terminal to run commands."
echo "   Or press Ctrl+Z then 'bg' to background it."
echo ""

ENV=dev doppler run -- aws ssm start-session \
  --target i-0dab21bdf83ce9aaf \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters '{
    "host":["dr-daily-report-aurora-dev.cluster-c9a0288e4hqm.ap-southeast-1.rds.amazonaws.com"],
    "portNumber":["3306"],
    "localPortNumber":["3307"]
  }'
