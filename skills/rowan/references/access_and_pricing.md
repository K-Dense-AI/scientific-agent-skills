# Access, Pricing, and Credits

Reviewed 2026-09-30 against [Rowan's official pricing page](https://rowansci.com/pricing).
These are dated published terms, not a live account quote.

- All users can create API keys. Free access covers core workflows; it does not
  include every function exported by the Python package.
- The public FAQ lists 500 signup credits and 20 credits per week for the general
  free tier. Academic/team allowances differ; inspect the account's plan.
- Listed compute rates are 1 credit/minute for CPU, 3 for GPU, and 7 for H100/H200.
- The page lists purchased credits at US$0.04 each, expiring up to one year after purchase.
- Advanced access includes macropKa, MSA, membrane permeability, protein/pose MD,
  and batch docking; FEP is listed under enterprise/group offerings.

Check the current account rather than inferring entitlement from the importable SDK:

```python
import rowan
user = rowan.whoami()
print(user.credits_available_string())
print(user.enabled_workflows)
# These are backend slugs; for example protein MD is molecular_dynamics.
```

There is no validated per-workflow runtime/cost table in this skill. Molecular
size, conformer counts, model/hardware, settings, and downstream calculations
change usage. Use a representative pilot and inspect its charged credits, then
budget the full campaign. Submission `max_credits` is a per-workflow ceiling;
set it explicitly where appropriate, but do not mistake it for a campaign-wide
limit or a guarantee the job can finish within that amount. Confirm account
limits and current terms before scaling up.
