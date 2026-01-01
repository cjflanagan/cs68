package com.nycevents

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import retrofit2.http.Query
import java.util.concurrent.TimeUnit

interface EventsApi {
    @GET("resource/tvpp-9vvx.json")
    suspend fun getEvents(
        @Query("\$limit") limit: Int = 1000,
        @Query("\$where") where: String = "start_date_time > '2026-01-01T00:00:00.000'"
    ): List<Event>
}

object EventsApiService {
    private const val BASE_URL = "https://data.cityofnewyork.us/resource/"

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }

    private val client = OkHttpClient.Builder()
        .addInterceptor(loggingInterceptor)
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    private val retrofit = Retrofit.Builder()
        .baseUrl(BASE_URL)
        .client(client)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    val api: EventsApi = retrofit.create(EventsApi::class.java)

    suspend fun fetchNonTouristyEvents(): List<Event> {
        return try {
            // Fetch events from NYC Open Data
            val allEvents = api.getEvents()

            // Filter for next week and non-touristy events
            allEvents.filter { event ->
                event.isInNextWeek() && event.isNonTouristy()
            }.sortedBy { it.startDateTime }
        } catch (e: Exception) {
            e.printStackTrace()
            // Return sample events if API fails
            getSampleEvents()
        }
    }

    private fun getSampleEvents(): List<Event> {
        // Sample events for demonstration
        return listOf(
            Event(
                name = "Brooklyn Night Market",
                eventType = "Food & Culture",
                startDateTime = "2026-01-03T18:00:00.000",
                endDateTime = "2026-01-03T23:00:00.000",
                location = "99 Scott Ave, Brooklyn",
                borough = "Brooklyn",
                agency = "Private",
                description = "Free outdoor market featuring local food vendors, artisans, and live music in Bushwick"
            ),
            Event(
                name = "Lower East Side Art Walk",
                eventType = "Arts & Culture",
                startDateTime = "2026-01-04T14:00:00.000",
                endDateTime = "2026-01-04T19:00:00.000",
                location = "Multiple galleries on Orchard St",
                borough = "Manhattan",
                agency = "Community Arts",
                description = "Free self-guided tour of independent art galleries in the Lower East Side"
            ),
            Event(
                name = "Astoria Park Community Yoga",
                eventType = "Outdoor Recreation",
                startDateTime = "2026-01-05T09:00:00.000",
                endDateTime = "2026-01-05T10:30:00.000",
                location = "Astoria Park",
                borough = "Queens",
                agency = "NYC Parks",
                description = "Free outdoor yoga session with views of the East River. All levels welcome"
            ),
            Event(
                name = "Red Hook Food Vendors Opening",
                eventType = "Food",
                startDateTime = "2026-01-06T12:00:00.000",
                endDateTime = "2026-01-06T20:00:00.000",
                location = "Red Hook Ball Fields",
                borough = "Brooklyn",
                agency = "Private",
                description = "Authentic Latin American food from local vendors. Cash only"
            ),
            Event(
                name = "Underground Comedy Show",
                eventType = "Comedy",
                startDateTime = "2026-01-06T20:00:00.000",
                endDateTime = "2026-01-06T22:00:00.000",
                location = "Secret Location in East Village",
                borough = "Manhattan",
                agency = "Private",
                description = "Intimate comedy night featuring up-and-coming NYC comedians"
            ),
            Event(
                name = "Prospect Park Birding Walk",
                eventType = "Outdoor Recreation",
                startDateTime = "2026-01-07T08:00:00.000",
                endDateTime = "2026-01-07T10:00:00.000",
                location = "Prospect Park Audubon Center",
                borough = "Brooklyn",
                agency = "NYC Parks",
                description = "Free guided birding walk through Prospect Park. Binoculars provided"
            ),
            Event(
                name = "Williamsburg Craft Beer Night",
                eventType = "Nightlife",
                startDateTime = "2026-01-07T19:00:00.000",
                endDateTime = "2026-01-07T23:00:00.000",
                location = "123 Grand St, Brooklyn",
                borough = "Brooklyn",
                agency = "Private",
                description = "Local craft breweries showcase. Meet the brewers and try exclusive releases"
            ),
            Event(
                name = "Crown Heights Drum Circle",
                eventType = "Music & Community",
                startDateTime = "2026-01-08T17:00:00.000",
                endDateTime = "2026-01-08T19:00:00.000",
                location = "Brower Park",
                borough = "Brooklyn",
                agency = "Community",
                description = "Free weekly drum circle. Bring your own drums or use community instruments"
            )
        )
    }
}
