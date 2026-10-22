#!/usr/bin/env bash
# Run one task in one arm, headless, in a fresh git-initialised folder.
# Usage: bench/run.sh TASK ARM RUNS_DIR [MODEL]
#   ARM: off (no plugin) | on (this repo loaded with --plugin-dir)
# User-level settings, hooks, plugins and CLAUDE.md are skipped with
# --setting-sources project,local so both arms see the same bare session.
set -euo pipefail
task=$1 arm=$2 runs=$3 model=${4:-best}
bench=$(cd "$(dirname "$0")" && pwd)
plugin=$(dirname "$bench")
dir="$runs/$task-$arm"
rm -rf "$dir" && mkdir -p "$dir"
git -C "$dir" init -q  # bounds the ledger search to this folder

extra=()
[ "$arm" = on ] && extra=(--plugin-dir "$plugin")

start=$(date +%s)
(cd "$dir" && claude -p "$(cat "$bench/tasks/$task/prompt.md")" \
  --model "$model" --setting-sources project,local \
  --permission-mode bypassPermissions --max-budget-usd 10 \
  --output-format stream-json --verbose ${extra[@]+"${extra[@]}"}) \
  > "$runs/$task-$arm.jsonl" 2> "$runs/$task-$arm.stderr" || true
echo $(( $(date +%s) - start )) > "$runs/$task-$arm.wall"
