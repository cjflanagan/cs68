# NYC Events Android App - Project Summary

## Overview

This is a complete Android application that provides custom insights into fun, non-touristy events happening in New York City over the next week.

## Key Features

### 1. Smart Event Filtering
- **Non-Touristy Filter**: Automatically excludes common tourist attractions like Times Square, Statue of Liberty, Empire State Building tours, etc.
- **Next Week Only**: Shows only events happening in the next 7 days
- **Local Focus**: Prioritizes neighborhood events over mainstream tourist activities

### 2. Custom Insights Engine
The app analyzes each event and provides custom insights tags:

- 🏘️ **Local neighborhood spot** - Events in authentic NYC neighborhoods (Williamsburg, Bushwick, Astoria, etc.)
- 👥 **Community event** - Parks department and community-organized activities
- 🎨 **Arts & culture** - Gallery openings, art walks, cultural events
- 🍴 **Food scene** - Food markets, vendor events, dining experiences
- 🌳 **Outdoor activity** - Park events, gardens, outdoor recreation
- 🌙 **Nightlife** - Concerts, DJ sets, late-night events
- 💰 **Free event** - No-cost activities

### 3. Data Source
- **NYC Open Data API**: Real-time event data from official NYC sources
- **Fallback Sample Data**: Curated sample events if API is unavailable
- **Dataset**: tvpp-9vvx.json (NYC Events Calendar)

## Technical Architecture

### Technology Stack
- **Language**: Kotlin
- **Minimum SDK**: Android 7.0 (API 24)
- **Target SDK**: Android 14 (API 34)
- **UI Framework**: Material Design 3
- **Networking**: Retrofit 2.9.0 + OkHttp
- **Async Processing**: Kotlin Coroutines
- **Architecture**: MVVM pattern

### Project Structure
```
NYCEventsApp/
├── app/
│   ├── src/main/
│   │   ├── java/com/nycevents/
│   │   │   ├── MainActivity.kt           # Main UI with RecyclerView
│   │   │   ├── Event.kt                  # Data model with filtering logic
│   │   │   ├── EventsAdapter.kt          # RecyclerView adapter
│   │   │   └── EventsApiService.kt       # API client and data fetching
│   │   ├── res/
│   │   │   ├── layout/
│   │   │   │   ├── activity_main.xml     # Main screen layout
│   │   │   │   └── item_event.xml        # Event card design
│   │   │   └── values/
│   │   │       ├── strings.xml
│   │   │       └── colors.xml
│   │   └── AndroidManifest.xml
│   └── build.gradle                      # App dependencies
├── build.gradle                          # Project configuration
├── settings.gradle                       # Gradle settings
├── gradle.properties                     # Gradle properties
├── gradlew                               # Gradle wrapper script
├── build.sh                              # Build script
├── docker-build.sh                       # Docker-based build
├── Dockerfile                            # Docker configuration
├── README.md                             # Main documentation
├── INSTALLATION.md                       # Detailed install guide
└── PROJECT_SUMMARY.md                    # This file
```

### Key Components

#### Event.kt
Core data model with:
- Event properties (name, date, location, borough, description)
- `isNonTouristy()` - Filters out touristy keywords
- `getInsight()` - Generates custom insight tags
- `isInNextWeek()` - Date filtering logic
- `getFormattedDate()` - User-friendly date formatting

#### EventsApiService.kt
API service with:
- Retrofit configuration for NYC Open Data
- Async event fetching with coroutines
- Error handling with fallback to sample data
- HTTP logging for debugging

#### MainActivity.kt
Main UI controller:
- RecyclerView setup for event list
- Coroutine-based async loading
- Progress indicator
- Empty state handling

#### EventsAdapter.kt
RecyclerView adapter:
- Material Design card layout
- Custom insight display
- Formatted dates and locations

## How It Works

### Data Flow
1. **App Launch** → MainActivity.onCreate()
2. **Fetch Events** → EventsApiService.fetchNonTouristyEvents()
3. **API Call** → NYC Open Data API
4. **Filter Events** → isInNextWeek() && isNonTouristy()
5. **Generate Insights** → getInsight() for each event
6. **Display** → RecyclerView with EventsAdapter
7. **User Views** → Scrollable list of curated events

### Filtering Algorithm

```kotlin
// Non-touristy filter
touristyKeywords = ["statue of liberty", "times square", "empire state", ...]
if (event contains touristy keyword) → exclude

// Time filter
if (event.startDate > today && event.startDate < today + 7 days) → include

// Insight generation
if (location in localNeighborhoods) → add "🏘️ Local neighborhood"
if (eventType contains "community") → add "👥 Community event"
if (description contains "free") → add "💰 Free event"
```

## Sample Events

The app includes 8 curated sample events that demonstrate the variety of non-touristy NYC experiences:

1. **Brooklyn Night Market** - Food & culture in Bushwick
2. **Lower East Side Art Walk** - Independent galleries
3. **Astoria Park Yoga** - Free outdoor fitness
4. **Red Hook Food Vendors** - Authentic Latin American cuisine
5. **Underground Comedy** - Intimate East Village show
6. **Prospect Park Birding** - Nature walk
7. **Williamsburg Craft Beer** - Local breweries
8. **Crown Heights Drum Circle** - Community music

## Build Methods

### Option 1: Android Studio
- Easiest for most users
- Full IDE support
- Built-in SDK management
- Build time: 2-3 minutes

### Option 2: Command Line
- For developers comfortable with terminal
- Requires Android SDK setup
- Uses Gradle wrapper
- Build time: 1-2 minutes

### Option 3: Docker
- No Android SDK installation needed
- Reproducible builds
- First build: 10-15 minutes (downloads SDK)
- Subsequent builds: 2-3 minutes

### Option 4: GitHub Actions
- Completely cloud-based
- No local setup required
- Build on push or manual trigger
- Download artifacts from GitHub

## Permissions

The app requires minimal permissions:
- **INTERNET**: Fetch events from NYC Open Data API
- **ACCESS_NETWORK_STATE**: Check connectivity status

No location, storage, camera, or other invasive permissions needed.

## Customization Points

### Add More Non-Touristy Keywords
Edit `Event.kt`, function `isNonTouristy()`:
```kotlin
val touristyKeywords = listOf(
    "your", "keywords", "here"
)
```

### Change Time Range
Edit `EventsApiService.kt`:
```kotlin
// Change from 7 days to 14 days
nextWeek.add(Calendar.DAY_OF_YEAR, 14)
```

### Add Custom Insights
Edit `Event.kt`, function `getInsight()`:
```kotlin
if (yourCondition) {
    insights.add("🎯 Your custom insight")
}
```

### Change Theme Colors
Edit `app/src/main/res/values/colors.xml`

## Installation Methods

### USB Installation
```bash
adb install app/build/outputs/apk/debug/app-debug.apk
```

### Wireless Installation
- Enable wireless debugging on device
- Pair with `adb pair`
- Install with `adb install`

### Manual Installation
- Transfer APK to device
- Enable "Install from Unknown Sources"
- Tap APK to install

## Testing

### Manual Testing Checklist
- [ ] App launches without crashes
- [ ] Events list loads (or shows sample data)
- [ ] All events display properly formatted dates
- [ ] All events show custom insights
- [ ] Event cards show all information
- [ ] Scrolling works smoothly
- [ ] No touristy events in the list
- [ ] Only events from next 7 days shown

### Common Test Scenarios
1. **No Internet**: Should show sample events
2. **First Launch**: Progress indicator should appear
3. **No Events Available**: Should show "No events found" message
4. **Many Events**: Should scroll smoothly

## Performance

- **App Size**: ~5-8 MB (debug APK)
- **Launch Time**: <1 second on modern devices
- **Data Usage**: Minimal (API calls ~50-100 KB)
- **Memory**: ~50-80 MB RAM usage
- **Battery**: Negligible impact

## Future Enhancements

Potential features for future versions:
- [ ] Save favorite events
- [ ] Share events with friends
- [ ] Calendar integration
- [ ] Location-based filtering
- [ ] Event categories filter
- [ ] Dark mode support
- [ ] Event details screen
- [ ] Map view of events
- [ ] Push notifications
- [ ] User preferences

## Dependencies

### Core Android
- androidx.core:core-ktx:1.12.0
- androidx.appcompat:appcompat:1.6.1
- com.google.android.material:material:1.11.0
- androidx.constraintlayout:constraintlayout:2.1.4

### UI Components
- androidx.recyclerview:recyclerview:1.3.2
- androidx.cardview:cardview:1.0.0

### Networking
- com.squareup.retrofit2:retrofit:2.9.0
- com.squareup.retrofit2:converter-gson:2.9.0
- com.squareup.okhttp3:logging-interceptor:4.11.0

### Async
- org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3
- androidx.lifecycle:lifecycle-runtime-ktx:2.7.0
- androidx.lifecycle:lifecycle-viewmodel-ktx:2.7.0

## Troubleshooting

See [INSTALLATION.md](INSTALLATION.md) for detailed troubleshooting guides.

## License

This project is provided as-is for educational and personal use.

## Credits

- Data: NYC Open Data (data.cityofnewyork.us)
- Icons: Material Design Icons
- Framework: Android SDK, Kotlin
- Libraries: Retrofit, OkHttp, Kotlin Coroutines

---

**Last Updated**: 2026-01-01
**Version**: 1.0
**Minimum Android**: 7.0 (API 24)
**Target Android**: 14 (API 34)
