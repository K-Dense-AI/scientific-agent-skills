# Sources and Verification Notes

Research date: **2026-09-30**.

Official LabArchives help pages were read through the web tool. The shared API
notebook was read with fresh `parallel-cli extract` requests and by navigating
its public tree in Chrome, because basic extraction returned an empty shell
and one container-page extraction redirected to login. Browser reading resolved
that gap without authentication. PyPI and GitHub public metadata were checked
for optional community clients. No authenticated API requests, remote writes,
or product-integration transfers were performed.

## Official API sources

### ELN overview and regional API hosts

https://mynotebook.labarchives.com/share/LabArchives%20API/NS4yfDI3LzQvVHJlZU5vZGUvMTF8MTMuMg

- Page revision: **2025-11-03**
- Describes the ELN API as REST-like.
- Lists API hosts for US/rest of world, Australia/New Zealand, UK, Europe
  outside the UK, and Canada.
- Requires HTTPS.
- States that many responses are XML and child-element order is not fixed.

### Requirements and best practices

https://mynotebook.labarchives.com/share/LabArchives%20API/MTM2LjV8MjcvMTA1L1RyZWVOb2RlLzM2MzY3OTM2NjF8MzQ2LjU=

- Page revision: **2024-06-28**
- Credentials are issued for a specific organization/vendor and purpose.
- Large batches must be serialized or staggered by at least one second.
- HTTP 4xx responses must not be automatically retried.
- Eligible retries must wait at least one second, back off, and stop at a
  bounded count/duration.
- `expires` should represent current epoch milliseconds, with server-clock
  adjustment, not a future expiry.

### Call authentication

https://mynotebook.labarchives.com/share/LabArchives%20API/Ny44fDI3LzYvVHJlZU5vZGUvMTE1MzU5MTAyNXwxOS44

- Page revision: **2023-05-10**
- Defines Base64(HMAC-SHA-512) over the concatenation of Access Key ID, method
  input, and `expires`, using the Access Password as the HMAC key.
- Documents `akid`, `expires`, and URI-encoded `sig` query parameters.
- The published dummy test vector is reproduced by
  `scripts/entry_operations.py self-test`.

### API user login and UID

https://mynotebook.labarchives.com/share/LabArchives%20API/ODEuOXwyNy82My05My9UcmVlTm9kZS8yMjYyMTU0MTg3fDIwNy44OTk5OTk5OTk5OTk5OA==

- Page revision: **2023-03-03**
- Documents the signed `/api_user_login` redirect, returned `auth_code` and
  email, and redemption through `users::user_access_info`.
- Defines the user-generated temporary password token alternative.
- States that UIDs are bound to the Access Key ID and persist until revoked.

### ELN API class tree

https://mynotebook.labarchives.com/share/LabArchives%20API/MS4zfDI3LzEvVHJlZU5vZGUvODYxMDc1MjB8My4z

- Current tree includes entries, search tools, utilities, users, tree tools,
  notifications, notebooks, and site-license tools.
- Method pages, not names inferred from other clients, are the source of truth.

### ELN entry response elements

https://mynotebook.labarchives.com/share/LabArchives%20API/NjguOXwyNy81My9UcmVlTm9kZS8xODUxMDkwNDk2fDE3NC45

- Documents common `<entry>` XML fields and optional entry/comment data.
- Distinguishes attachment metadata from retrieval of attachment bytes.

### LA container file

https://mynotebook.labarchives.com/share/LabArchives%20API/Ni41fDI3LzUvVHJlZU5vZGUvNDQ3MDk3MTI0fDE2LjU=

- Original page revision shown as **2014-11-10**; the public page also contained
  an example-file revision dated **2026-03-02** at research time.
- Defines an LA container as a ZIP with `lamanifest.xml`, an application file,
  preview file, and UTF-8 index file.
- This format is not the same thing as a notebook-backup response.

### Inventory authentication

https://mynotebook.labarchives.com/share/LabArchives%20API/MTQ0LjN8MjcvMTExL1RyZWVOb2RlLzM5NjYzNjc4MjJ8MzY2LjI5OTk5OTk5OTk5OTk1

- Page revision: **2025-11-24**
- Inventory uses the shared LabArchives authentication flow.
- Requires a new signature for each exact relative route.
- Lists `X-LabArchives-UId`, `X-LabArchives-AKId`,
  `X-LabArchives-LabId`, `X-LabArchives-Signature`, and
  `X-LabArchives-Expires`.
- Route parameters are included in the signature input; query parameters are
  excluded. The method-specific `users/me` exception omits the Lab ID header.

### Inventory API v1 item creation

https://mynotebook.labarchives.com/share/LabArchives%20API/MTg4LjV8MjcvMTQ1L1RyZWVOb2RlLzEyOTcxODY5ODF8NDc4LjU=

- Page revision: **2026-04-02**
- The public navigation labels the Inventory surface **APIs (v1)**.
- Explicitly documents `POST /public/v1/inventory` and its JSON body fields.
- The navigation also exposes read/update item routes and sections for item
  types, orders, storage locations, and vendors.

### Method-level audit

Opened every endpoint named by this skill through **ELN API Classes** or
**Inventory > APIs (v1)** in the official notebook:

- `entries/entry_info`: GET, `uid`/`eid`, optional data/comment flags; XML.
- `entries/entry_attachment`: GET, `uid`/`eid`, raw application file and
  `Content-Disposition`, not an LA container ZIP.
- `notebooks/notebook_backup`: GET, owner `uid`/`nbid`, optional `json` and
  `no_attachments`; `.7z` archive. Internal archive schema remains access-gated.
- `users/user_access_info`: GET, `login_or_email` and authorization-code/token
  `password`, signed query; returns UID and auto-login permission in XML.
- `users/user_info_via_id`: GET with UID; honor auto-login permission and the
  documented restricted purpose of `authenticated=true`.
- `utilities/epoch_time`: GET with `akid`, no `sig`/`expires`; epoch milliseconds.
- `utilities/api_base_urls`: signed GET; XML region URL/description list. Its
  older example uses browser hosts, inconsistent with the newer API overview.
- Inventory `GET /public/v1/users/me`: lab discovery, no Lab ID needed;
  https://mynotebook.labarchives.com/share/LabArchives%20API/MTQ4LjIwMDAwMDAwMDAwMDAyfDI3LzExNC9UcmVlTm9kZS8zODc0Mjc0OTI5fDM3Ni4y
- Inventory `GET /public/v1/inventory`: JSON array, `pageSize` at most 1000,
  `pageNumber`, optional filters; out-of-stock items excluded by default.
  Page-number origin/default and stable ordering are not specified.
- Inventory `GET /public/v1/inventory/{itemId}`: one item JSON object, no query;
  https://mynotebook.labarchives.com/share/LabArchives%20API/MTg0LjZ8MjcvMTQyLTIyMC9UcmVlTm9kZS8zMzkzMTkwNjY5fDQ2OC41OTk5OTk5OTk5OTk5Nw==
- Inventory `GET /public/v1/inventory/{itemId}/attachments`: ZIP bytes.
- Inventory POST create and update: `name` and `typeId` marked required, HTTP
  200 item detail; examples include comments that must be removed for valid JSON.

**Inventory > Overview** explicitly publishes `https://iapi.labarchives.com`,
request `Content-Type: application/json`, JSON/ZIP response media types, and
v1 version/deprecation policy. It does not provide a regional variant table.
Navigate there from the official notebook linked above; navigation does not
update its address bar, so the method titles identify the pages read.

Additional direct method sources:

- https://mynotebook.labarchives.com/share/LabArchives%2520API/MjAuOHwyNy8xNi9UcmVlTm9kZS8xMTk0MTIyNDl8NTIuOA==
- https://mynotebook.labarchives.com/share/LabArchives%2520API/MjIuMXwyNy8xNy9UcmVlTm9kZS8yODM1OTg2MjY1fDU2LjE=
- https://mynotebook.labarchives.com/share/LabArchives%2520API/MTQuM3wyNy8xMS9UcmVlTm9kZS8yMTI3OTAwNDQzfDM2LjM=
- https://mynotebook.labarchives.com/share/LabArchives%2520API/MTEwLjV8MjcvODUtMTM5L1RyZWVOb2RlLzk0NjQ2ODg4MXwyODAuNQ==

## Official product and help sources

### Regional browser login URLs

https://help.labarchives.com/hc/en-us/articles/11728160845332-Using-an-Institutional-Single-Sign-on-for-LabArchives-Access

- Updated **2025-11-04**
- Lists separate login URLs for US/rest of world, Canada,
  Australia/New Zealand, UK, and Europe.

### ELN API entitlement

https://help.labarchives.com/hc/en-us/articles/11723701830676-ELN-for-Research-Introduction-and-Subscription-Plans

- Updated **2026-08-27**
- Lists developer API access under the Enterprise plan.

### Inventory API entitlement

https://help.labarchives.com/hc/en-us/articles/11811035048212-Inventory-FAQs

- Updated **2026-05-19**
- Limits API availability to Enterprise and Enterprise Plus licensees.
- Requires Inventory account/API access and directs eligible users to support.

### Integration index

https://help.labarchives.com/hc/en-us/sections/11732611360660-Integrations

Current index at research time included GraphPad Prism, SnapGene, Geneious,
Proofig AI, Jupyter, REDCap, Protocols.io, Qeios, SciSpace, Vernier Logger Pro,
and DataCite.

Selected dated articles:

- Jupyter, updated **2025-09-08**:
  https://help.labarchives.com/hc/en-us/articles/11780569021972-Jupyter-Integration
- REDCap, updated **2025-09-05**:
  https://help.labarchives.com/hc/en-us/articles/11780613160980-REDCap-Integration
- Protocols.io, updated **2025-09-22**:
  https://help.labarchives.com/hc/en-us/articles/11780572389524-Protocols-io-Integration

## Community Python client status

Community projects are not official LabArchives sources and are not installed by
this skill.

### `mcmero/labarchives-py`

https://github.com/mcmero/labarchives-py

GitHub metadata checked **2026-09-30**:

- personal/community repository, not LabArchives-owned,
- last commit: **2022-08-10** (`1b5b745baaf9`),
- no tags,
- no GitHub releases,
- no official LabArchives endorsement found.

Conclusion: remove the old unpinned Git clone installation and do not recommend
this wrapper by default.

### `nimh-dsst/labapi`

- PyPI: https://pypi.org/project/labapi/
- Source: https://github.com/nimh-dsst/labapi
- Documentation: https://nimh-dsst.github.io/labapi/

Verified status on **2026-09-30** using project-owned PyPI/GitHub metadata:

- NIMH DSST community project, not LabArchives-owned;
- stable release **1.2.0**, published **2026-08-20** on PyPI and GitHub;
- Python requirement **>=3.10**;
- current PyPI `license_expression` and GitHub license both identify **MIT**;
- no official LabArchives endorsement was identified in the reviewed vendor docs.

Metadata sources:

- https://pypi.org/pypi/labapi/json
- https://api.github.com/repos/nimh-dsst/labapi/releases
- https://api.github.com/repos/nimh-dsst/labapi/license

This review checked release metadata, not client execution or transitive
behavior. Adoption remains a separate institution-reviewed choice. Pin the
selected release and inspect its credential-loading behavior; the bundled
standard-library tools do not import or require this client.

## Claims not established by public official sources

The research did **not** establish:

- an Inventory regional base-URL table beyond the published `iapi.labarchives.com`,
- the Inventory list endpoint's page-number origin/default or stable ordering,
- a numeric requests-per-minute or burst quota,
- a generic LabArchives OAuth 2.0 authorization/token endpoint,
- an official LabArchives Python SDK,
- a blanket backward-compatibility guarantee for the legacy ELN API,
- universal attachment extensions, file-size limits, or archive formats,
- that every advertised product integration exposes a programmable API.

Obtain missing product-specific details from institution/vendor-provided API
documentation or LabArchives support. Do not fill gaps from model memory or a
community wrapper.
