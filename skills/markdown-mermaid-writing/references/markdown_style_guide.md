<!-- Source: https://github.com/SuperiorByteWorks-LLC/agent-project | License: Apache-2.0 | Author: Clayton Young / Superior Byte Works, LLC (Boreal Bytes) -->

# Markdown Style Guide

> **For AI agents:** Read this file for all core formatting rules. When creating any markdown document, follow these conventions for consistent, professional output. When a template exists for your document type, start from it — see [Templates](#templates).
>
> **For humans:** This guide ensures every markdown document in your project is clean, scannable, well-cited, and renders beautifully on GitHub. Reference it from your `AGENTS.md` or contributing guide.

**Target platform:** GitHub Markdown (Issues, PRs, Discussions, Wikis, `.md` files)
**Design goal:** Clear, professional documents that communicate effectively through consistent structure, meaningful formatting, proper citations, and strategic use of diagrams.

---

## Quick Start for Agents

1. **Identify the document type** → Check if a [template](#templates) exists
2. **Structure first** → Heading hierarchy, then content
3. **Apply formatting from this guide** → Headings, text, lists, tables, images, links
4. **Add citations** → Footnote references for all claims and sources
5. **Consider diagrams** → Would a [Mermaid diagram](mermaid_style_guide.md) communicate this better than text?
6. **Add collapsible sections** → For supplementary detail, speaker notes, or lengthy context
7. **Verify** → Run through the [quality checklist](#quality-checklist)

---

## Core Principles

| #   | Principle                         | Rule                                                                                                                                                                                       |
| --- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | **Answer before they ask**        | Anticipate reader questions and address them inline. A great document resolves doubts as they form — the reader finishes with no lingering "but what about...?"                            |
| 2   | **Scannable first**               | Readers skim before they read. Use headings, bold, and lists to make the structure visible at a glance.                                                                                    |
| 3   | **Cite everything**               | Every claim, statistic, or external reference gets a footnote citation with a full URL. No orphan claims.                                                                                  |
| 4   | **Diagrams over walls of text**   | If a concept involves flow, relationships, or structure, use a [Mermaid diagram](mermaid_style_guide.md) alongside the text.                                                               |
| 5   | **Generous with information**     | Don't hide the details — surface them. Use collapsible sections for depth without clutter, but never omit information because "they probably don't need it." If it's relevant, include it. |
| 6   | **Consistent structure**          | Same heading hierarchy, same formatting patterns, same emoji placement across every document.                                                                                              |
| 7   | **One idea per section**          | Each heading should cover one topic. If you're covering two ideas, split into two headings.                                                                                                |
| 8   | **Professional but approachable** | Clean formatting, no clutter, no decorative noise — but not stiff or academic. Write like a senior engineer explains to a colleague.                                                       |

---

## 🗂️ Everything is Code

Everything is code. PRs, issues, kanban boards — they're all markdown files in your repo, not data trapped in a platform's database.

### Why this matters

- **Portable** — GitHub → GitLab → Gitea → anywhere. Your project management data isn't locked into any vendor. Switch platforms and your issues, PR records, and boards come with you — they're just files.
- **AI-native** — Agents can read every issue, PR record, and kanban board with local file access. No API tokens, no rate limits, no platform-specific queries. `grep` beats `gh api` every time.
- **Auditable** — Project management changes go through the same PR review process as code changes. Every board update, every issue status change — it's all in git history with attribution and timestamps.

### How it works

| What                 | Where it lives                                            | What GitHub does                                                                                                                                                   |
| -------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Pull requests**    | `docs/project/pr/pr-NNNNNNNN-short-description.md`        | GitHub PR is a thin pointer — humans go there to comment on diffs, approve, and watch CI. The record of what changed, why, and what was learned lives in the file. |
| **Issues**           | `docs/project/issues/issue-NNNNNNNN-short-description.md` | GitHub Issues is a notification and comment layer. Bug reports, feature requests, investigation logs, and resolutions live in the file.                            |
| **Kanban boards**    | `docs/project/kanban/{scope}-{id}-short-description.md`   | No external board tool needed. Modify the board in your branch, merge it with your PR. The board evolves with the codebase.                                        |
| **Decision records** | `docs/decisions/NNN-{slug}.md`                            | Not tracked in GitHub at all — purely repo-native.                                                                                                                 |

### The rule

> 📌 **Don't capture information in GitHub's UI that should be captured in a file.** Approve PRs in GitHub. Watch CI in GitHub. Comment in GitHub. But the actual content — the description, the investigation, the decision — lives in a committed file. If it's worth writing down, it's worth committing.

### Templates for tracked documents

- [Pull request record](../templates/pull_request.md) — the PR description IS this file
- [Issue record](../templates/issue.md) — bug reports and feature requests as repo files
- [Kanban board](../templates/kanban.md) — sprint/project boards that merge with your code

See [File conventions](#file-conventions-for-tracked-documents) for directory structure and naming.

---

## Document Structure

### Title and metadata

Every document starts with exactly one H1 title, followed by a brief context line and a separator:

```markdown
# Document Title Here

_Brief context — project name, date, or purpose in one line_

---
```

- **One H1 per document** — never more
- Context line in italics — what this document is, when, and for whom
- Horizontal rule separates metadata from content

### Heading hierarchy

| Level | Syntax          | Use                     | Max per document    |
| ----- | --------------- | ----------------------- | ------------------- |
| H1    | `# Title`       | Document title          | **1** (exactly one) |
| H2    | `## Section`    | Major sections          | 4–10                |
| H3    | `### Topic`     | Topics within a section | 2–5 per H2          |
| H4    | `#### Subtopic` | Subtopics when needed   | 2–4 per H3          |
| H5+   | Never use       | —                       | 0                   |

**Rules:**

- **Never skip levels** — don't jump from H2 to H4
- **Emoji in H2 headings** — one emoji per H2, at the start: `## 📋 Project Overview`
- **No emoji in H3/H4** — keep sub-headings clean
- **Sentence case** — `## 📋 Project overview` not `## 📋 Project Overview` (exception: proper nouns)
- **Descriptive headings** — `### Authentication flow` not `### Details`

---

## Text Formatting

### Bold, italic, code

| Format     | Syntax       | When to use                                   | Example                             |
| ---------- | ------------ | --------------------------------------------- | ----------------------------------- |
| **Bold**   | `**text**`   | Key terms, important concepts, emphasis       | **Primary database** handles writes |
| _Italic_   | `*text*`     | Definitions, titles, subtle emphasis          | The process is called _sharding_    |
| `Code`     | `` `text` `` | Technical terms, commands, file names, values | Run `npm install` to install        |
| ~~Strike~~ | `~~text~~`   | Deprecated content, corrections               | ~~Old approach~~ replaced by v2     |

**Rules:**

- **Bold sparingly** — if everything is bold, nothing is. Max 2–3 bold terms per paragraph.
- **Don't combine** bold and italic (`***text***`) — pick one
- **Code for anything technical** — file names (`README.md`), commands (`git push`), config values (`true`), environment variables (`NODE_ENV`)
- **Never bold entire sentences** — bold the key word(s) within the sentence

### Blockquotes

Use blockquotes for definitions, callouts, and important notes:

```markdown
> **Definition:** A _load balancer_ distributes incoming network traffic
> across multiple servers to ensure no single server bears too much demand.
```

For warnings and callouts:

```markdown
> ⚠️ **Warning:** This operation is destructive and cannot be undone.

> 💡 **Tip:** Use `--dry-run` to preview changes before applying.

> 📌 **Note:** This requires admin permissions on the repository.
```

- Prefix with emoji + bold label for typed callouts
- Keep blockquotes to 1–3 lines
- Don't nest blockquotes (`>>`)

---

## Lists

### When to use each type

| List type | Syntax       | Use when                                  |
| --------- | ------------ | ----------------------------------------- |
| Bullet    | `- item`     | Items have no inherent order              |
| Numbered  | `1. step`    | Steps must happen in sequence             |
| Checkbox  | `- [ ] item` | Tracking completion (agendas, checklists) |

### Formatting rules

- **Consistent indentation** — 2 spaces for sub-items (some renderers use 4; pick one, stick with it)
- **Parallel structure** — every item in a list should have the same grammatical form
- **No period at end** unless items are full sentences
- **Keep items concise** — if a bullet needs a paragraph, it should be a sub-section instead
- **Max nesting depth: 2 levels** — if you need a third level, restructure

```markdown
✅ Good — parallel structure, concise:

- Configure the database connection
- Run the migration scripts
- Verify the schema changes

❌ Bad — mixed structure, verbose:

- You need to configure the database
- Migration scripts
- After that, you should verify that the schema looks correct
```

---

## Links and Citations

### Inline links

```markdown
See the [Mermaid Style Guide](mermaid_style_guide.md) for diagram conventions.
```

- **Meaningful link text** — `[Mermaid Style Guide]` not `[click here]` or `[link]`
- **Relative paths** for internal links — `[Guide](./README.md)` not absolute URLs
- **Full URLs** for external links — always `https://`

### Footnote citations

**Every claim, statistic, or reference to external work MUST have a footnote citation.** This is non-negotiable for credibility.

```markdown
Markdown was created by John Gruber in 2004 as a lightweight
markup language designed for readability[^1]. GitHub adopted
Mermaid diagram support in February 2022[^2].

[^1]: Gruber, J. (2004). "Markdown." _Daring Fireball_. https://daringfireball.net/projects/markdown/

[^2]: GitHub Blog. (2022). "Include diagrams in your Markdown files with Mermaid." https://github.blog/2022-02-14-include-diagrams-markdown-files-mermaid/
```

**Citation format:**

```
[^N]: Author/Org. (Year). "Title." *Publication*. https://full-url
```

**Rules:**

- **Number sequentially** — `[^1]`, `[^2]`, `[^3]` in order of appearance
- **Full URL always included** — the reader must be able to reach the source
- **Group all footnotes at the document bottom** — under a `## References` section or at the very end
- **Every external claim needs one** — statistics, quotes, methodologies, tools mentioned
- **Internal project links don't need footnotes** — use inline links instead

### Reference-style links (for repeated URLs)

When the same URL appears multiple times, use reference-style links to keep the text clean:

```markdown
The [official docs][mermaid-docs] cover all diagram types.
See [Mermaid documentation][mermaid-docs] for the full syntax.

[mermaid-docs]: https://mermaid.js.org/ 'Mermaid Documentation'
```

---

## Images and Figures

### Placement and syntax

```markdown
![Descriptive alt text for screen readers](images/architecture_overview.png)
_Figure 1: System architecture showing the three-tier deployment model_
```

**Rules:**

- **Inline with content** — place images where they're relevant, not in a separate "Images" section
- **Descriptive alt text** — `![Three-tier architecture diagram]` not `![image]` or `![screenshot]`
- **Italic caption below** — `*Figure N: What this image shows*`
- **Number figures sequentially** — Figure 1, Figure 2, etc. if multiple images
- **Relative paths** — `images/file.png` not absolute paths
- **Reasonable file sizes** — compress PNGs, use SVG where possible

### Image naming convention

```
{document-slug}_{description}.{ext}

Examples:
  auth_flow_overview.png
  deployment_architecture.svg
  api_response_example.png
```

### When NOT to use an image

If the content could be expressed as a **Mermaid diagram**, prefer that over a static image:

| Scenario                   | Use                                        |
| -------------------------- | ------------------------------------------ |
| Architecture diagram       | Mermaid `flowchart` or `architecture-beta` |
| Sequence/interaction       | Mermaid `sequenceDiagram`                  |
| Data model                 | Mermaid `erDiagram`                        |
| Timeline                   | Mermaid `timeline` or `gantt`              |
| Screenshot of UI           | Image (Mermaid can't do this)              |
| Photo / real-world image   | Image                                      |
| Complex data visualization | Image or Mermaid `xychart-beta`            |

See the [Mermaid Style Guide](mermaid_style_guide.md) for diagram type selection and styling.

---

## Tables

### When to use tables

- **Structured comparisons** — features, options, tradeoffs
- **Reference data** — configuration values, API parameters, status codes
- **Schedules and matrices** — timelines, responsibility assignments

### When NOT to use tables

- **Narrative content** — use paragraphs instead
- **Simple lists** — use bullet points
- **More than 5 columns** — becomes unreadable on mobile; restructure

### Formatting

```markdown
| Feature | Free Tier | Pro Tier | Enterprise |
| ------- | --------- | -------- | ---------- |
| Users   | 5         | 50       | Unlimited  |
| Storage | 1 GB      | 100 GB   | Custom     |
| Support | Community | Email    | Dedicated  |
```

**Rules:**

- **Header row always** — no headerless tables
- **Left-align text columns** — `|---|` (default)
- **Right-align number columns** — `|---:|` when appropriate
- **Concise cell content** — 1–5 words per cell. If you need more, it's not a table problem
- **Bold key column** — the first column or the column the reader scans first
- **Consistent formatting within columns** — don't mix sentences and fragments

---

## Code Blocks

### Inline code

Use backticks for technical terms within prose:

```markdown
Run `git status` to check for uncommitted changes.
The `NODE_ENV` variable controls the runtime environment.
```

### Fenced code blocks

Always specify the language for syntax highlighting:

````markdown
```python
def calculate_average(values: list[float]) -> float:
    """Return the arithmetic mean of a list of values."""
    return sum(values) / len(values)
```
````

**Rules:**

- **Always include language identifier** — ` ```python `, ` ```bash `, ` ```json `, etc.
- **Use ` ```text ` for plain output** — not ` ``` ` with no language
- **Keep blocks focused** — show the relevant snippet, not the entire file
- **Add a comment if context needed** — `# Configure the database connection` at the top of the block

---

## Collapsible Sections

Use HTML `<details>` for supplementary content that shouldn't clutter the main flow — speaker notes, implementation details, verbose logs, or optional deep-dives.

```markdown
<details>
<summary><strong>💬 Speaker Notes</strong></summary>

- Key talking point one
- Transition to next topic
- **Bold** emphasis works inside details
- [Links](https://example.com) work too

</details>

---
```

**Rules:**

- **Collapsed by default** — the `<details>` tag collapses automatically
- **Descriptive summary** — `<strong>💬 Speaker Notes</strong>` or `<strong>📋 Implementation Details</strong>`
- **Blank line after `<summary>` tag** — required for markdown to render inside the block
- **ALWAYS follow with `---`** — horizontal rule after every `</details>` for visual separation
- **Any markdown works inside** — bullets, bold, links, code blocks, tables

### Common collapsible patterns

| Summary label         | Use for                                          |
| --------------------- | ------------------------------------------------ |
| 💬 **Speaker Notes**  | Presentation talking points, timing, transitions |
| 📋 **Details**        | Extended explanation, verbose context            |
| 🔧 **Implementation** | Technical details, code samples, config          |
| 📊 **Raw Data**       | Full output, logs, data tables                   |
| 💡 **Background**     | Context that helps but isn't essential           |

---

## Horizontal Rules

Use `---` (three hyphens) for visual separation:

```markdown
---
```

**When to use:**

- **After every `</details>` block** — mandatory, creates clear separation
- **After title/metadata** — separates document header from content
- **Between major sections** — when an H2 heading alone doesn't create enough visual break
- **Before footnotes/references** — separates content from citation list

**When NOT to use:**

- Between every paragraph (too busy)
- Between H3 sub-sections within the same H2 (use whitespace instead)

---

## Approved Emoji Set

One emoji per H2 heading, at the start. Use sparingly in body text for callouts and emphasis only.

### Section headings

| Emoji | Use for                                |
| ----- | -------------------------------------- |
| 📋    | Overview, summary, agenda, checklist   |
| 🎯    | Goals, objectives, outcomes, targets   |
| 📚    | Content, documentation, main body      |
| 🔗    | Resources, references, links           |
| 📍    | Agenda, navigation, current position   |
| 🏠    | Housekeeping, logistics, announcements |
| ✍️    | Tasks, assignments, action items       |

### Status and outcomes

| Emoji | Meaning                              |
| ----- | ------------------------------------ |
| ✅    | Success, complete, correct, approved |
| ❌    | Failure, incorrect, avoid, rejected  |
| ⚠️    | Warning, caution, important notice   |
| 💡    | Tip, insight, idea, best practice    |
| 📌    | Important, key point, remember       |
| 🚫    | Prohibited, do not, blocked          |

### Technical and process

| Emoji | Meaning                           |
| ----- | --------------------------------- |
| ⚙️    | Configuration, settings, process  |
| 🔧    | Tools, utilities, setup           |
| 🔍    | Analysis, investigation, review   |
| 📊    | Data, metrics, analytics          |
| 📈    | Growth, trends, improvement       |
| 🔄    | Cycle, refresh, iteration         |
| ⚡    | Performance, speed, quick action  |
| 🔐    | Security, authentication, privacy |
| 🌐    | Web, API, network, global         |
| 💾    | Storage, database, persistence    |
| 📦    | Package, artifact, deployment     |

### People and collaboration

| Emoji | Meaning                             |
| ----- | ----------------------------------- |
| 👤    | User, person, individual            |
| 👥    | Team, group, collaboration          |
| 💬    | Discussion, comments, speaker notes |
| 🎓    | Learning, education, knowledge      |
| 🤔    | Question, consideration, reflection |

### Emoji rules

1. **One per H2 heading** at the start — `## 📋 Overview`
2. **None in H3/H4** — keep sub-headings clean
3. **Sparingly in body text** — for callouts (`> ⚠️ **Warning:**`) and key markers only
4. **Never in**: titles (H1), code blocks, link text, table data cells
5. **No decorative emoji** — 🎉 💯 🔥 🎊 💥 ✨ add noise, not meaning
6. **Consistency** — same emoji = same meaning across all documents in the project

---

## Mermaid Diagram Integration

**Whenever content describes flow, structure, relationships, or processes, consider whether a Mermaid diagram would communicate it better than prose alone.** Diagrams and text together are more effective than either alone.

### When to add a diagram

**Any time your text describes flow, structure, relationships, timing, or comparisons, there's a Mermaid diagram that communicates it better.** Scan the table below to identify the right type, then follow this workflow:

1. **Read the [Mermaid Style Guide](mermaid_style_guide.md) first** — emoji, color palette, accessibility, complexity management
2. **Then open the specific type file** — exemplar, tips, template, complex example

| Your content describes...                            | Add a...                 | Type file                                           |
| ---------------------------------------------------- | ------------------------ | --------------------------------------------------- |
| Steps in a process, workflow, decision logic         | **Flowchart**            | [flowchart.md](diagrams/flowchart.md)       |
| Who talks to whom and when (API calls, messages)     | **Sequence diagram**     | [sequence.md](diagrams/sequence.md)         |
| Class hierarchy, type relationships, interfaces      | **Class diagram**        | [class.md](diagrams/class.md)               |
| Status transitions, entity lifecycle, state machine  | **State diagram**        | [state.md](diagrams/state.md)               |
| Database schema, data model, entity relationships    | **ER diagram**           | [er.md](diagrams/er.md)                     |
| Project timeline, roadmap, task dependencies         | **Gantt chart**          | [gantt.md](diagrams/gantt.md)               |
| Parts of a whole, proportions, distribution          | **Pie chart**            | [pie.md](diagrams/pie.md)                   |
| Git branching strategy, merge/release flow           | **Git Graph**            | [git_graph.md](diagrams/git_graph.md)       |
| Concept hierarchy, brainstorm, topic map             | **Mindmap**              | [mindmap.md](diagrams/mindmap.md)           |
| Chronological events, milestones, history            | **Timeline**             | [timeline.md](diagrams/timeline.md)         |
| User experience, satisfaction scores, journey        | **User Journey**         | [user_journey.md](diagrams/user_journey.md) |
| Two-axis comparison, prioritization matrix           | **Quadrant chart**       | [quadrant.md](diagrams/quadrant.md)         |
| Requirements traceability, compliance mapping        | **Requirement diagram**  | [requirement.md](diagrams/requirement.md)   |
| System architecture at varying zoom levels           | **C4 diagram**           | [c4.md](diagrams/c4.md)                     |
| Flow magnitude, resource distribution, budgets       | **Sankey diagram**       | [sankey.md](diagrams/sankey.md)             |
| Numeric trends, bar charts, line charts              | **XY Chart**             | [xy_chart.md](diagrams/xy_chart.md)         |
| Component layout, spatial arrangement, layers        | **Block diagram**        | [block.md](diagrams/block.md)               |
| Work item tracking, status board, task columns       | **Kanban board**         | [kanban.md](diagrams/kanban.md)             |
| Binary protocol layout, data packet format           | **Packet diagram**       | [packet.md](diagrams/packet.md)             |
| Cloud infrastructure, service topology, networking   | **Architecture diagram** | [architecture.md](diagrams/architecture.md) |
| Multi-dimensional comparison, skills, radar analysis | **Radar chart**          | [radar.md](diagrams/radar.md)               |
| Hierarchical proportions, budget breakdown           | **Treemap**              | [treemap.md](diagrams/treemap.md)           |

> 💡 **Pick the right type, not the easy type.** Don't default to flowcharts for everything — a timeline is better than a flowchart for chronological events, a sequence diagram is better for service interactions, an ER diagram is better for data models. Scan the table above and match your content to the most specific type. **If you catch yourself writing a paragraph that describes a visual concept, stop and diagram it.**

### How to integrate

Place the diagram **inline with the related text**, not in a separate section:

````markdown
### Authentication Flow

The login process validates credentials, checks MFA status,
and issues session tokens. Failed attempts are logged for
security monitoring.

‎```mermaid
sequenceDiagram
accTitle: Login Authentication Flow
accDescr: User login sequence through API and auth service

    participant U as 👤 User
    participant A as 🌐 API
    participant S as 🔐 Auth Service

    U->>A: POST /login
    A->>S: Validate credentials
    S-->>A: ✅ Token issued
    A-->>U: 200 OK + session

‎```

The token expires after 24 hours. See [Authentication flow](#authentication-flow)
for refresh token details.
````

**Always follow the [Mermaid Style Guide](mermaid_style_guide.md)** for diagram styling — emoji, color classes, accessibility (`accTitle`/`accDescr`), and type-specific conventions.

---

## Whitespace and Spacing

- **Blank line between paragraphs** — always
- **Blank line before and after headings** — always
- **Blank line before and after code blocks** — always
- **Blank line before and after blockquotes** — always
- **No blank line between list items** — keep lists tight
- **No trailing whitespace** — clean line endings
- **One blank line at end of file** — standard convention
- **No more than one consecutive blank line** — two blank lines = too much space

---

## Quality Checklist

### Structure

- [ ] Exactly one H1 title
- [ ] Heading hierarchy is correct (H1 → H2 → H3 → H4, no skips)
- [ ] Each H2 has exactly one emoji at the start
- [ ] H3 and H4 have no emoji
- [ ] Horizontal rules after title metadata and after every `</details>` block

### Content

- [ ] Every external claim has a footnote citation
- [ ] All footnotes have full URLs
- [ ] All links tested and working
- [ ] Meaningful link text (no "click here")
- [ ] Bold used for key terms, not entire sentences
- [ ] Code formatting for all technical terms

### Visual elements

- [ ] Images have descriptive alt text
- [ ] Images have italic figure captions
- [ ] Images placed inline with related content (not in separate section)
- [ ] Tables have header rows and consistent formatting
- [ ] Mermaid diagrams considered where applicable (with `accTitle`/`accDescr`)

### Collapsible sections

- [ ] `<details>` blocks have descriptive `<summary>` labels
- [ ] Blank line after `<summary>` tag (for markdown rendering)
- [ ] Horizontal rule `---` after every `</details>` block
- [ ] Content inside collapses renders correctly

### Polish

- [ ] No spelling or grammar errors
- [ ] Consistent whitespace (no trailing spaces, no double blanks)
- [ ] Parallel grammatical structure in lists
- [ ] Renders correctly in GitHub light and dark mode

---

## Templates

Templates provide pre-built structures for common document types. Copy the template, fill in your content, and follow this style guide for formatting. Every template enforces the principles above — citations, diagrams, collapsible depth, and self-answering structure.

| Document type                   | Template                                                                | Best for                                                                                              |
| ------------------------------- | ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Presentation / briefing         | [presentation.md](../templates/presentation.md)                   | Slide-deck-style documents with speaker notes, structured sections, and visual flow                   |
| Research paper / analysis       | [research_paper.md](../templates/research_paper.md)               | Data-driven analysis, literature reviews, methodology + findings with heavy citations                 |
| Project documentation           | [project_documentation.md](../templates/project_documentation.md) | Software/product docs — architecture, getting started, API reference, contribution guide              |
| Decision record (ADR/RFC)       | [decision_record.md](../templates/decision_record.md)             | Recording why a decision was made — context, options evaluated, outcome, consequences                 |
| How-to / tutorial guide         | [how_to_guide.md](../templates/how_to_guide.md)                   | Step-by-step instructions with prerequisites, verification steps, and troubleshooting                 |
| Status report / executive brief | [status_report.md](../templates/status_report.md)                 | Progress updates, risk summaries, decisions needed — for leadership and stakeholders                  |
| Pull request record             | [pull_request.md](../templates/pull_request.md)                   | PR documentation with change inventory, testing evidence, rollback plan, and review notes             |
| Issue record                    | [issue.md](../templates/issue.md)                                 | Bug reports (reproduction steps, root cause) and feature requests (acceptance criteria, user stories) |
| Kanban board                    | [kanban.md](../templates/kanban.md)                               | Sprint/release/project work tracking with visual board, WIP limits, metrics, and blocked items        |

### File conventions for tracked documents

Some templates produce documents that accumulate over time. Use these directory conventions:

| Document type    | Directory              | Naming pattern                              | Example                                                                 |
| ---------------- | ---------------------- | ------------------------------------------- | ----------------------------------------------------------------------- |
| Pull requests    | `docs/project/pr/`     | `pr-NNNNNNNN-short-description.md`          | `docs/project/pr/pr-00000123-fix-auth-timeout.md`                       |
| Issues           | `docs/project/issues/` | `issue-NNNNNNNN-short-description.md`       | `docs/project/issues/issue-00000456-add-export-filter.md`               |
| Kanban boards    | `docs/project/kanban/` | `{scope}-{identifier}-short-description.md` | `docs/project/kanban/sprint-2026-w07-agentic-template-modernization.md` |
| Decision records | `docs/decisions/`      | `NNN-{slug}.md`                             | `docs/decisions/001-use-postgresql.md`                                  |
| Status reports   | `docs/status/`         | `status-{date}.md`                          | `docs/status/status-2026-02-14.md`                                      |

### Choosing a template

- **Presenting to people?** → Presentation
- **Publishing analysis or research?** → Research paper
- **Documenting a codebase or product?** → Project documentation
- **Recording why you chose X over Y?** → Decision record
- **Teaching someone how to do something?** → How-to guide
- **Updating leadership on progress?** → Status report
- **Documenting a PR for posterity?** → Pull request record
- **Tracking a bug or requesting a feature?** → Issue record
- **Managing work items for a sprint or project?** → Kanban board
- **None of these fit?** → Start from this style guide's rules directly — no template required

---

## Common Mistakes

### ❌ Multiple emoji per heading

```markdown
## 📚📊📈 Content Topics ← Too many
```

✅ Fix: One emoji per H2

```markdown
## 📚 Content topics
```

### ❌ Missing citations

```markdown
Studies show 73% of developers prefer Markdown. ← Where's the source?
```

✅ Fix: Add footnote

```markdown
Studies show 73% of developers prefer Markdown[^1].

[^1]: Stack Overflow. (2024). "Developer Survey Results." https://survey.stackoverflow.co/2024
```

### ❌ Wall of text without structure

```markdown
The system handles authentication by first checking the JWT token
validity, then verifying the user exists in the database, then
checking their permissions against the requested resource...
```

✅ Fix: Use a list, heading, or diagram

```markdown
### Authentication flow

1. Validate JWT token signature and expiration
2. Verify user exists in the database
3. Check user permissions against the requested resource
```

### ❌ Images in a separate section

```markdown
## Content

[paragraphs of text]

## Screenshots

[all images grouped here] ← Disconnected from context
```

✅ Fix: Place images inline where relevant

### ❌ No horizontal rule after collapsible sections

```markdown
</details>
### Next Topic  ← Runs together visually
```

✅ Fix: Always add `---` after `</details>`

```markdown
</details>

---

### Next topic ← Clear separation
```

---

## Resources

- [GitHub Flavored Markdown Spec](https://github.github.com/gfm/) · [Mermaid Style Guide](mermaid_style_guide.md) · [GitHub Basic Formatting](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax)
