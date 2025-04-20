#!/usr/bin/env bash
set -euo pipefail
: "${HF_TOKEN:?HF_TOKEN env var must be set}"

kubectl create secret generic hf-secret \
  --from-literal=hf_api_token="$HF_TOKEN" \
  --namespace default \
  --dry-run=client -o yaml | kubectl apply -f -