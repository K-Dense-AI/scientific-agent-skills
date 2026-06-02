from cluster import segment_sessions, cluster_sessions


def _evt(ts: int, app: str, title: str = "", text: str = "") -> dict:
    return {"ts": ts, "app": app, "window_title": title, "text": text}


def test_contiguous_events_form_one_session():
    events = [_evt(i * 30, "VSCode") for i in range(20)]  # 10 minutes
    sessions = segment_sessions(events, idle_gap_seconds=600, min_session_seconds=300)
    assert len(sessions) == 1
    assert sessions[0]["apps"] == ["VSCode"]
    assert sessions[0]["duration_seconds"] == 19 * 30


def test_idle_gap_splits_sessions():
    left = [_evt(i * 30, "Chrome") for i in range(20)]             # 0..570
    right = [_evt(10000 + i * 30, "Chrome") for i in range(20)]    # gap of ~9400s
    sessions = segment_sessions(left + right, idle_gap_seconds=600, min_session_seconds=300)
    assert len(sessions) == 2


def test_sessions_below_minimum_are_dropped():
    events = [_evt(i * 10, "Finder") for i in range(5)]  # 40 seconds total
    sessions = segment_sessions(events, idle_gap_seconds=600, min_session_seconds=300)
    assert sessions == []


def test_session_records_distinct_apps_in_order_of_first_appearance():
    events = [
        _evt(0, "Chrome"), _evt(30, "Chrome"),
        _evt(60, "Zotero"), _evt(90, "Zotero"),
        _evt(120, "VSCode"), _evt(600, "VSCode"),
    ]
    sessions = segment_sessions(events, idle_gap_seconds=600, min_session_seconds=300)
    assert len(sessions) == 1
    assert sessions[0]["apps"] == ["Chrome", "Zotero", "VSCode"]


def test_clusters_group_sessions_with_identical_app_signatures():
    sessions = [
        {"apps": ["Chrome", "Zotero"], "duration_seconds": 600, "window_titles": ["PubMed"]},
        {"apps": ["Chrome", "Zotero"], "duration_seconds": 800, "window_titles": ["bioRxiv"]},
        {"apps": ["VSCode"], "duration_seconds": 900, "window_titles": ["paper.tex"]},
    ]
    clusters = cluster_sessions(sessions, min_cluster_size=2)
    assert len(clusters) == 1
    assert clusters[0]["apps"] == ["Chrome", "Zotero"]
    assert clusters[0]["session_count"] == 2


def test_cluster_summary_exposes_total_duration_and_example_titles():
    sessions = [
        {"apps": ["Chrome"], "duration_seconds": 300, "window_titles": ["arXiv"]},
        {"apps": ["Chrome"], "duration_seconds": 500, "window_titles": ["Nature"]},
    ]
    clusters = cluster_sessions(sessions, min_cluster_size=2)
    assert clusters[0]["total_duration_seconds"] == 800
    assert set(clusters[0]["example_titles"]) == {"arXiv", "Nature"}


def test_singleton_clusters_are_dropped_when_below_min_cluster_size():
    sessions = [
        {"apps": ["Slack"], "duration_seconds": 400, "window_titles": ["general"]},
    ]
    clusters = cluster_sessions(sessions, min_cluster_size=2)
    assert clusters == []
