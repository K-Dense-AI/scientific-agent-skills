# DISGENET — Gene/variant–disease associations

Use the current [DISGENET documentation](https://www.disgenet.com/docs) and
[API/tools page](https://www.disgenet.com/Tools). The old disgenet.org API and
email/password login recipes are not the current integration contract.

Access is plan-dependent: the [Academic plan](https://www.disgenet.com/Plans)
exposes the curated subset; full-dataset API access requires an appropriate
subscription. Obtain a key and the current base URL, authorization-header
syntax and endpoint schema from the account's API documentation before running
requests. These authenticated details could not be independently verified in
this review, so no speculative URL or token exchange is provided.

For a reproducible retrieval, choose gene–disease (GDA) or variant–disease (VDA),
resolve the input identifier, and save source filters, release, evidence rows,
PMIDs, score fields and pagination metadata. Summary rows aggregate evidence;
inspect supporting evidence before making a mechanistic claim.

[Current score guidance](https://support.disgenet.com/support/solutions/articles/202000100283-what-are-the-gda-score-vda-score-disgenet-score-)
removes the former cap at 1. Do not treat the raw DISGENET score as a probability,
clamp it to [0,1], or confuse it with a normalized score. DSI measures disease
specificity and DPI pleiotropy; neither is causal evidence.
