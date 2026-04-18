"""Google Calendar tool – create events from natural language."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

from rayban_meta.config import settings
from rayban_meta.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class CalendarTool(BaseTool):
    name = "calendar"
    description = "Create calendar events, reminders, or check schedule."
    keywords = ["calendar", "remind", "schedule", "meeting", "event", "reminder"]

    async def execute(self, query: str, store, llm) -> ToolResult:
        # Use LLM to extract structured event data
        now = datetime.now().isoformat()
        extraction = await llm.complete(
            messages=[{"role": "user", "content": query}],
            system=(
                f"Current datetime: {now}\n"
                "Extract calendar event details from the user message. "
                "Return JSON with keys: title, date (YYYY-MM-DD), time (HH:MM), "
                "duration_minutes (int, default 30), description (optional). "
                "If the user says 'tomorrow', compute the actual date. "
                "Return ONLY valid JSON, nothing else."
            ),
            max_tokens=200,
        )

        try:
            event_data = json.loads(extraction)
        except json.JSONDecodeError:
            return ToolResult(text="I couldn't understand the event details. Please try again with a date and time.")

        # Try to create via Google Calendar API
        if settings.google_calendar_credentials:
            try:
                result = await self._create_google_event(event_data)
                return ToolResult(text=result)
            except Exception:
                logger.exception("Google Calendar API failed")

        # Fallback: save as a knowledge entry
        title = event_data.get("title", "Reminder")
        date = event_data.get("date", "?")
        time = event_data.get("time", "?")
        await store.add_knowledge(
            content=f"EVENT: {title} on {date} at {time}",
            source="calendar",
            folder="calendar",
        )
        return ToolResult(text=f"Noted: {title} on {date} at {time}. (Saved locally – connect Google Calendar for full sync.)")

    async def _create_google_event(self, event_data: dict) -> str:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials.from_authorized_user_file(settings.google_calendar_credentials)
        service = build("calendar", "v3", credentials=creds)

        date = event_data.get("date", datetime.now().strftime("%Y-%m-%d"))
        time = event_data.get("time", "09:00")
        duration = event_data.get("duration_minutes", 30)
        start = datetime.fromisoformat(f"{date}T{time}:00")
        end = start + timedelta(minutes=duration)

        event = {
            "summary": event_data.get("title", "Reminder"),
            "description": event_data.get("description", "Created via Ray-Ban Meta glasses"),
            "start": {"dateTime": start.isoformat(), "timeZone": "Europe/Bucharest"},
            "end": {"dateTime": end.isoformat(), "timeZone": "Europe/Bucharest"},
        }
        created = service.events().insert(calendarId="primary", body=event).execute()
        return f"Event created: {created.get('summary')} on {date} at {time}"
