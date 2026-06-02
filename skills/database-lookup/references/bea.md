# BEA (Bureau of Economic Analysis) API Reference

## Overview
The Bureau of Economic Analysis API provides access to U.S. economic accounts data including GDP (national income and product accounts -- NIPA), personal income, international trade, industry accounts, and regional economic data. Structured as a single endpoint with dataset-specific parameters.

## Base URL
```
https://apps.bea.gov/api/data
```

## Authentication
- **API Key: REQUIRED.** Register at https://apps.bea.gov/API/signup/
- Pass as query parameter: `&UserID=YOUR_API_KEY`

## Rate Limits
- **100 requests per minute** per API key.
- **100 MB of data per minute** per API key.
- **30 errors per minute** -- exceeding triggers a temporary lockout.
- Daily and monthly limits are not formally published but BEA may throttle heavy use.

## Common Parameters (all requests)
| Parameter  | Type   | Required | Description |
|-----------|--------|----------|-------------|
| `UserID`  | string | Yes      | Your BEA API key. |
| `method`  | string | Yes      | API method (see below). |
| `ResultFormat` | string | No  | `JSON` (default) or `XML`. |

---

## Methods

### 1. GetDataSetList
Lists all available datasets.

#### `GET /api/data?method=GetDataSetList&UserID=YOUR_KEY&ResultFormat=JSON`

**Example:**
```
https://apps.bea.gov/api/data?method=GetDataSetList&UserID=YOUR_KEY&ResultFormat=JSON
```

**Response:**
```json
{
  "BEAAPI": {
    "Request": {
      "RequestParam": [
        {"ParameterName": "METHOD", "ParameterValue": "GETDATASETLIST"},
        {"ParameterName": "RESULTFORMAT", "ParameterValue": "JSON"}
      ]
    },
    "Results": {
      "Dataset": [
        {"DatasetName": "NIPA", "DatasetDescription": "Standard NIPA tables"},
        {"DatasetName": "NIUnderlyingDetail", "DatasetDescription": "National Income and Product Accounts Underlying Detail"},
        {"DatasetName": "MNE", "DatasetDescription": "Multinational Enterprises"},
        {"DatasetName": "FixedAssets", "DatasetDescription": "Fixed Assets"},
        {"DatasetName": "ITA", "DatasetDescription": "International Transactions"},
        {"DatasetName": "IIP", "DatasetDescription": "International Investment Position"},
        {"DatasetName": "GDPbyIndustry", "DatasetDescription": "GDP by Industry"},
        {"DatasetName": "Regional", "DatasetDescription": "Regional data"},
        {"DatasetName": "UnderlyingGDPbyIndustry", "DatasetDescription": "Underlying GDP by Industry"},
        {"DatasetName": "InputOutput", "DatasetDescription": "Input-Output Statistics"}
      ]
    }
  }
}
```

---

### 2. GetParameterList
Lists parameters for a specific dataset.

#### `GET /api/data?method=GetParameterList&DatasetName={dataset}&UserID=YOUR_KEY&ResultFormat=JSON`

**Example:**
```
https://apps.bea.gov/api/data?method=GetParameterList&DatasetName=NIPA&UserID=YOUR_KEY&ResultFormat=JSON
```

**Response:**
```json
{
  "BEAAPI": {
    "Results": {
      "Parameter": [
        {
          "ParameterName": "TableName",
          "ParameterDataType": "string",
          "ParameterDescription": "The standard NIPA table identifier",
          "ParameterIsRequiredFlag": "1",
          "ParameterDefaultValue": ""
        },
        {
          "ParameterName": "Frequency",
          "ParameterDataType": "string",
          "ParameterDescription": "A - Annual, Q - Quarterly, M - Monthly",
          "ParameterIsRequiredFlag": "1",
          "ParameterDefaultValue": ""
        },
        {
          "ParameterName": "Year",
          "ParameterDataType": "string",
          "ParameterDescription": "List of year(s) of data to retrieve",
          "ParameterIsRequiredFlag": "1",
          "ParameterDefaultValue": ""
        }
      ]
    }
  }
}
```

---

### 3. GetParameterValues
Lists valid values for a parameter.

#### `GET /api/data?method=GetParameterValues&DatasetName={dataset}&ParameterName={param}&UserID=YOUR_KEY&ResultFormat=JSON`

**Example (list NIPA tables):**
```
https://apps.bea.gov/api/data?method=GetParameterValues&DatasetName=NIPA&ParameterName=TableName&UserID=YOUR_KEY&ResultFormat=JSON
```

**Response (abbreviated):**
```json
{
  "BEAAPI": {
    "Results": {
      "ParamValue": [
        {"TableName": "T10101", "Description": "Table 1.1.1. Percent Change From Preceding Period in Real Gross Domestic Product"},
        {"TableName": "T10106", "Description": "Table 1.1.6. Real Gross Domestic Product, Chained Dollars"},
        {"TableName": "T10105", "Description": "Table 1.1.5. Gross Domestic Product"},
        {"TableName": "T20100", "Description": "Table 2.1. Personal Income and Its Disposition"},
        {"TableName": "T30100", "Description": "Table 3.1. Government Current Receipts and Expenditures"}
      ]
    }
  }
}
```

---

### 4. GetData
The main data retrieval method. Parameters vary by dataset.

#### `GET /api/data?method=GetData&DatasetName={dataset}&{params}&UserID=YOUR_KEY&ResultFormat=JSON`

---

## Dataset-Specific Parameters & Examples

### A. NIPA (National Income and Product Accounts)

**Parameters:**
| Parameter   | Type   | Required | Description |
|------------|--------|----------|-------------|
| `TableName`| string | Yes      | NIPA table identifier (e.g., `T10101`). |
| `Frequency`| string | Yes      | `A` (annual), `Q` (quarterly), `M` (monthly). |
| `Year`     | string | Yes      | Comma-separated years, or `ALL`, or `X` for latest. |

**Example (Real GDP percent change, quarterly, 2022-2024):**
```
https://apps.bea.gov/api/data?method=GetData&DatasetName=NIPA&TableName=T10101&Frequency=Q&Year=2022,2023,2024&UserID=YOUR_KEY&ResultFormat=JSON
```

**Example (GDP levels, annual, all years):**
```
https://apps.bea.gov/api/data?method=GetData&DatasetName=NIPA&TableName=T10105&Frequency=A&Year=ALL&UserID=YOUR_KEY&ResultFormat=JSON
```

**Response:**
```json
{
  "BEAAPI": {
    "Request": { ... },
    "Results": {
      "Statistic": "NIPA Table",
      "UTCProductionTime": "2024-11-01T13:00:00.000",
      "Dimensions": [
        {"Name": "TableName", "DataType": "string", "IsValue": "0"},
        {"Name": "SeriesCode", "DataType": "string", "IsValue": "0"},
        {"Name": "LineNumber", "DataType": "numeric", "IsValue": "0"},
        {"Name": "LineDescription", "DataType": "string", "IsValue": "0"},
        {"Name": "TimePeriod", "DataType": "string", "IsValue": "0"},
        {"Name": "METRIC_NAME", "DataType": "string", "IsValue": "0"},
        {"Name": "CL_UNIT", "DataType": "string", "IsValue": "0"},
        {"Name": "UNIT_MULT", "DataType": "numeric", "IsValue": "0"},
        {"Name": "DataValue", "DataType": "numeric", "IsValue": "1"}
      ],
      "Data": [
        {
          "TableName": "T10101",
          "SeriesCode": "A191RL",
          "LineNumber": "1",
          "LineDescription": "Gross domestic product",
          "TimePeriod": "2022Q1",
          "METRIC_NAME": "Fisher Quantity Index",
          "CL_UNIT": "Percent change",
          "UNIT_MULT": "0",
          "DataValue": "-1.6",
          "NoteRef": "T10101"
        },
        {
          "TableName": "T10101",
          "SeriesCode": "A191RL",
          "LineNumber": "1",
          "LineDescription": "Gross domestic product",
          "TimePeriod": "2022Q2",
          "CL_UNIT": "Percent change",
          "DataValue": "-0.6"
        }
      ],
      "Notes": [
        {"NoteRef": "T10101", "NoteText": "Table 1.1.1. Percent Change From Preceding Period..."}
      ]
    }
  }
}
```

---

### B. Regional (State, County, MSA data)

**Parameters:**
| Parameter     | Type   | Required | Description |
|--------------|--------|----------|-------------|
| `TableName`  | string | Yes      | Regional table (e.g., `CAGDP1` for GDP by state). |
| `LineCode`   | int    | Yes      | Line number within the table (specifies the data series). |
| `GeoFips`    | string | Yes      | FIPS code: `STATE` (all states), `COUNTY` (all counties), `MSA` (all MSAs), or specific FIPS (e.g., `06000` for California). |
| `Year`       | string | Yes      | Comma-separated years or `ALL` or `LAST5`. |

**Common Regional Tables:**
| Table | Description |
|-------|-------------|
| `CAGDP1` | GDP summary by state |
| `CAGDP2` | GDP by component by state |
| `CAGDP9` | Real GDP by state |
| `CAINC1` | Personal income summary by state |
| `CAINC4` | Personal income and employment by state |
| `CAINC5N` | Personal income by type by state |
| `SAINC1` | State annual personal income |
| `SQINC1` | State quarterly personal income |

**Example (GDP by state, all states, 2020-2023):**
```
https://apps.bea.gov/api/data?method=GetData&DatasetName=Regional&TableName=CAGDP1&LineCode=1&GeoFips=STATE&Year=2020,2021,2022,2023&UserID=YOUR_KEY&ResultFormat=JSON
```

**Example (Personal income for California):**
```
https://apps.bea.gov/api/data?method=GetData&DatasetName=Regional&TableName=CAINC1&LineCode=1&GeoFips=06000&Year=LAST5&UserID=YOUR_KEY&ResultFormat=JSON
```

**Response:**
```json
{
  "BEAAPI": {
    "Results": {
      "Data": [
        {
          "GeoFips": "06000",
          "GeoName": "California",
          "Code": "CAINC1-1",
          "TimePeriod": "2023",
          "CL_UNIT": "Thousands of dollars",
          "UNIT_MULT": "3",
          "DataValue": "3,220,965,123"
        }
      ]
    }
  }
}
```

---

### C. ITA (International Transactions Accounts / Trade)

**Parameters:**
| Parameter    | Type   | Required | Description |
|-------------|--------|----------|-------------|
| `Indicator` | string | Yes      | Indicator code (e.g., `BalGds` for goods balance). |
| `AreaOrCountry` | string | Yes  | Country code: `AllCountries`, `China`, `Japan`, etc., or `All`. |
| `Frequency` | string | Yes      | `A`, `Q`, `M`. |
| `Year`      | string | Yes      | Comma-separated years or `ALL`. |

**Common ITA Indicators:**
| Code | Description |
|------|-------------|
| `BalGds` | Balance on goods |
| `BalServ` | Balance on services |
| `BalGdsServ` | Balance on goods and services |
| `BalCurAcct` | Current account balance |
| `ExpGds` | Exports of goods |
| `ImpGds` | Imports of goods |
| `ExpServ` | Exports of services |
| `ImpServ` | Imports of services |

**Example (US trade balance in goods with China, quarterly):**
```
https://apps.bea.gov/api/data?method=GetData&DatasetName=ITA&Indicator=BalGds&AreaOrCountry=China&Frequency=Q&Year=2022,2023,2024&UserID=YOUR_KEY&ResultFormat=JSON
```

---

### D. GDPbyIndustry

**Parameters:**
| Parameter    | Type   | Required | Description |
|-------------|--------|----------|-------------|
| `TableID`   | int    | Yes      | Table number (1-15). |
| `Industry`  | string | Yes      | Industry code: `ALL`, or specific (e.g., `11` for agriculture). |
| `Frequency` | string | Yes      | `A` or `Q`. |
| `Year`      | string | Yes      | Comma-separated years or `ALL`. |

**Common Table IDs:**
| ID | Description |
|----|-------------|
| 1  | Value added by industry |
| 5  | Value added by industry as % of GDP |
| 6  | Real value added by industry |
| 7  | Percent change in real value added by industry |

**Example (Value added by all industries, annual):**
```
https://apps.bea.gov/api/data?method=GetData&DatasetName=GDPbyIndustry&TableID=1&Industry=ALL&Frequency=A&Year=2020,2021,2022,2023&UserID=YOUR_KEY&ResultFormat=JSON
```

---

### E. IIP (International Investment Position)

**Parameters:**
| Parameter       | Type   | Required | Description |
|----------------|--------|----------|-------------|
| `TypeOfInvestment` | string | Yes  | `ALL`, `FinAssetsExclFinDeriv`, etc. |
| `Component`    | string | Yes      | `ALL` or specific component. |
| `Frequency`    | string | Yes      | `A` or `Q`. |
| `Year`         | string | Yes      | Comma-separated years or `ALL`. |

**Example:**
```
https://apps.bea.gov/api/data?method=GetData&DatasetName=IIP&TypeOfInvestment=ALL&Component=ALL&Frequency=A&Year=2020,2021,2022,2023&UserID=YOUR_KEY&ResultFormat=JSON
```

---

### F. FixedAssets

**Parameters:**
| Parameter   | Type   | Required | Description |
|------------|--------|----------|-------------|
| `TableName`| string | Yes      | Fixed asset table ID. |
| `Year`     | string | Yes      | Comma-separated years or `ALL`. |

**Example:**
```
https://apps.bea.gov/api/data?method=GetData&DatasetName=FixedAssets&TableName=FAAt101&Year=ALL&UserID=YOUR_KEY&ResultFormat=JSON
```

---

## Key NIPA Table Reference

| TableName | Description |
|-----------|-------------|
| `T10101` | Percent change in real GDP |
| `T10105` | GDP (current dollars) |
| `T10106` | Real GDP (chained 2017 dollars) |
| `T10107` | GDP price index (percent change) |
| `T10110` | GDP price deflator |
| `T20100` | Personal income and its disposition |
| `T20301` | Personal consumption expenditures by type |
| `T20600` | Personal income and outlays |
| `T30100` | Government current receipts and expenditures |
| `T40100` | Foreign transactions in the national accounts |
| `T50100` | Saving and investment by sector |
| `T50105` | Saving and investment (real) |
| `T60100` | Corporate profits |
| `T70100` | GDP by major type of product |
| `T11000` | Real GDP, expanded detail |
| `T11200` | Contributions to GDP growth |

## GeoFips Reference (Common)
| FIPS | State |
|------|-------|
| `00000` | United States |
| `01000` | Alabama |
| `06000` | California |
| `12000` | Florida |
| `36000` | New York |
| `48000` | Texas |
| `STATE` | All states |
| `COUNTY` | All counties |
| `MSA` | All metropolitan statistical areas |

## Notes
- DataValue in responses is a string, sometimes with commas (e.g., `"3,220,965,123"`). Parse by removing commas.
- `Year=X` returns only the most recent year available.
- `Year=LAST5` returns the 5 most recent years.
- For NIPA tables, results contain multiple line items per table (different GDP components are different LineNumbers).
- The `GetParameterValues` method is essential for discovering valid table names, line codes, and indicator codes for each dataset.
- BEA also provides bulk download files at https://apps.bea.gov/iTable/ for interactive use.
- Time periods for quarterly data use format `2024Q1`, `2024Q2`, etc.
- All monetary values are in U.S. dollars unless otherwise specified. Units are indicated in `CL_UNIT` and `UNIT_MULT` fields.
