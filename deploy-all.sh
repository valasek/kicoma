#!/usr/bin/env bash
# Build and push the image once, then deploy it to every destination (config/deploy.<name>.yml).
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
kamal build push -d "${destinations[0]}"
for destination in "${destinations[@]}"; do
  echo "=== Deploying $destination ==="
  kamal deploy -d "$destination" --skip-push
done
