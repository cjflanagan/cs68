# NYC Events - Installation Guide

This guide provides multiple methods to build and install the NYC Events Android app.

## Table of Contents

1. [Quick Start - Android Studio](#method-1-android-studio-easiest)
2. [Command Line Build](#method-2-command-line-build)
3. [Docker Build](#method-3-docker-build-no-android-sdk-needed)
4. [Online Build Services](#method-4-online-build-services)
5. [Installation on Device](#installation-on-device)
6. [Troubleshooting](#troubleshooting)

---

## Method 1: Android Studio (Easiest)

This is the recommended method for most users.

### Prerequisites
- [Android Studio](https://developer.android.com/studio) (latest version)

### Steps

1. **Download and Install Android Studio**
   - Visit https://developer.android.com/studio
   - Download for your operating system
   - Install and run Android Studio
   - During first run, let it download the Android SDK components

2. **Open the Project**
   - Launch Android Studio
   - Click "Open" or "Open an Existing Project"
   - Navigate to the `NYCEventsApp` folder and select it
   - Click "OK"

3. **Wait for Gradle Sync**
   - Android Studio will automatically sync Gradle
   - This may take a few minutes on first run
   - Wait for the "Gradle sync completed" message

4. **Build the APK**
   - Click **Build** menu → **Build Bundle(s) / APK(s)** → **Build APK(s)**
   - Wait for build to complete
   - Click "locate" in the popup to find your APK
   - Or find it at: `app/build/outputs/apk/debug/app-debug.apk`

5. **Done!**
   - Transfer the APK to your Android device and install
   - Or use "Run" in Android Studio to install on a connected device

---

## Method 2: Command Line Build

For users comfortable with terminal/command line.

### Prerequisites
- JDK 17 or higher
- Android SDK installed
- ANDROID_HOME environment variable set

### Steps

1. **Install JDK 17**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install openjdk-17-jdk

   # macOS (using Homebrew)
   brew install openjdk@17

   # Windows
   # Download from: https://adoptium.net/
   ```

2. **Install Android SDK**
   ```bash
   # Option 1: Install Android Studio (includes SDK)
   # Option 2: Install command-line tools only
   # Download from: https://developer.android.com/studio#command-tools
   ```

3. **Set Environment Variables**
   ```bash
   # Add to ~/.bashrc or ~/.zshrc (Linux/Mac)
   export ANDROID_HOME=$HOME/Android/Sdk
   export PATH=$PATH:$ANDROID_HOME/tools
   export PATH=$PATH:$ANDROID_HOME/platform-tools

   # Windows (Command Prompt)
   setx ANDROID_HOME "C:\Users\YourUsername\AppData\Local\Android\Sdk"
   ```

4. **Build the APK**
   ```bash
   cd NYCEventsApp

   # Use the build script
   ./build.sh

   # Or use Gradle directly
   ./gradlew assembleDebug
   ```

5. **Find Your APK**
   - Location: `app/build/outputs/apk/debug/app-debug.apk`

---

## Method 3: Docker Build (No Android SDK Needed)

Perfect if you don't want to install Android SDK on your machine.

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) installed

### Steps

1. **Install Docker**
   ```bash
   # Ubuntu
   sudo apt-get update
   sudo apt-get install docker.io
   sudo systemctl start docker
   sudo systemctl enable docker

   # macOS/Windows
   # Download Docker Desktop from: https://www.docker.com/products/docker-desktop
   ```

2. **Build Using Docker**
   ```bash
   cd NYCEventsApp

   # Run the Docker build script
   ./docker-build.sh
   ```

3. **Wait for Build**
   - First run will take 10-15 minutes (downloading Android SDK)
   - Subsequent builds will be faster

4. **Find Your APK**
   - Location: `app/build/outputs/apk/debug/app-debug.apk`

---

## Method 4: Online Build Services

If you can't build locally, use online services:

### GitHub Actions (Recommended)

1. **Fork the Repository**
   - Upload the project to GitHub
   - Fork or create a new repository

2. **Create GitHub Actions Workflow**
   - Create `.github/workflows/build.yml`:
   ```yaml
   name: Android Build

   on: [push, workflow_dispatch]

   jobs:
     build:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - uses: actions/setup-java@v3
           with:
             java-version: '17'
             distribution: 'adopt'
         - name: Build APK
           run: |
             chmod +x gradlew
             ./gradlew assembleDebug
         - name: Upload APK
           uses: actions/upload-artifact@v3
           with:
             name: app-debug
             path: app/build/outputs/apk/debug/app-debug.apk
   ```

3. **Trigger Build**
   - Push to GitHub or manually trigger workflow
   - Download APK from "Actions" tab → "Artifacts"

### Appetize.io
- Upload project to https://appetize.io
- Build and test in browser
- Download APK

---

## Installation on Device

### Method A: ADB (USB)

1. **Enable Developer Options**
   - Go to Settings → About Phone
   - Tap "Build Number" 7 times
   - Go back to Settings → Developer Options
   - Enable "USB Debugging"

2. **Connect Device**
   ```bash
   # Check device is connected
   adb devices

   # Install APK
   adb install app/build/outputs/apk/debug/app-debug.apk

   # If app already installed, use -r to replace
   adb install -r app/build/outputs/apk/debug/app-debug.apk
   ```

### Method B: Manual Transfer

1. **Transfer APK**
   - Copy `app-debug.apk` to your phone
   - Use USB, email, cloud storage, etc.

2. **Install APK**
   - On your phone, go to Settings → Security
   - Enable "Install from Unknown Sources" or "Install Unknown Apps"
   - Use a file manager to find the APK
   - Tap to install

### Method C: Wireless ADB

1. **Enable Wireless Debugging** (Android 11+)
   - Settings → Developer Options → Wireless Debugging
   - Tap "Pair device with pairing code"

2. **Pair and Connect**
   ```bash
   # Pair (use code from phone)
   adb pair <IP>:<PORT>

   # Connect
   adb connect <IP>:<PORT>

   # Install
   adb install app-debug.apk
   ```

---

## Troubleshooting

### Build Issues

**"ANDROID_HOME is not set"**
```bash
# Find your SDK location
# Usually: ~/Android/Sdk (Linux/Mac) or C:\Users\<you>\AppData\Local\Android\Sdk (Windows)

# Set it
export ANDROID_HOME=/path/to/android/sdk
export PATH=$PATH:$ANDROID_HOME/platform-tools
```

**"Unsupported Java version"**
```bash
# Check Java version
java -version

# Should be 17 or higher. Install JDK 17 if needed.
```

**"SDK not found"**
```bash
# Install SDK platform and build tools
sdkmanager "platforms;android-34" "build-tools;34.0.0"
```

**"Gradle build failed"**
```bash
# Clean and rebuild
./gradlew clean
./gradlew assembleDebug --stacktrace
```

### Installation Issues

**"App not installed"**
- Enable "Install from Unknown Sources" in Settings
- Make sure you have enough storage space
- Try uninstalling any existing version first

**"Parse error"**
- Make sure you're installing on Android 7.0 (API 24) or higher
- APK file might be corrupted, rebuild it

**"ADB device not found"**
```bash
# Restart ADB server
adb kill-server
adb start-server
adb devices
```

### Runtime Issues

**"No events showing"**
- Check internet connection
- App will show sample events if API fails
- Wait a few seconds for data to load

**"App crashes on startup"**
- Check Android version (minimum 7.0)
- Check logcat for errors: `adb logcat | grep nycevents`
- Reinstall the app

---

## Support

For issues or questions:
1. Check the [README.md](README.md)
2. Review error messages carefully
3. Search for error messages online
4. Check Android Studio's "Build" output for details

---

## Quick Reference

**File Locations:**
- APK output: `app/build/outputs/apk/debug/app-debug.apk`
- Source code: `app/src/main/java/com/nycevents/`
- Layouts: `app/src/main/res/layout/`
- Manifest: `app/src/main/AndroidManifest.xml`

**Common Commands:**
```bash
# Build
./gradlew assembleDebug

# Clean
./gradlew clean

# Install
adb install app/build/outputs/apk/debug/app-debug.apk

# View logs
adb logcat | grep nycevents

# Check devices
adb devices
```
