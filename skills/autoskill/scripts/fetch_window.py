_MAX_PAGES = 10_000  # bounded exit: hard ceiling so the loop cannot spin forever


def fetch_window(client, start_time, end_time, page_size=50, token=None):
    events = []
    offset = 0
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    for _page in range(_MAX_PAGES):
        response = client.get("/search", params={
            "start_time": start_time,
            "end_time": end_time,
            "limit": page_size,
            "offset": offset,
        }, headers=headers)
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data", [])
        total = payload.get("pagination", {}).get("total", 0)

        for item in data:
            content = item.get("content", {})
            events.append({
                "ts": content.get("timestamp"),
                "app": content.get("app_name", ""),
                "window_title": content.get("window_name", ""),
                "text": content.get("text", ""),
                "content_type": item.get("type", "").lower(),
            })

        offset += len(data)
        if not data or offset >= total:
            break
    return events
