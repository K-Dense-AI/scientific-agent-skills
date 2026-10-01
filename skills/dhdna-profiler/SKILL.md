---
name: dhdna-profiler
description: Applies the DHDNA framework as an exploratory rubric for reasoning and writing patterns in supplied text. Used for explicit requests for DHDNA, cognitive-style reflection, a thinking-pattern profile, or comparisons of textual reasoning. Scores describe evidence in the sample, not validated psychological traits or personal identity.
allowed-tools: Read Write
license: MIT license
metadata:
  version: "2.0"
  last-reviewed: "2026-09-30"
  skill-author: AHK Strategies (ashrafkahoush-ux)
---

# DHDNA Profiler — Text Pattern Annotation

An exploratory rubric for describing a supplied text using Digital Human DNA (DHDNA) terminology. Its cognitive-fingerprint language is a framework metaphor; it does not establish a unique, stable, or identifiable psychological signature.

Use this workflow for requested reflection on writing. It requires no package, credentials, API call, or MindBook account. It does not reproduce MindBook's scoring engine.

## Sources and scope

The [current publisher page](https://www.ahkstrategies.net/dhdna) names twelve public dimensions as a design vocabulary. The table below maps those names to the existing skill's annotation labels. The observation criteria and score anchors are local conventions, not an upstream validated scoring instrument.

The [DHDNA preprint](https://doi.org/10.5281/zenodo.18736629), *DHDNA: A Framework for Ethical Digital Identity as Inheritable Heritage* (February 23, 2026), states in section 6.3 that validation was limited to internal testing. The [IDNA v2 preprint](https://doi.org/10.5281/zenodo.18807387), *Toward a Unified Theory of Digital Consciousness* (February 27, 2026), proposes the tension pairs in section 4.3/Table 3 and the temporal-attractor model in section 2. Neither source establishes psychometric validity for this skill's annotations. A DOI, product demonstration, or journal submission is not evidence of such validity.

Describe observable reasoning and rhetorical choices. Genre, task, language proficiency, editing, collaboration, and AI assistance can change those choices. Do not infer intelligence, diagnosis, honesty, latent emotions, or a person's stable cognitive architecture from them.

## The 12 annotation dimensions

| # | Skill label | Current publisher label | Evidence to describe in the sample |
| --- | --- | --- | --- |
| 1 | Analytical Depth | Reasoning style | Explicit premises, alternatives, causal arguments, and checks of conclusions |
| 2 | Creative Range | Creative synthesis | Connections, analogies, alternative framings; novelty needs a stated comparison context |
| 3 | Emotional Processing | Emotional architecture | Expressed affect and consideration of others' feelings; not inferred internal emotion |
| 4 | Linguistic Precision | Linguistic signature | Defined terms, clear references, and controlled ambiguity; simple prose can be precise |
| 5 | Ethical Reasoning | Ethical reasoning | Explicit values, affected parties, tradeoffs, and consequences; not moral character |
| 6 | Strategic Thinking | Strategic cognition | Stated goals, constraints, contingencies, and action sequences |
| 7 | Memory Integration | Memory topology | Use of past events or precedents; not memory capacity or historical truth |
| 8 | Social Intelligence | Social intelligence | Audience adaptation and represented perspectives; not actual interpersonal ability |
| 9 | Domain Expertise | Domain expertise | Relevant technical explanations and qualified claims; jargon alone is insufficient, accuracy needs independent checking |
| 10 | Intuitive Reasoning | Intuitive processing | Explicit reliance on impressions or heuristics; missing reasoning alone is not intuition |
| 11 | Temporal Orientation | Temporal awareness | Stated time horizons and links between past, present, and future |
| 12 | Metacognition | Metacognition | Explicit uncertainty, assumptions, limitations, and revision of reasoning |

### The 6 proposed tension pairs

The IDNA preprint proposes these pairings. They are prompts for comparison, not established negative correlations or complementary scales. Rate both independently; both may be high, low, or N/A. Do not derive one score by subtracting the other from ten.

| Pair | Compare the sample's evidence for |
| --- | --- |
| 1 and 10 | Analytical Depth and Intuitive Reasoning |
| 3 and 6 | Emotional Processing and Strategic Thinking |
| 2 and 5 | Creative Range and Ethical Reasoning |
| 4 and 12 | Linguistic Precision and Metacognition |
| 7 and 11 | Memory Integration and Temporal Orientation |
| 8 and 9 | Social Intelligence and Domain Expertise |

## Workflow

### 1. Establish the sample

Use only the text designated for this request. Record a sample label, paragraph or line references, genre, purpose, language, and known editing context. Mark missing context unknown. Distinguish the author's assertions from quoted speech, fictional characters, and copied material; do not attribute all voices to the author.

If the user explicitly requests analysis of specified conversation turns, state that source scope and proceed. If the request leaves the source ambiguous, ask which text to use before expanding to earlier conversations or unrelated files.

### 2. Collect evidence

For each dimension, identify specific quotations and how they support the observation. Include contrary evidence where present. Distinguish lack of expression from lack of opportunity to express it. Do not manufacture quotations or use a fictional narrator as evidence about the writer's personality.

### 3. Annotate all twelve dimensions

Use qualitative observations by default. If numeric scoring is requested, use whole numbers on the local 1–10 rubric with these declared anchors:

- **1–3:** Relevant but limited or weakly developed expression in this sample.
- **4–7:** Explicit, developed expression with some supporting context.
- **8–10:** Sustained, elaborated expression across several relevant passages.
- **N/A:** No suitable evidence or no opportunity to assess; never impute zero or a midpoint.

Explain each numeric choice against the dimension's evidence criterion. These are ordinal judgments, not equal-interval measurements, percentiles, calibrated probabilities, or rankings of ability. Short samples may warrant only a few observations and many N/A entries. Do not force all scores or a dominant pattern.

Attach annotation confidence to each observation: HIGH for multiple unambiguous passages, MEDIUM for a clear but limited example, LOW for ambiguous evidence. Confidence concerns the textual interpretation, not a stable trait. If uncertainty prevents a defensible observation, use N/A instead of speculative scoring.

### 4. Synthesize the text pattern

Identify two or three most evidenced dimensions only when the sample supports them. Discuss the six proposed pairings only where both sides have evidence. A numeric gap, if requested, is a difference between local annotations; it does not identify inner conflict or predict behavior.

Describe the **argument structure** with examples: a sequence of premises, revisiting an idea, connecting topics, or contrasting alternatives. Labels such as linear, spiral, web, dialectic, or fractal are optional metaphors; they are neither exhaustive categories nor a model of the author's mind.

Describe **stated decision steps** only when choices are actually discussed. The order of sentences cannot establish whether a person privately felt, reasoned, or decided first.

### 5. Review and return

Verify every quotation against the sample, every observation against the cited passage, and every N/A against the available context. Check that the synthesis stays about the text. Return a profile in the conversation; export it only when requested.

Use this output template, including all twelve dimensions:

```text
DHDNA TEXT PATTERN PROFILE
Sample: [label and source scope]
Context: [genre, purpose, language, editing context or unknown]
Method: [qualitative, or local ordinal 1–10 rubric]

Dimension | Observation | Score or N/A if requested | Confidence | Quote/location
[one row per dimension; missing evidence remains N/A]

Most evidenced patterns: [supported patterns, or insufficient evidence]
Proposed pair comparisons: [both sides supported, or not assessed]
Argument structure: [description with passage references]
Stated decision steps: [description, or not expressed]
Context and limitations: [alternative explanations and missing evidence]
```

## Worked example

Synthetic sample, one paragraph:

> We could repeat the measurement or replace the sensor. I favor repeating it because the control failed. If the control fails again, we will inspect the wiring. This explanation is tentative: temperature was not recorded.

A manual application supports Analytical Depth (alternatives and a reason), Strategic Thinking (a conditional next step), and Metacognition (a stated limitation). Emotional Processing and Memory Integration are N/A: this sample offers no suitable evidence for them. Intuitive Reasoning is N/A, not a low score inferred from the presence of analysis. Linguistic Precision can be discussed from the explicit referents and conditional wording. Domain accuracy remains unchecked; the paragraph does not establish the writer's expertise. There is insufficient material to characterize a stable thinking style or predict a choice.

This is an illustrative annotation, not a validated reference profile or a benchmark of rater agreement.

## Comparing samples

First compare genre, prompt, length, language, editing context, and opportunities to express each dimension. When these differ, describe the resulting sample differences without attributing them to authors. Compare evidence dimension by dimension; preserve N/A and avoid composite totals, average-person rankings, predicted compatibility, or imagined interpersonal conversations presented as findings.

For self-reflection, state which designated turns or samples were used. Conversational writing for an AI may differ from other writing. For repeated samples, keep the annotation protocol and context comparable and distinguish observed changes from changes in elicitation or rater judgment. See [advanced profiling](references/advanced-profiling.md) for genre lenses, longitudinal limits, and compact notation.

## Boundaries

- Analyze the supplied text, including third-party text, as text. State that observations do not establish attributes of its author.
- Do not use this rubric for hiring, promotion, admission, clinical, disciplinary, or credit decisions. Offer direct, task-relevant review of the writing or evidence instead.
- Do not retrieve extra personal material, upload samples to MindBook or other services, or save profiles without the user's instruction. This skill makes no offline-processing or retention guarantee about its host application.
- Do not describe changing sample annotations as cognitive growth, decline, identity, or a diagnosis. Neither a high score nor a low score is a measure of intelligence or human worth.

## Attribution

Original skill author: [AHK Strategies](https://www.ahkstrategies.net/). Related product: [MindBook](https://themindbook.app/). These public links are references, not service integrations. The skill's MIT license does not relicense the linked research or product.
