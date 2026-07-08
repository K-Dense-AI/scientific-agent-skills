# Deep Research

Research topic: $ARGUMENTS

## When to use (vs web search)

ONLY use this capability when the user explicitly requests deep/exhaustive research. Deep research takes **15–30 minutes** (sometimes up to 60 minutes) and is significantly more expensive than web search. For normal "research X" requests, quick lookups, or fact-checking, use **web search** instead.

## Step 1: Start the research

Frame the research objective to prioritize academic literature. If the user's query is scientific or technical, prepend context that steers toward scholarly sources — e.g., instead of `"effects of sleep deprivation"`, use `"peer-reviewed research and clinical studies on the effects of sleep deprivation"`.

Choose a descriptive filename based on the topic (e.g., `mrna-vaccine-platforms-2026`, `gut-microbiome-depression`). Use lowercase with hyphens, no spaces.

```bash
python scripts/google_research.py research "$ARGUMENTS" --no-wait
```

Important:
- **Always use `--no-wait`.** This returns in seconds with an `interaction_id`. Do **NOT** run blocking `research` without `--no-wait` — it blocks for 15–30+ minutes and will time out in the coding agent's Bash tool (~2 min limit).
- The script prints `interaction_id=ChBi...` to stderr. **Save this ID** — you need it for Step 2.
- Immediately tell the user:
  - Deep research has been kicked off
  - Expected latency: **15–30 minutes** (up to ~60 minutes for complex academic queries)
  - You will poll for the report in Step 2

Tell them they can continue other work while polling runs (you may background the poll step).

## Step 2: Poll for results

```bash
python scripts/google_research.py poll "$INTERACTION_ID" -o "$FILENAME.md" --timeout 1800
```

Important:
- Use `--timeout 1800` (30 minutes) per poll invocation.
- The poll command waits synchronously, checking status every ~10s until `completed` or timeout.
- Do **NOT** paste the full report stdout into chat — the `-o` file is the deliverable.

### If the poll times out

A poll timeout is **NOT a failure** — research continues server-side on Google.

1. Tell the user the research is still running server-side.
2. Wait **2–3 minutes**.
3. Re-run the **same** poll command with the same `interaction_id`:

```bash
python scripts/google_research.py poll "$INTERACTION_ID" -o "$FILENAME.md" --timeout 1800
```

Total job time may reach **30–60 minutes**. Re-run poll until the command succeeds and `$FILENAME.md` exists. Do **NOT** tell the user research failed without retrying poll at least once.

### If poll exits before Step 1 completed

If you only have stderr from Step 1 and have not polled yet, use the `interaction_id` from `[research] interaction_id=...` in Step 2.

## What the output looks like

The script writes a comprehensive markdown report to `$FILENAME.md`. The report contains:
- Full narrative with inline `[[N]](url)` citations
- A `## Sources` section (often 50–100+ entries for deep queries)

There is no separate `.json` metadata file or executive summary — the markdown is the complete deliverable.

**Expect mixed sources.** Google deep research often includes peer-reviewed journals *and* commercial supplement sites, health blogs, news outlets, or product pages — especially in practical/clinical sections. Do not assume every source is academic.

## Response format

**After Step 1:** Confirm research started; share expected latency and that you saved `interaction_id`.

**After Step 2 (report ready):**

1. **Brief summary** — relay the report's opening summary section (usually `## Summary` or the first paragraph). Do **not** paste the full report into chat.

2. **Source Quality** — required section. Read only the `## Sources` section (and the summary if needed for context). Do **not** read the entire report into context.

   Use this template:

   ```markdown
   ### Source Quality

   - **Total sources cited:** ~N
   - **Peer-reviewed / preprint / clinical-registry** (PubMed, PMC, Nature, MDPI, Frontiers, arXiv, ClinicalTrials.gov, university domains): ~X (~Y%)
   - **Institutional / government** (NIH, WHO, .gov, .edu pages that are not journal articles): ~X
   - **News / industry / commercial / blog** (supplement retailers, product pages, health blogs, Wikipedia, YouTube): ~X (~Y%)

   **Assessment:** [1–2 sentences — e.g. "Core mechanistic and clinical claims are grounded in peer-reviewed literature; non-academic sources appear mainly in commercial/product sections." OR "Academic coverage is thin — consider a follow-up targeted search."]

   **Evidence note:** [If &lt;50% academic/institutional, flag explicitly. Note which key claims rely on academic vs non-academic sources.]
   ```

   Classification rules:
   - URLs are often grounding redirects — judge from **source titles and domain names** in the `## Sources` list (e.g. `nih.gov`, `mdpi.com`, `justthrivehealth.com`).
   - Do not read all 100+ sources line-by-line if the list is huge — sample systematically (first 20, middle 20, last 20) or grep for domain patterns, then extrapolate with a clear caveat.
   - Do not invent counts — if you cannot estimate, say "approximately" and explain your sampling method.

3. **Report file path** — tell the user: `$FILENAME.md`

4. **Offer to read more** — ask if the user wants to review the full report. **Do NOT read the file into context unless the user asks** — reports are often 5,000–10,000+ words.

5. **`interaction_id`** — note from stderr for potential follow-up or poll recovery.
