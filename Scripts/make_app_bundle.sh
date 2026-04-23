#!/bin/bash
APP_NAME="PoISLAM"
BUILD_DIR="build_macos"
APP_BUNDLE="$BUILD_DIR/$APP_NAME.app"
CONTENTS="$APP_BUNDLE/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"

mkdir -p "$MACOS"
mkdir -p "$RESOURCES"

# 1. バイナリとWASMの配置
cp "$BUILD_DIR/PoISLAMApp" "$MACOS/$APP_NAME"
cp "Web/poi.wasm" "$MACOS/"
cp "Web/poi.wasm" "$RESOURCES/"
cp "$BUILD_DIR/default.metallib" "$RESOURCES/"

# 2. Info.plist の作成 (カメラ権限に必須)
cat <<EOF > "$CONTENTS/Info.plist"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>$APP_NAME</string>
    <key>CFBundleIdentifier</key>
    <string>com.poi.slam.prototype</string>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>NSCameraUsageDescription</key>
    <string>PoI-SLAM uses the camera to perceive physical structures in the world.</string>
</dict>
</plist>
EOF

echo "Successfully created $APP_BUNDLE"
