#!/bin/bash
# Builds "AlphaGo Lite.app" into MacApp/build/.
#   MacApp/scripts/build_app.sh            release build
#   MacApp/scripts/build_app.sh --open     build, then launch
# Needs MacApp/Resources/{AlphaGoLite.mlpackage,metrics.json,games.json}
# (written by: cd trainer && .venv/bin/python -m alphago_lite.export_app).
set -euo pipefail
cd "$(dirname "$0")/.."

APP="build/AlphaGo Lite.app"
RES="Resources"

swift build -c release --product AlphaGoLite
BIN="$(swift build -c release --show-bin-path)/AlphaGoLite"

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$BIN" "$APP/Contents/MacOS/AlphaGoLite"

if [ -d "$RES/AlphaGoLite.mlpackage" ]; then
  xcrun coremlcompiler compile "$RES/AlphaGoLite.mlpackage" "$APP/Contents/Resources/" >/dev/null
else
  echo "warning: no $RES/AlphaGoLite.mlpackage — the app will fall back to a uniform policy" >&2
fi
for f in metrics.json games.json AppIcon.icns; do
  [ -f "$RES/$f" ] && cp "$RES/$f" "$APP/Contents/Resources/"
done

VERSION="$(cat VERSION 2>/dev/null || echo 1.0)"
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>AlphaGo Lite</string>
  <key>CFBundleDisplayName</key><string>AlphaGo Lite</string>
  <key>CFBundleIdentifier</key><string>com.amalmehta.AlphaGoLite</string>
  <key>CFBundleExecutable</key><string>AlphaGoLite</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>${VERSION}</string>
  <key>CFBundleVersion</key><string>${VERSION}</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>LSMinimumSystemVersion</key><string>14.0</string>
  <key>LSApplicationCategoryType</key><string>public.app-category.board-games</string>
  <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST

codesign --force --deep --sign - "$APP" >/dev/null 2>&1 || true
echo "Built $(pwd)/$APP"
[ "${1:-}" = "--open" ] && open "$APP"
exit 0
