<!-- Source: https://github.com/SuperiorByteWorks-LLC/agent-project | License: Apache-2.0 | Author: Clayton Young / Superior Byte Works, LLC (Boreal Bytes) -->

# Status Report / Executive Briefing Template

> **Back to [Markdown Style Guide](../references/markdown_style_guide.md)** — Read the style guide first for formatting, citation, and emoji rules.

**Use this template for:** Weekly/monthly status updates, executive briefings, project health reports, quarterly reviews, sprint retrospectives, or any document that updates stakeholders on progress, risks, and decisions needed. Designed to be read in under 5 minutes by someone with decision-making authority.

**Key features:** TL;DR at the top for executives who won't read further, traffic-light health indicators, explicit "decisions needed" section that surfaces blockers, metrics table with trends, and risk register with mitigations.

**Philosophy:** The #1 failure mode of status reports is burying the important stuff in a wall of accomplishments. Lead with what needs attention. If the reader only has 30 seconds, the TL;DR and health summary give them what they need. If they have 5 minutes, the full report answers every follow-up question they'd ask. Never make leadership dig for the thing they need to act on.

---

## How to Use

1. Copy this file for each reporting period
2. Name it by date: `status-2026-02-14.md` or `status-week-07.md`
3. **Fill in the TL;DR first** — if you can't summarize it, you don't understand it yet
4. Be honest about health status — green means green, not "green because I'm optimistic"
5. Add [Mermaid diagrams](../references/mermaid_style_guide.md) for progress timelines, architecture changes, or risk impact flows

---

## The Template

Everything below the line is the template. Copy from here; commands, API routes,
versions, thresholds, and numerical values are illustrative placeholders. Verify them
against the actual project before publishing. Follow its existing tracker and PR conventions.

---

# [Project/Team Name] — Status Report

_[Reporting period: Week of Month DD, YYYY / Month YYYY / Q# YYYY]_
_[Author] · [Date]_

---

## 📋 TL;DR

[3–5 bullet points. One sentence each. The most important things leadership needs to know. If they read nothing else, this is it.]

- **Overall:** [One-sentence project health summary]
- **Progress:** [Key milestone hit or approaching]
- **Blocker:** [The biggest risk or decision needed, or "None" if clear]
- **Next:** [What happens in the next period]

---

## 🚦 Health Summary

| Area         | Status       | Trend | Notes                     |
| ------------ | ------------ | ----- | ------------------------- |
| **Schedule** | 🟢 On track  | →     | [Brief context]           |
| **Scope**    | 🟡 At risk   | ↓     | [What's causing concern]  |
| **Budget**   | 🟢 On track  | →     | [Brief context]           |
| **Quality**  | 🟢 Good      | ↑     | [What's improving]        |
| **Team**     | 🟡 Stretched | →     | [Staffing or morale note] |

**Status key:** 🟢 On track · 🟡 At risk · 🔴 Off track / blocked
**Trend key:** ↑ Improving · → Stable · ↓ Declining

---

## ⚠️ Decisions Needed

> **This section is for items that require action from leadership or stakeholders.** If nothing needs a decision, write "No decisions needed this period."

### Decision 1: [Specific question that needs an answer]

**Context:** [Why this decision is needed now — 2–3 sentences]

**Options:**

| Option     | Impact         | Recommendation                  |
| ---------- | -------------- | ------------------------------- |
| [Option A] | [What happens] | [Recommended / Not recommended] |
| [Option B] | [What happens] | [Recommended / Not recommended] |

**Deadline:** [When this decision is needed by and what happens if it's delayed]

### Decision 2: [Another question]

[Same structure as above]

---

## 📊 Key Metrics

| Metric                             | Previous | Current | Target   | Trend   |
| ---------------------------------- | -------- | ------- | -------- | ------- |
| [Metric 1 — e.g., Sprint velocity] | [Value]  | [Value] | [Target] | [↑/→/↓] |
| [Metric 2 — e.g., Open bugs]       | [Value]  | [Value] | [Target] | [↑/→/↓] |
| [Metric 3 — e.g., Test coverage]   | [Value]  | [Value] | [Target] | [↑/→/↓] |
| [Metric 4 — e.g., Uptime SLA]      | [Value]  | [Value] | [Target] | [↑/→/↓] |

<details>
<summary><strong>📊 Detailed Metrics</strong></summary>

[Extended metrics, charts, or breakdowns that support the summary table but would overwhelm the main report.]

</details>

---

## ✅ Accomplishments

### Completed this period

- **[Accomplishment 1]** — [Impact or outcome. Why it matters.]
- **[Accomplishment 2]** — [Impact]
- **[Accomplishment 3]** — [Impact]

### Milestones

| Milestone     | Planned date | Actual date | Status         |
| ------------- | ------------ | ----------- | -------------- |
| [Milestone 1] | [Date]       | [Date or —] | ✅ Complete    |
| [Milestone 2] | [Date]       | [Date or —] | 🔄 In progress |
| [Milestone 3] | [Date]       | —           | 📋 Upcoming    |

---

## 🔄 In Progress

| Work item | Owner    | Started | Expected completion | Status                         |
| --------- | -------- | ------- | ------------------- | ------------------------------ |
| [Item 1]  | [Person] | [Date]  | [Date]              | [On track / At risk / Blocked] |
| [Item 2]  | [Person] | [Date]  | [Date]              | [Status]                       |
| [Item 3]  | [Person] | [Date]  | [Date]              | [Status]                       |

---

## 🚨 Risks and Issues

### Active risks

| Risk     | Likelihood | Impact  | Mitigation                  | Owner    |
| -------- | ---------- | ------- | --------------------------- | -------- |
| [Risk 1] | 🟡 Medium  | 🔴 High | [What we're doing about it] | [Person] |
| [Risk 2] | [Level]    | [Level] | [Mitigation]                | [Person] |

### Active blockers

| Blocker                 | Impact           | Needed from       | Status                           |
| ----------------------- | ---------------- | ----------------- | -------------------------------- |
| [Blocker 1 — or "None"] | [What's delayed] | [Who can unblock] | [Escalated / Waiting / Resolved] |

<details>
<summary><strong>📋 Resolved Issues</strong></summary>

| Issue     | Resolution            | Date resolved |
| --------- | --------------------- | ------------- |
| [Issue 1] | [How it was resolved] | [Date]        |
| [Issue 2] | [Resolution]          | [Date]        |

</details>

---

## 📍 Plan for Next Period

### Priorities

1. **[Priority 1]** — [What will be done and expected outcome]
2. **[Priority 2]** — [What will be done]
3. **[Priority 3]** — [What will be done]

### Key dates

| Date   | Event              |
| ------ | ------------------ |
| [Date] | [What's happening] |
| [Date] | [What's happening] |

---

## 🔗 References

- [Project board / Jira / Linear](https://example.com) — Live work tracking
- Previous status report (replace with the project link) — For context on trends
- Relevant decision record (replace with the project link) — Background on recent changes

---

_Next report due: [Date]_
