# Data Enrichment

Enrich: $ARGUMENTS

## Before starting

Inform the user that enrichment may take several minutes depending on the number of rows and fields requested.

## Step 1: Start the enrichment

Use ONE of these command patterns (substitute user's actual data):

For inline data:

```bash
parallel-cli enrich run --data '[{"company": "Google"}, {"company": "Microsoft"}]' --intent "CEO name and founding year" --target "output.json" --no-wait --json
```

For CSV file:

```bash
parallel-cli enrich run --source-type csv --source "input.csv" --target "/tmp/output.json" --source-columns '[{"name": "company", "description": "Company name"}]' --intent "CEO name and founding year" --no-wait --json
```

If this is a **follow-up** to a previous research or enrichment task where you know the `interaction_id`, add context chaining:

```bash
parallel-cli enrich run --data '...' --intent "..." --target "output.json" --no-wait --json --previous-interaction-id "$INTERACTION_ID"
```

By chaining `interaction_id` values across requests, each follow-up automatically has the full context of prior turns — so you can enrich entities discovered in earlier research without restating what was already found.

**IMPORTANT:** Always include `--no-wait` so the command returns immediately instead of blocking.

Parse the output to extract the `taskgroup_id`, `interaction_id`, and monitoring URL. Immediately tell the user:
- Enrichment has been kicked off
- The monitoring URL where they can track progress

Tell them they can background the polling step to continue working while it runs.

## Step 2: Poll for results

Choose a short, descriptive filename based on the enrichment task (e.g., `companies-ceos`, `startups-funding`). Use lowercase with hyphens, no spaces.

```bash
parallel-cli enrich poll "$TASKGROUP_ID" --timeout 540 --json --output "$FILENAME.json"
```

The `--target` flag on `enrich run` does not carry over to the poll — you must pass `--output` here to save the results. Always use `--json` to get structured JSON output.

Important:
- Use `--timeout 540` (9 minutes) to stay within tool execution limits

### If the poll times out

Enrichment of large datasets can take longer than 9 minutes. If the poll exits without completing:
1. Tell the user the enrichment is still running server-side
2. Re-run the same `parallel-cli enrich poll` command to continue waiting

## Response format

**After step 1:** Share the monitoring URL (for tracking progress).

**After step 2:**
1. Report number of rows enriched
2. Preview first few rows of the output JSON
3. Tell user the full path to the output JSON file (`$FILENAME.json`)
4. Share the `interaction_id` and tell the user they can ask follow-up questions that build on this enrichment

Do NOT re-share the monitoring URL after completion — the results are in the output file.

**Remember the `interaction_id`** — if the user asks a follow-up question that relates to this enrichment, use it as `--previous-interaction-id` in the next research or enrichment command.
