package com.nycevents

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView

class EventsAdapter(private val events: List<Event>) :
    RecyclerView.Adapter<EventsAdapter.EventViewHolder>() {

    class EventViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val eventName: TextView = view.findViewById(R.id.eventName)
        val eventInsight: TextView = view.findViewById(R.id.eventInsight)
        val eventDate: TextView = view.findViewById(R.id.eventDate)
        val eventLocation: TextView = view.findViewById(R.id.eventLocation)
        val eventBorough: TextView = view.findViewById(R.id.eventBorough)
        val eventDescription: TextView = view.findViewById(R.id.eventDescription)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): EventViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_event, parent, false)
        return EventViewHolder(view)
    }

    override fun onBindViewHolder(holder: EventViewHolder, position: Int) {
        val event = events[position]

        holder.eventName.text = event.name ?: "Unnamed Event"
        holder.eventInsight.text = event.getInsight()
        holder.eventDate.text = event.getFormattedDate()
        holder.eventLocation.text = event.location ?: "Location TBA"
        holder.eventBorough.text = event.borough ?: "NYC"
        holder.eventDescription.text = event.description ?: "No description available"
    }

    override fun getItemCount() = events.size
}
