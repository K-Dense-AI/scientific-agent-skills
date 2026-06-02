# OpenWeatherMap API Reference

## Base URL
```
https://api.openweathermap.org
```

## Authentication
- **API Key: REQUIRED.** Register for a free key at https://home.openweathermap.org/users/sign_up
- Pass as query parameter: `&appid=YOUR_KEY`
- Free tier key activates within a few hours of registration.

## Rate Limits (Free Tier)
- **60 calls per minute** (1,000 calls/day for some endpoints).
- **Current weather, 5-day forecast, geocoding:** Available on free tier.
- **One Call 3.0:** Requires subscription (1,000 free calls/day with credit card on file).
- **Historical data, air pollution history:** Requires paid plan for extended ranges.

---

## Key Endpoints

### 1. Current Weather
```
GET /data/2.5/weather
```

**Parameters:**
| Parameter | Type   | Required | Default  | Description |
|-----------|--------|----------|----------|-------------|
| `q`       | string | Cond.    | -        | City name, optionally with state/country: `London`, `London,GB`, `Portland,OR,US`. |
| `lat`     | float  | Cond.    | -        | Latitude (use with `lon`). |
| `lon`     | float  | Cond.    | -        | Longitude (use with `lat`). |
| `id`      | int    | Cond.    | -        | City ID (from OWM city list). |
| `zip`     | string | Cond.    | -        | Zip/postal code with country: `90210,US`, `SW1,GB`. |
| `units`   | string | No       | `standard` | `standard` (Kelvin), `metric` (Celsius), `imperial` (Fahrenheit). |
| `lang`    | string | No       | `en`     | Language code for descriptions. |
| `appid`   | string | Yes      | -        | API key. |

One location parameter (`q`, `lat`+`lon`, `id`, or `zip`) is required.

**Example:**
```
https://api.openweathermap.org/data/2.5/weather?lat=40.7128&lon=-74.0060&units=metric&appid=YOUR_KEY
```

**Response:**
```json
{
  "coord": {"lon": -74.006, "lat": 40.7128},
  "weather": [
    {
      "id": 800,
      "main": "Clear",
      "description": "clear sky",
      "icon": "01d"
    }
  ],
  "base": "stations",
  "main": {
    "temp": 22.5,
    "feels_like": 21.8,
    "temp_min": 20.1,
    "temp_max": 24.3,
    "pressure": 1013,
    "humidity": 55,
    "sea_level": 1013,
    "grnd_level": 1010
  },
  "visibility": 10000,
  "wind": {"speed": 3.6, "deg": 220, "gust": 5.1},
  "clouds": {"all": 0},
  "dt": 1700000000,
  "sys": {
    "country": "US",
    "sunrise": 1699960000,
    "sunset": 1699996000
  },
  "timezone": -18000,
  "id": 5128581,
  "name": "New York",
  "cod": 200
}
```

### 2. 5-Day / 3-Hour Forecast (Free)
```
GET /data/2.5/forecast
```
Returns forecast data in 3-hour intervals for 5 days (40 data points). Same location parameters as current weather.

**Additional Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `cnt`     | int  | Number of 3-hour steps to return (max 40). |

**Example:**
```
https://api.openweathermap.org/data/2.5/forecast?q=London,GB&units=metric&cnt=8&appid=YOUR_KEY
```

**Response:**
```json
{
  "cod": "200",
  "message": 0,
  "cnt": 8,
  "list": [
    {
      "dt": 1700000000,
      "main": {
        "temp": 10.5,
        "feels_like": 8.2,
        "temp_min": 9.8,
        "temp_max": 10.5,
        "pressure": 1020,
        "humidity": 80
      },
      "weather": [{"id": 802, "main": "Clouds", "description": "scattered clouds", "icon": "03d"}],
      "clouds": {"all": 40},
      "wind": {"speed": 4.1, "deg": 250},
      "visibility": 10000,
      "pop": 0.2,
      "dt_txt": "2024-01-15 12:00:00"
    }
  ],
  "city": {
    "id": 2643743,
    "name": "London",
    "coord": {"lat": 51.5085, "lon": -0.1257},
    "country": "GB",
    "population": 1000000,
    "timezone": 0,
    "sunrise": 1699950000,
    "sunset": 1699982000
  }
}
```
`pop` is probability of precipitation (0.0 to 1.0).

### 3. Geocoding
```
GET /geo/1.0/direct
GET /geo/1.0/reverse
GET /geo/1.0/zip
```

**Direct geocoding (city name to coordinates):**
```
https://api.openweathermap.org/geo/1.0/direct?q=London,GB&limit=5&appid=YOUR_KEY
```
Returns array of `{name, lat, lon, country, state}`.

**Reverse geocoding (coordinates to city name):**
```
https://api.openweathermap.org/geo/1.0/reverse?lat=51.5085&lon=-0.1257&limit=1&appid=YOUR_KEY
```

**Zip code geocoding:**
```
https://api.openweathermap.org/geo/1.0/zip?zip=90210,US&appid=YOUR_KEY
```

### 4. One Call API 3.0 (Subscription Required)
```
GET /data/3.0/onecall
```
Comprehensive endpoint returning current, minutely (1h), hourly (48h), daily (8d), and alerts in one call.

**Parameters:**
| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| `lat`     | float  | Yes      | Latitude. |
| `lon`     | float  | Yes      | Longitude. |
| `exclude` | string | No       | Comma-separated parts to exclude: `current`, `minutely`, `hourly`, `daily`, `alerts`. |
| `units`   | string | No       | `standard`, `metric`, `imperial`. |
| `appid`   | string | Yes      | API key. |

**Example:**
```
https://api.openweathermap.org/data/3.0/onecall?lat=40.7128&lon=-74.006&exclude=minutely,alerts&units=metric&appid=YOUR_KEY
```

### 5. Air Pollution
```
GET /data/2.5/air_pollution
GET /data/2.5/air_pollution/forecast
GET /data/2.5/air_pollution/history
```

**Parameters:** `lat`, `lon`, `appid` (required). For history: `start` and `end` (Unix timestamps).

**Example:**
```
https://api.openweathermap.org/data/2.5/air_pollution?lat=40.7128&lon=-74.006&appid=YOUR_KEY
```

**Response:**
```json
{
  "coord": {"lon": -74.006, "lat": 40.7128},
  "list": [
    {
      "main": {"aqi": 2},
      "components": {
        "co": 230.31,
        "no": 0.5,
        "no2": 15.0,
        "o3": 68.0,
        "so2": 2.5,
        "pm2_5": 8.1,
        "pm10": 12.3,
        "nh3": 1.0
      },
      "dt": 1700000000
    }
  ]
}
```
AQI scale: 1=Good, 2=Fair, 3=Moderate, 4=Poor, 5=Very Poor. Components in ug/m3.

---

## Weather Condition Codes
| Range   | Category |
|---------|----------|
| 2xx     | Thunderstorm |
| 3xx     | Drizzle |
| 5xx     | Rain |
| 6xx     | Snow |
| 7xx     | Atmosphere (fog, mist, haze) |
| 800     | Clear |
| 80x     | Clouds |

Weather icons: `https://openweathermap.org/img/wn/{icon}@2x.png`

## Free Tier vs Paid Summary
| Endpoint | Free | Subscription |
|----------|------|-------------|
| Current weather | Yes | Yes |
| 5-day/3-hour forecast | Yes | Yes |
| Geocoding | Yes | Yes |
| Air pollution (current) | Yes | Yes |
| One Call 3.0 | 1000/day (credit card required) | Yes |
| Historical weather | No | Yes |
| Daily forecast 16-day | No | Yes |
| Climatic forecast 30-day | No | Yes |

## Notes
- All timestamps (`dt`, `sunrise`, `sunset`) are **Unix epoch seconds (UTC)**.
- `timezone` field is offset in seconds from UTC (e.g. -18000 = UTC-5).
- Default temperature unit is Kelvin. Always specify `units=metric` or `units=imperial`.
- City name queries (`q=`) can be ambiguous. Prefer `lat`+`lon` for precision, using geocoding first if needed.
- Weather icon URL pattern: `https://openweathermap.org/img/wn/{icon}@2x.png` (e.g. `01d` for clear day).
- Error responses return `{"cod": 401, "message": "Invalid API key"}` or similar.
