# How to Get Your APK

Since the build environment doesn't have network access to download Android dependencies, here are your options to build the APK:

## Option 1: GitHub Actions (Automated - Easiest) ⭐

I've set up a GitHub Actions workflow that will automatically build your APK in the cloud!

### Steps:
1. **Push this code to GitHub** (already done!)
2. **Go to your GitHub repository**: https://github.com/cjflanagan/cs68
3. **Click the "Actions" tab** at the top
4. **Click "Build Android APK"** workflow on the left
5. **Click "Run workflow"** button (green button on the right)
6. **Wait 3-5 minutes** for the build to complete
7. **Download your APK**:
   - Click on the completed workflow run
   - Scroll down to "Artifacts"
   - Download "nyc-events-app-debug"
   - Unzip the file to get `app-debug.apk`

**That's it!** Transfer the APK to your Android device and install.

---

## Option 2: Build Locally with Android Studio

If you have Android Studio installed:

1. **Open Android Studio**
2. **File → Open** → Select the `NYCEventsApp` folder
3. **Wait for Gradle sync** (2-3 minutes first time)
4. **Build → Build Bundle(s) / APK(s) → Build APK(s)**
5. **APK location**: `app/build/outputs/apk/debug/app-debug.apk`

---

## Option 3: Command Line (If you have Android SDK)

```bash
cd NYCEventsApp

# Make sure ANDROID_HOME is set
export ANDROID_HOME=/path/to/Android/Sdk
export PATH=$PATH:$ANDROID_HOME/platform-tools

# Build
./gradlew assembleDebug

# Find APK at:
# app/build/outputs/apk/debug/app-debug.apk
```

---

## Option 4: Docker Build

If you have Docker installed:

```bash
cd NYCEventsApp
./docker-build.sh
```

First build takes 10-15 minutes (downloads Android SDK).

---

## Installing the APK on Your Phone

### Method A: USB Cable
```bash
# Enable USB debugging on your phone first
adb install app-debug.apk
```

### Method B: Manual Transfer
1. Transfer `app-debug.apk` to your phone (email, cloud, USB, etc.)
2. On your phone: **Settings → Security → Install from Unknown Sources** (enable)
3. Open the APK file with a file manager
4. Tap **Install**

---

## Recommended: GitHub Actions

**GitHub Actions is the easiest option** because:
- No local setup required
- No Android SDK installation needed
- No dependencies to download
- Builds automatically in the cloud
- Takes just a few clicks

Just go to your GitHub repository's Actions tab and run the workflow!

---

## Quick Troubleshooting

**GitHub Actions not showing?**
- Make sure the code is pushed to GitHub
- The workflow file is in `.github/workflows/build-android-apk.yml`
- You may need to enable Actions in repository settings

**Local build failing?**
- Check that you have Android SDK installed
- Verify `ANDROID_HOME` environment variable is set
- Make sure you have JDK 17 or higher
- Run `./gradlew clean` then try again

**APK won't install on phone?**
- Enable "Install from Unknown Sources" in Settings
- Make sure your phone is Android 7.0 or newer
- Try uninstalling any existing version first

---

## Need Help?

See the detailed guides:
- [README.md](README.md) - Overview and features
- [INSTALLATION.md](INSTALLATION.md) - Comprehensive installation guide
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - Technical details
