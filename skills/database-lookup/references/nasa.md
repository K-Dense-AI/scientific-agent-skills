# NASA APIs

## Base URL

```
https://api.nasa.gov
```

## Authentication

NeoWs uses an API key passed as `api_key`; APOD now uses the separate WordPress endpoint below. Check per-service authentication in the NASA catalogue.
- Get a free key at: https://api.nasa.gov/#signUp
- Demo key: `DEMO_KEY` (rate-limited: 30 req/hour, 50 req/day per IP)
- Registered keys: 1,000 req/hour

## Key Endpoints

### 1. APOD (Astronomy Picture of the Day)

Use the new WordPress service:
```text
GET https://science.nasa.gov/wp-json/wp/v2/apod-basic/260911
GET https://science.nasa.gov/wp-json/wp/v2/apod-basic?page=1&per_page=5
GET https://science.nasa.gov/wp-json/wp/v2/apod-basic?date_from=260901&date_to=260930
```
A single date is a **YYMMDD path segment**; ranges use `date_from` and `date_to`
in the same format. List pagination is one-based and `per_page` is capped at 25.
The old `date=YYYY-MM-DD` parameter can be silently ignored by this service:
a September 30 probe returned the latest 25 entries instead of the requested date.

The single-date response is an object; list responses are arrays. Fields include
`date`, `post_id`, `title`, `permalink`, `media_type`, `explanation`, `credit`,
`copyright`, `alt`, `url`, `hdurl`, and generated HTML links. `url` can be an
article page. Preserve attribution and inspect media type before downloading.

The NASA-linked [new API guide](https://schlotterer.notion.site/APOD-Feed-And-API-User-Guide-39697d8747c38015a53edfdde76d4f5e)
is authoritative for this syntax; the NASA catalogue still contains some old
query parameters. Legacy `/planetary/apod` is scheduled to retire December 1, 2026.

### 2. NEO — Near Earth Objects (Asteroids NeoWs)

```
GET /neo/rest/v1/feed
```

**Parameters:**

| Parameter    | Type   | Description |
|--------------|--------|-------------|
| `api_key`    | string | **Required.** |
| `start_date` | string | YYYY-MM-DD. Default: today. |
| `end_date`   | string | YYYY-MM-DD. Max 7 days from start. |

**Example:**
```
https://api.nasa.gov/neo/rest/v1/feed?start_date=2024-01-01&end_date=2024-01-03&api_key=DEMO_KEY
```

**Lookup by asteroid ID:**
```
GET /neo/rest/v1/neo/{asteroid_id}?api_key=DEMO_KEY
```

**Browse all:**
```
GET /neo/rest/v1/neo/browse?api_key=DEMO_KEY
```

**Response structure:** `near_earth_objects` keyed by date, each containing array of objects with `name`, `nasa_jpl_url`, `estimated_diameter`, `close_approach_data`, `is_potentially_hazardous_asteroid`.

### 3. Archived services

The NASA portal marks the Mars Rover Photos and Earth APIs as archived. Do not
use the former `/mars-photos/api/v1/...` routes for new retrieval workflows.
For Earth imagery, follow the portal's Earthdata GIBS replacement link.

## Rate Limits

| Key Type   | Hourly Limit | Daily Limit |
|------------|-------------|-------------|
| `DEMO_KEY` | 30/hour     | 50/day      |
| Registered | 1,000/hour  | Unlimited   |

Rate limit headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`.

Official [migration notice](https://api.nasa.gov/assets/html/header.html) and [API catalogue](https://api.nasa.gov/assets/json/apis.json).
