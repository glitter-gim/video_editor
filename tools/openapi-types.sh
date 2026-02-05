#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
OUT_DIR="$ROOT_DIR/app/web/src/api"
OUT_FILE="$OUT_DIR/schema.ts"

mkdir -p "$OUT_DIR"

npx -y openapi-typescript "https://vedit.glitter.kr/openapi.json" -o "$OUT_FILE"
