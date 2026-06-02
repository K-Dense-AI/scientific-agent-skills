# WHO Global Health Observatory (GHO) API Reference

## Overview
The WHO Global Health Observatory (GHO) OData API provides access to health statistics for 194 WHO member states. It covers over 2000 indicators including life expectancy, disease burden, mortality, immunization coverage, health workforce, air pollution, water/sanitation, and the Sustainable Development Goal (SDG) health indicators.

## Base URL
```
https://ghoapi.azureedge.net/api
```

## Authentication
**No API key required.** The API is fully open and free.

## Rate Limits
- No formal rate limits documented.
- The API is served via Azure CDN and handles moderate loads well.
- Be respectful with automated requests; 1-2 per second recommended.

---

## Key Endpoints

The API follows the OData v4 protocol. Standard OData query parameters work: `$filter`, `$select`, `$orderby`, `$top`, `$skip`, `$count`.

### 1. List All Indicators

```
GET /Indicator
```

**Example:**
```
https://ghoapi.azureedge.net/api/Indicator
```

**Response:**
```json
{
  "@odata.context": "...",
  "value": [
    {
      "IndicatorCode": "WHOSIS_000001",
      "IndicatorName": "Life expectancy at birth (years)",
      "Language": "EN"
    },
    {
      "IndicatorCode": "WHOSIS_000002",
      "IndicatorName": "Healthy life expectancy (HALE) at birth (years)",
      "Language": "EN"
    },
    {
      "IndicatorCode": "WHS4_100",
      "IndicatorName": "Measles (MCV1) immunization coverage among 1-year-olds (%)",
      "Language": "EN"
    }
  ]
}
```

### 2. Get Data for a Specific Indicator

```
GET /{IndicatorCode}
```

**Example (life expectancy at birth):**
```
https://ghoapi.azureedge.net/api/WHOSIS_000001
```

**Response:**
```json
{
  "@odata.context": "...",
  "value": [
    {
      "Id": 12345,
      "IndicatorCode": "WHOSIS_000001",
      "SpatialDim": "USA",
      "SpatialDimType": "COUNTRY",
      "TimeDim": 2019,
      "TimeDimType": "YEAR",
      "Dim1": "SEX",
      "Dim1Type": "BTSX",
      "Dim2": null,
      "Dim2Type": null,
      "Dim3": null,
      "Dim3Type": null,
      "DataSourceDim": null,
      "Value": "78.5",
      "NumericValue": 78.5,
      "Low": 78.2,
      "High": 78.8,
      "Comments": "",
      "Date": "2024-01-15T00:00:00+00:00",
      "TimeDimensionValue": "2019",
      "TimeDimensionBegin": "2019-01-01T00:00:00+00:00",
      "TimeDimensionEnd": "2019-12-31T00:00:00+00:00"
    }
  ]
}
```

### 3. Filter by Country

Use OData `$filter` to restrict results by country (SpatialDim).

**Example (life expectancy for USA only):**
```
https://ghoapi.azureedge.net/api/WHOSIS_000001?$filter=SpatialDim eq 'USA'
```

**Example (life expectancy for multiple countries):**
```
https://ghoapi.azureedge.net/api/WHOSIS_000001?$filter=SpatialDim eq 'USA' or SpatialDim eq 'GBR' or SpatialDim eq 'JPN'
```

### 4. Filter by Year

**Example (life expectancy in 2019):**
```
https://ghoapi.azureedge.net/api/WHOSIS_000001?$filter=TimeDim eq 2019
```

**Example (life expectancy for USA since 2015):**
```
https://ghoapi.azureedge.net/api/WHOSIS_000001?$filter=SpatialDim eq 'USA' and TimeDim ge 2015
```

### 5. Filter by Sex/Dimension

**Example (life expectancy, both sexes, USA, 2015+):**
```
https://ghoapi.azureedge.net/api/WHOSIS_000001?$filter=SpatialDim eq 'USA' and TimeDim ge 2015 and Dim1 eq 'BTSX'
```

Dim1 sex values: `BTSX` (both sexes), `MLE` (male), `FMLE` (female).

### 6. Pagination and Limiting

**Example (first 10 results):**
```
https://ghoapi.azureedge.net/api/WHOSIS_000001?$top=10
```

**Example (skip first 100, get next 50):**
```
https://ghoapi.azureedge.net/api/WHOSIS_000001?$top=50&$skip=100
```

### 7. Select Specific Fields

```
https://ghoapi.azureedge.net/api/WHOSIS_000001?$filter=SpatialDim eq 'USA'&$select=SpatialDim,TimeDim,NumericValue,Dim1
```

### 8. Order Results

```
https://ghoapi.azureedge.net/api/WHOSIS_000001?$filter=SpatialDim eq 'USA'&$orderby=TimeDim desc
```

### 9. List Dimension Values

```
GET /DIMENSION/{DimensionType}/DimensionValues
```

**Example (list all countries):**
```
https://ghoapi.azureedge.net/api/DIMENSION/COUNTRY/DimensionValues
```

**Example (list all regions):**
```
https://ghoapi.azureedge.net/api/DIMENSION/REGION/DimensionValues
```

**Example (list sex dimension values):**
```
https://ghoapi.azureedge.net/api/DIMENSION/SEX/DimensionValues
```

---

## Common Indicator Codes

### Life Expectancy & Mortality
| Code | Description |
|------|-------------|
| `WHOSIS_000001` | Life expectancy at birth (years) |
| `WHOSIS_000002` | Healthy life expectancy (HALE) at birth (years) |
| `WHOSIS_000004` | Neonatal mortality rate (per 1000 live births) |
| `MDG_0000000001` | Infant mortality rate (per 1000 live births) |
| `MDG_0000000007` | Under-five mortality rate (per 1000 live births) |
| `MORT_MATERNALNUM` | Number of maternal deaths |
| `MDG_0000000026` | Maternal mortality ratio (per 100000 live births) |
| `NCDMORT3070` | Probability of dying from NCDs between ages 30-70 |
| `LIFE_0000000029` | Adult mortality rate (probability of dying 15-60) |

### Communicable Diseases
| Code | Description |
|------|-------------|
| `WHS3_49` | HIV prevalence (% of population ages 15-49) |
| `MDG_0000000029` | Tuberculosis incidence (per 100,000) |
| `MALARIA_EST_INCIDENCE` | Malaria incidence (per 1000 population at risk) |
| `WHS3_62` | New HIV infections (per 1000 uninfected population) |

### Immunization
| Code | Description |
|------|-------------|
| `WHS4_100` | Measles (MCV1) immunization (% of 1-year-olds) |
| `WHS4_117` | DTP3 immunization (% of 1-year-olds) |
| `WHS4_129` | Hepatitis B (HepB3) immunization (%) |
| `WHS4_543` | Polio (Pol3) immunization (% of 1-year-olds) |

### Non-Communicable Diseases & Risk Factors
| Code | Description |
|------|-------------|
| `NCD_BMI_30A` | Prevalence of obesity (BMI >= 30), age-standardized |
| `NCD_HYP_PREVALENCE_A` | Prevalence of raised blood pressure |
| `NCD_GLUC_04` | Prevalence of diabetes (% of population) |
| `M_Est_smk_curr_std` | Prevalence of current tobacco smoking |
| `SA_0000001462` | Total alcohol per capita consumption (litres) |

### Health Systems
| Code | Description |
|------|-------------|
| `HWF_0001` | Medical doctors (per 10,000 population) |
| `HWF_0006` | Nursing and midwifery personnel (per 10,000) |
| `WHS7_104` | Hospital beds (per 10,000 population) |
| `GHED_CHE_pc_US_SHA2011` | Current health expenditure per capita (USD) |
| `UHC_INDEX_REPORTED` | UHC service coverage index |

### Environmental Health
| Code | Description |
|------|-------------|
| `SDGPM25` | PM2.5 air pollution, mean annual exposure (ug/m3) |
| `WSH_SANITATION_SAFELY_MANAGED` | Safely managed sanitation services (%) |
| `WSH_WATER_SAFELY_MANAGED` | Safely managed drinking water services (%) |

---

## Country Codes (ISO 3166-1 alpha-3)

The GHO API uses **ISO 3-letter codes** for countries in the `SpatialDim` field.

`USA` (United States), `GBR` (United Kingdom), `DEU` (Germany), `FRA` (France), `JPN` (Japan), `CHN` (China), `IND` (India), `BRA` (Brazil), `ZAF` (South Africa), `NGA` (Nigeria), `AUS` (Australia), `CAN` (Canada), `KOR` (Republic of Korea), `MEX` (Mexico), `RUS` (Russian Federation)

WHO Regions: `AFR` (Africa), `AMR` (Americas), `SEAR` (South-East Asia), `EUR` (Europe), `EMR` (Eastern Mediterranean), `WPR` (Western Pacific), `GLOBAL` (Global)

---

## Response Format
All responses are JSON following OData v4 conventions:

```json
{
  "@odata.context": "https://ghoapi.azureedge.net/api/$metadata#...",
  "value": [
    { ... observation object ... },
    { ... observation object ... }
  ]
}
```

Key fields in each observation:
- `SpatialDim`: Country/region code (ISO alpha-3)
- `TimeDim`: Year (integer)
- `NumericValue`: The numeric data value (float or null)
- `Value`: String representation of the value
- `Low` / `High`: Confidence interval bounds (when available)
- `Dim1`: First additional dimension (often sex: `BTSX`, `MLE`, `FMLE`)
- `Dim2`, `Dim3`: Additional dimensions (age group, etc.)

## Notes
- The API uses OData v4 syntax. Filter operators: `eq`, `ne`, `gt`, `ge`, `lt`, `le`, `and`, `or`, `not`. String values must be in single quotes.
- Not all indicators have data for all countries or years. Check data availability before building dependent workflows.
- `NumericValue` is preferred over `Value` for numeric analysis; `Value` is a string and may contain qualifiers.
- Many indicators are disaggregated by sex (`Dim1`) and/or age group (`Dim2`). Use the dimension values endpoint to discover valid codes.
- Data may have multi-year lag, especially for lower-income countries.
- The `Low` and `High` fields provide uncertainty intervals from WHO estimation processes (not all indicators have these).
- For bulk exploration, the GHO data portal at https://www.who.int/data/gho provides a browsable interface to find indicator codes.
