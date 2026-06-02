# NASA APIs

## Base URL

```
https://api.nasa.gov
```

## Authentication

All endpoints require an API key passed as `api_key` query parameter.
- Get a free key at: https://api.nasa.gov/#signUp
- Demo key: `DEMO_KEY` (rate-limited: 30 req/hour, 50 req/day per IP)
- Registered keys: 1,000 req/hour

## Key Endpoints

### 1. APOD (Astronomy Picture of the Day)

```
GET /planetary/apod
```

**Parameters:**

| Parameter  | Type   | Description |
|------------|--------|-------------|
| `api_key`  | string | **Required.** API key. |
| `date`     | string | YYYY-MM-DD. Default: today. |
| `start_date` | string | Start of date range (YYYY-MM-DD). |
| `end_date` | string | End of date range (YYYY-MM-DD). |
| `count`    | int    | Return N random images (cannot combine with date/range). |
| `thumbs`   | bool   | Return thumbnail URL for video entries. |

**Example:**
```
https://api.nasa.gov/planetary/apod?api_key=DEMO_KEY&date=2024-01-15
```

**Response (JSON):**
```json
{
  "date": "2024-01-15",
  "title": "...",
  "explanation": "...",
  "url": "https://apod.nasa.gov/apod/image/...",
  "hdurl": "https://apod.nasa.gov/apod/image/...",
  "media_type": "image",
  "copyright": "..."
}
```

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

### 3. Mars Rover Photos

```
GET /mars-photos/api/v1/rovers/{rover}/photos
```

Rovers: `curiosity`, `opportunity`, `spirit`, `perseverance`

**Parameters:**

| Parameter | Type   | Description |
|-----------|--------|-------------|
| `api_key` | string | **Required.** |
| `sol`     | int    | Martian sol (day). Use `sol` OR `earth_date`, not both. |
| `earth_date` | string | YYYY-MM-DD. |
| `camera`  | string | Filter by camera: `FHAZ`, `RHAZ`, `MAST`, `CHEMCAM`, `NAVCAM`, etc. |
| `page`    | int    | 25 results per page. |

**Example:**
```
https://api.nasa.gov/mars-photos/api/v1/rovers/curiosity/photos?sol=1000&camera=NAVCAM&api_key=DEMO_KEY
```

**Rover manifest (mission metadata):**
```
GET /mars-photos/api/v1/manifests/{rover}?api_key=DEMO_KEY
```

**Response:** Array of `photos`, each with `id`, `sol`, `camera` (with `full_name`), `img_src`, `earth_date`, `rover`.

## Rate Limits

| Key Type   | Hourly Limit | Daily Limit |
|------------|-------------|-------------|
| `DEMO_KEY` | 30/hour     | 50/day      |
| Registered | 1,000/hour  | Unlimited   |

Rate limit headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`.
