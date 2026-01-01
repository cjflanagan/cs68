package com.nycevents

import com.google.gson.annotations.SerializedName
import java.text.SimpleDateFormat
import java.util.*

data class Event(
    @SerializedName("event_name")
    val name: String?,

    @SerializedName("event_type")
    val eventType: String?,

    @SerializedName("start_date_time")
    val startDateTime: String?,

    @SerializedName("end_date_time")
    val endDateTime: String?,

    @SerializedName("event_location")
    val location: String?,

    @SerializedName("event_borough")
    val borough: String?,

    @SerializedName("event_agency")
    val agency: String?,

    @SerializedName("event_description")
    val description: String?
) {
    fun isNonTouristy(): Boolean {
        val touristyKeywords = listOf(
            "statue of liberty", "times square", "empire state",
            "tourist", "sightseeing", "hop on hop off", "broadway tour",
            "city tour", "landmark tour"
        )

        val searchText = "${name?.lowercase()} ${description?.lowercase()} ${location?.lowercase()}"
        return !touristyKeywords.any { searchText.contains(it) }
    }

    fun getInsight(): String {
        val insights = mutableListOf<String>()

        // Local neighborhood vibe
        val localNeighborhoods = listOf("williamsburg", "bushwick", "astoria", "greenpoint",
            "prospect heights", "red hook", "crown heights", "bed-stuy", "east village")
        if (localNeighborhoods.any { location?.lowercase()?.contains(it) == true }) {
            insights.add("🏘️ Local neighborhood spot")
        }

        // Community events
        if (eventType?.lowercase()?.contains("community") == true ||
            agency?.lowercase()?.contains("parks") == true) {
            insights.add("👥 Community event")
        }

        // Arts & Culture
        if (eventType?.lowercase()?.let { it.contains("art") || it.contains("music") || it.contains("culture") } == true) {
            insights.add("🎨 Arts & culture")
        }

        // Food & dining
        if (name?.lowercase()?.let { it.contains("food") || it.contains("market") || it.contains("dining") } == true) {
            insights.add("🍴 Food scene")
        }

        // Outdoor activities
        if (name?.lowercase()?.let { it.contains("outdoor") || it.contains("park") || it.contains("garden") } == true) {
            insights.add("🌳 Outdoor activity")
        }

        // Night life
        if (name?.lowercase()?.let { it.contains("night") || it.contains("concert") || it.contains("dj") } == true) {
            insights.add("🌙 Nightlife")
        }

        // Free events
        if (description?.lowercase()?.contains("free") == true) {
            insights.add("💰 Free event")
        }

        return if (insights.isEmpty()) "📍 Authentic NYC experience" else insights.joinToString(" • ")
    }

    fun isInNextWeek(): Boolean {
        if (startDateTime.isNullOrEmpty()) return false

        return try {
            val dateFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS", Locale.US)
            val eventDate = dateFormat.parse(startDateTime)
            val now = Calendar.getInstance()
            val nextWeek = Calendar.getInstance()
            nextWeek.add(Calendar.DAY_OF_YEAR, 7)

            eventDate != null && eventDate.after(now.time) && eventDate.before(nextWeek.time)
        } catch (e: Exception) {
            false
        }
    }

    fun getFormattedDate(): String {
        if (startDateTime.isNullOrEmpty()) return "Date TBA"

        return try {
            val inputFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS", Locale.US)
            val outputFormat = SimpleDateFormat("EEE, MMM d 'at' h:mm a", Locale.US)
            val date = inputFormat.parse(startDateTime)
            if (date != null) outputFormat.format(date) else "Date TBA"
        } catch (e: Exception) {
            startDateTime
        }
    }
}

data class EventsResponse(
    val data: List<Event>?
)
