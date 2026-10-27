#!/bin/sh
# Uploads site/ to the placebo.wiki bucket. Text files go up gzip-compressed (Content-Encoding: gzip);
# CSS, JS and SVG need explicit types or browsers refuse them; pages revalidate on every visit,
# the font is cached for a year. Not uploaded: old prototypes, the personal list (data.js),
# and top.json, which belongs to the placebo-top cloud function.
set -e
Y="${YC:-$HOME/yandex-cloud/bin/yc}"
SITE="$(cd "$(dirname "$0")/../site" && pwd)"
STAGE="$(mktemp -d)"
python3 "$SITE/../data/build_stats.py"
trap 'rm -rf "$STAGE"' EXIT
rsync -a --exclude data.js --exclude app.js --exclude 'story.*' --exclude style.css --exclude welcome.html --exclude map.html --exclude top.json --exclude mock "$SITE/" "$STAGE/"
find "$STAGE" -type f \( -name '*.html' -o -name '*.css' -o -name '*.js' -o -name '*.json' -o -name '*.xml' -o -name '*.svg' -o -name '*.txt' \) -exec gzip -9 -n {} \; -exec sh -c 'mv "$1.gz" "$1"' _ {} \;
NC="no-cache"
up() { "$Y" storage s3 cp --recursive "$STAGE/" s3://placebo.wiki/ --exclude "*" "$@" >/dev/null; }
up --include "*.html" --content-type "text/html; charset=utf-8" --content-encoding gzip --cache-control "$NC"
up --include "*.xml" --content-type "application/xml; charset=utf-8" --content-encoding gzip --cache-control "$NC"
up --include "*.txt" --content-type "text/plain; charset=utf-8" --content-encoding gzip --cache-control "$NC"
up --include "*.json" --content-type "application/json; charset=utf-8" --content-encoding gzip --cache-control "$NC"
up --include "*.css" --content-type "text/css; charset=utf-8" --content-encoding gzip --cache-control "$NC"
up --include "*.js" --content-type "application/javascript; charset=utf-8" --content-encoding gzip --cache-control "$NC"
up --include "*.svg" --content-type "image/svg+xml" --content-encoding gzip --cache-control "$NC"
up --include "*.woff2" --content-type "font/woff2" --cache-control "public, max-age=31536000, immutable"
up --include "*.png" --include "*.ico" --cache-control "public, max-age=86400"
python3 "$(dirname "$0")/ping_index.py" || echo "indexnow: пропущен"
echo "deployed"
