from collections import defaultdict


def segment_sessions(events, idle_gap_seconds, min_session_seconds):
    if not events:
        return []
    events = sorted(events, key=lambda e: e["ts"])
    groups = [[events[0]]]
    for prev, curr in zip(events, events[1:]):
        if curr["ts"] - prev["ts"] > idle_gap_seconds:
            groups.append([curr])
        else:
            groups[-1].append(curr)

    sessions = []
    for group in groups:
        duration = group[-1]["ts"] - group[0]["ts"]
        if duration < min_session_seconds:
            continue
        apps, seen = [], set()
        for evt in group:
            if evt["app"] not in seen:
                seen.add(evt["app"])
                apps.append(evt["app"])
        sessions.append({
            "start_ts": group[0]["ts"],
            "end_ts": group[-1]["ts"],
            "duration_seconds": duration,
            "apps": apps,
            "window_titles": [e["window_title"] for e in group if e.get("window_title")],
        })
    return sessions


def cluster_sessions(sessions, min_cluster_size):
    buckets = defaultdict(list)
    for s in sessions:
        buckets[tuple(s["apps"])].append(s)

    clusters = []
    for apps, members in buckets.items():
        if len(members) < min_cluster_size:
            continue
        example_titles = []
        for m in members:
            if m["window_titles"]:
                example_titles.append(m["window_titles"][0])
        clusters.append({
            "apps": list(apps),
            "session_count": len(members),
            "total_duration_seconds": sum(m["duration_seconds"] for m in members),
            "example_titles": example_titles,
        })
    return clusters
