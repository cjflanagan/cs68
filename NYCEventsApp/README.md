# NYC Events - Non-Touristy Events Finder

An Android app that discovers fun, non-touristy events happening in NYC in the next week.

## Features

- **Custom Insights**: Each event is tagged with custom insights to help you understand what makes it special
  - 🏘️ Local neighborhood spots
  - 👥 Community events
  - 🎨 Arts & culture
  - 🍴 Food scene
  - 🌳 Outdoor activities
  - 🌙 Nightlife
  - 💰 Free events

- **Smart Filtering**: Automatically filters out touristy attractions like Times Square tours, Statue of Liberty, etc.

- **NYC Open Data Integration**: Uses the official NYC Open Data API to fetch real-time events

- **Next Week Focus**: Only shows events happening in the next 7 days

- **Beautiful UI**: Material Design 3 with card-based layout

## Technology Stack

- **Language**: Kotlin
- **UI**: Material Design 3, RecyclerView, ConstraintLayout
- **Networking**: Retrofit 2, OkHttp
- **Async**: Kotlin Coroutines
- **Architecture**: MVVM pattern with lifecycle-aware components

## Building the APK

### Prerequisites

1. Android Studio (latest version recommended)
2. Android SDK 34
3. JDK 17 or higher
4. Gradle 8.1

### Build Instructions

#### Option 1: Android Studio (Recommended)

1. Open Android Studio
2. Select "Open an existing project"
3. Navigate to the `NYCEventsApp` folder
4. Wait for Gradle sync to complete
5. Click "Build" → "Build Bundle(s) / APK(s)" → "Build APK(s)"
6. The APK will be located at: `app/build/outputs/apk/debug/app-debug.apk`

#### Option 2: Command Line

```bash
cd NYCEventsApp

# Make gradlew executable (Unix/Linux/Mac)
chmod +x gradlew

# Build debug APK
./gradlew assembleDebug

# The APK will be at: app/build/outputs/apk/debug/app-debug.apk
```

#### Option 3: Release Build (Signed)

```bash
# Build release APK
./gradlew assembleRelease

# The APK will be at: app/build/outputs/apk/release/app-release.apk
```

### Installation

After building, install the APK on your Android device:

```bash
# Connect your Android device via USB with USB debugging enabled
adb install app/build/outputs/apk/debug/app-debug.apk
```

Or transfer the APK file to your device and install it manually.

## Project Structure

```
NYCEventsApp/
├── app/
│   ├── build.gradle
│   └── src/
│       └── main/
│           ├── AndroidManifest.xml
│           ├── java/com/nycevents/
│           │   ├── MainActivity.kt          # Main activity with RecyclerView
│           │   ├── Event.kt                 # Event data model with filtering logic
│           │   ├── EventsAdapter.kt         # RecyclerView adapter
│           │   └── EventsApiService.kt      # API service for fetching events
│           └── res/
│               ├── layout/
│               │   ├── activity_main.xml    # Main screen layout
│               │   └── item_event.xml       # Event card layout
│               └── values/
│                   ├── strings.xml
│                   └── colors.xml
├── build.gradle
├── settings.gradle
└── gradle.properties
```

## API Integration

The app uses the NYC Open Data API endpoint:
- Base URL: `https://data.cityofnewyork.us/resource/`
- Dataset: `tvpp-9vvx.json` (NYC Events Calendar)

### Sample Events

If the API is unavailable, the app shows curated sample events including:
- Brooklyn Night Market in Bushwick
- Lower East Side Art Walk
- Astoria Park Community Yoga
- Red Hook Food Vendors
- Underground Comedy Shows
- Prospect Park Birding Walks
- Williamsburg Craft Beer Nights
- Crown Heights Drum Circle

## Customization

### Adjusting Non-Touristy Filtering

Edit `Event.kt` to modify the `isNonTouristy()` function:

```kotlin
fun isNonTouristy(): Boolean {
    val touristyKeywords = listOf(
        "statue of liberty", "times square", "empire state",
        // Add more keywords here
    )
    // ...
}
```

### Adding Custom Insights

Edit `Event.kt` to modify the `getInsight()` function to add your own insight categories.

### Changing Time Range

Edit `EventsApiService.kt` to adjust the date filter:

```kotlin
@Query("\$where") where: String = "start_date_time > '2026-01-01T00:00:00.000'"
```

## Permissions

The app requires:
- `INTERNET`: To fetch events from NYC Open Data API
- `ACCESS_NETWORK_STATE`: To check network connectivity

## Troubleshooting

### Gradle Build Fails

1. Ensure you have JDK 17 installed
2. Check that ANDROID_HOME is set correctly
3. Try: `./gradlew clean build`

### APK Won't Install

1. Enable "Install from Unknown Sources" on your device
2. Check that your device runs Android 7.0 (API 24) or higher

### No Events Showing

1. Check internet connection
2. The app will show sample events if API is unavailable
3. Check that your system date is correct

## License

This project is provided as-is for educational and personal use.

## Credits

Data provided by NYC Open Data (data.cityofnewyork.us)
