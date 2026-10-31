# BRENDA Enzyme Database (SOAP API)

## Important: BRENDA uses SOAP, not REST. Requires Python with `zeep` library.

## SOAP Endpoint
```
https://www.brenda-enzymes.org/soap/brenda_zeep.wsdl
```

## Auth
Free registration required at https://www.brenda-enzymes.org/register.php
Credentials (email + SHA-256 hashed password) passed with every call.

## Key SOAP Methods

All methods take `email`, `password` (SHA-256), and `ecNumber` as base parameters.

| Method | Description |
|--------|-------------|
| `getKmValue` | Michaelis constant (Km) |
| `getTurnoverNumber` | Turnover number (kcat) |
| `getKcatKmValue` | Catalytic efficiency (kcat/Km) |
| `getKiValue` | Inhibition constant (Ki) |
| `getIc50Value` | IC50 values |
| `getSpecificActivity` | Specific activity |
| `getPhOptimum` | pH optimum |
| `getTemperatureOptimum` | Temperature optimum |
| `getSubstrate` | Substrates |
| `getProduct` | Products |
| `getInhibitors` | Inhibitors |
| `getCofactor` | Cofactors |
| `getOrganism` | Source organisms |
| `getReaction` | Reaction equations |
| `getSequence` | Protein sequences |
| `getDisease` | Associated diseases |

## Parameter Syntax
`fieldName*value` format. Empty value = return all.

```
ecNumber*1.1.1.1           # Required: EC number
organism*Homo sapiens      # Optional: filter by organism
substrate*ethanol          # Optional: filter by substrate
kmValue*                   # Return field (empty = all)
```

## Python Example
```python
import hashlib
from zeep import Client

client = Client("https://www.brenda-enzymes.org/soap/brenda_zeep.wsdl")
email = "your@email.com"
password = hashlib.sha256("your_password".encode()).hexdigest()

# Get Km values for alcohol dehydrogenase
result = client.service.getKmValue(
    email, password,
    "ecNumber*1.1.1.1", "organism*Homo sapiens",
    "kmValue*", "kmValueMaximum*", "substrate*", "commentary*",
    "ligandStructureId*", "literature*"
)
```

## Response Format
The `brenda_zeep.wsdl` binding returns typed records, including `kmValue`,
`kmValueMaximum`, `organism`, and `substrate` for `getKmValue`. Serialize with
`zeep.helpers.serialize_object` when needed. The delimiter-separated string
format belongs to the older `brenda.wsdl` interface; do not apply that parser to
Zeep record objects. Each method has its own ordered arguments: inspect its WSDL
signature instead of reusing the Km parameter tuple for every method.

## Rate Limits
BRENDA requests at most **one request per second**. The online service is
CC BY 4.0; registration is required. The authenticated example is illustrative
and was not executed during this documentation review.

Reviewed 2026-09-30: [official SOAP help](https://www.brenda-enzymes.org/soap.php)
and the linked Zeep WSDL.

## Note for this skill
Since BRENDA uses SOAP (not REST), making calls requires writing and executing a Python script with `zeep`. Use Bash to run the script rather than WebFetch.
