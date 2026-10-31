# DrugBank APIs

DrugBank requires licensed API access; a website account does not imply an API
subscription. Use the product and quota authorized for your key.

For drug/target research, the [Discovery API](https://docs.drugbank.com/discovery/v1/)
base is `https://api.drugbank.com/discovery/v1`. Server-side authentication is
`Authorization: <DRUGBANK_API_KEY>` without a Bearer prefix. Responses are JSON.

| GET path | Purpose |
|---|---|
| `/drugs/DB00316` | Drug details |
| `/drugs?q=acetaminophen` | Search drugs |
| `/drugs/DB00316/bonds` | Target, enzyme, carrier and transporter bonds |
| `/bonds/targets` | Target bonds |
| `/polypeptides/P49189/bonds` | Bonds involving a UniProt protein |

Illustrative authenticated request (not executed):
```bash
curl --fail-with-body 'https://api.drugbank.com/discovery/v1/drugs/DB00316/bonds' \
  -H "Authorization: $DRUGBANK_API_KEY"
```

Bond responses are arrays with type, bio-entity, actions and references. Preserve
organism, action direction and evidence; a listed bond need not prove efficacy.

[Clinical API](https://docs.drugbank.com/v1/) calls use `https://api.drugbank.com/v1`
and a different endpoint catalogue (including `/ddi`). Do not move Discovery
routes under that base. Browser applications require short-lived tokens issued
by a trusted backend; never embed the secret API key in a browser.
