#!/usr/bin/env bash
# Build, push and deploy each destination (config/deploy.<name>.yml).
#   ./deploy-all.sh
set -euo pipefail
cd "$(dirname "$0")"

destinations=()
for file in config/deploy.*.yml; do
  name="${file#config/deploy.}"
  destinations+=("${name%.yml}")
done
if [[ ${#destinations[@]} -eq 0 ]]; then
  echo "No destinations found in config/deploy.*.yml" >&2
  exit 1
fi

echo "Destinations: ${destinations[*]}"
for destination in "${destinations[@]}"; do
  echo "=== Deploying $destination ==="
  kamal deploy -d "$destination"
done
