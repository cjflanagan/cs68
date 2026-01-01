#!/bin/bash

echo "================================"
echo "NYC Events Android App Builder"
echo "================================"
echo ""

# Check for Android SDK
if [ -z "$ANDROID_HOME" ]; then
    echo "❌ ANDROID_HOME is not set!"
    echo ""
    echo "Please install Android Studio and set ANDROID_HOME:"
    echo "  export ANDROID_HOME=/path/to/Android/Sdk"
    echo "  export PATH=\$PATH:\$ANDROID_HOME/tools:\$ANDROID_HOME/platform-tools"
    echo ""
    echo "Or you can open this project in Android Studio and build from there."
    exit 1
fi

echo "✓ Android SDK found at: $ANDROID_HOME"
echo ""

# Check for Java
if ! command -v java &> /dev/null; then
    echo "❌ Java is not installed!"
    echo "Please install JDK 17 or higher."
    exit 1
fi

JAVA_VERSION=$(java -version 2>&1 | awk -F '"' '/version/ {print $2}' | cut -d'.' -f1)
echo "✓ Java version: $JAVA_VERSION"

if [ "$JAVA_VERSION" -lt 17 ]; then
    echo "⚠️  Warning: Java 17 or higher is recommended. You have version $JAVA_VERSION"
fi

echo ""
echo "Building APK..."
echo ""

# Make gradlew executable
chmod +x gradlew

# Build the APK
./gradlew assembleDebug

if [ $? -eq 0 ]; then
    echo ""
    echo "================================"
    echo "✅ BUILD SUCCESSFUL!"
    echo "================================"
    echo ""
    echo "APK Location: app/build/outputs/apk/debug/app-debug.apk"
    echo ""
    echo "To install on your device:"
    echo "  adb install app/build/outputs/apk/debug/app-debug.apk"
    echo ""
    echo "Or transfer the APK to your Android device and install manually."
else
    echo ""
    echo "================================"
    echo "❌ BUILD FAILED"
    echo "================================"
    echo ""
    echo "Please check the error messages above."
    echo "You can also try building in Android Studio for better error reporting."
    exit 1
fi
