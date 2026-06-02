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
    "kmValue*", "substrate*", "literature*"
)
```

## Response Format
Returns string parsed with `!` (record separator) and `#`/`*` (field separators). Must be parsed manually.

## Rate Limits
No published limits. SOAP responses can take 1-5 seconds. Be respectful — free academic service.

## Note for this skill
Since BRENDA uses SOAP (not REST), making calls requires writing and executing a Python script with `zeep`. Use Bash to run the script rather than WebFetch.
