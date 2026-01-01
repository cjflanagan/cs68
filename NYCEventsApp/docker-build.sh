#!/bin/bash

echo "================================"
echo "NYC Events - Docker Build"
echo "================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed!"
    echo ""
    echo "Please install Docker from: https://docs.docker.com/get-docker/"
    exit 1
fi

echo "✓ Docker found"
echo ""
echo "Building Docker image..."
echo ""

# Build Docker image
docker build -t nyc-events-builder .

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Docker image build failed!"
    exit 1
fi

echo ""
echo "✓ Docker image built successfully"
echo ""
echo "Building APK in Docker container..."
echo ""

# Run container and build APK
docker run --rm -v "$(pwd)/app/build:/app/app/build" nyc-events-builder

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
else
    echo ""
    echo "❌ Build failed in Docker container"
    exit 1
fi
