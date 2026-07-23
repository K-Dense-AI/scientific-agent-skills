# Responsible AI in Research Ideation

AI can supply prompts, reframings, counterarguments, or organizational help.
It is not an expert panel, evidence source, author, ethics reviewer, or
scientific decision maker. Capabilities and policies change; follow current
institutional, funder, publisher, legal, and community requirements.

## Default sequence

1. **Classify information.** Decide whether the prompt would include personal,
   patient, confidential, unpublished, proprietary, export-controlled,
   security-sensitive, or otherwise restricted information.
2. **Generate human ideas first.** Freeze an independent human-only round
   before showing AI suggestions.
3. **Define the AI role.** Examples: produce orthogonal questions, challenge an
   assumption, list search terms, or reformat an already approved record.
4. **Use only an approved tool and data class.** Do not assume a paid or
   “private” interface satisfies institutional controls.
5. **Capture provenance.** Record tool/model or service, date, purpose, material
   prompt constraints, output IDs used, and human editor. Avoid storing
   restricted prompt text in the session register.
6. **Verify externally.** Check factual claims and every citation against
   authoritative sources. Search for contradictory and null evidence.
7. **Run a second independent human round.** Ask for ideas outside the AI's
   frames and for harms or stakeholders the output omitted.
8. **Disclose as required.** The accountable humans retain authorship,
   responsibility, and final judgment.

AI use is optional. The bundled CLIs make no network or LLM calls.

## Suitable bounded roles

- Generate alternative phrasings of a non-sensitive focal question.
- Suggest dimensions for a morphological matrix, followed by human review.
- Produce counterexamples or alternative mechanisms for registered ideas.
- Identify ambiguous terms or missing assumptions.
- Generate candidate search vocabulary, not references presented as real.
- Convert an approved, non-sensitive record between formats.
- Act as one disclosed adversarial prompt after human-first ideation.

Avoid using AI to:

- decide which scientific claim is true;
- certify novelty, safety, ethics, legality, or regulatory compliance;
- invent or complete missing data;
- rank people, patients, communities, or protected groups;
- replace stakeholder participation or domain expertise;
- generate actionable harmful or dual-use procedures;
- review confidential manuscripts, grants, or peer-review material in systems
  where confidentiality is not assured.

## Hallucination and source verification

Generative systems can produce plausible but false claims, references,
methods, statistics, and quotations. A 2023 study found fabricated and
substantively erroneous bibliographic citations in outputs from the tested
GPT-3.5 and GPT-4 versions; model-specific rates are not timeless estimates.

For every AI-suggested source:

1. locate the work in a trusted index or publisher site;
2. match title, authors, venue, year, DOI, and version;
3. read the relevant primary text;
4. confirm the cited result, population, design, and limitations;
5. record the stable source identifier;
6. delete unsupported claims rather than laundering them as “AI suggested.”

Never cite the model as evidence for a scientific claim.

## Anchoring and homogenization

AI output can anchor users on examples and compress a group's idea diversity.
In a preregistered short-story experiment, access to GPT-4 ideas improved
average evaluated creativity for some writers while making outputs more
similar in aggregate. The task was short creative writing, not scientific
ideation, so treat homogenization as a credible risk to test—not a universal
effect size.

Controls:

- human-only generation before any AI output;
- different participants receive no AI, or distinct prompt frames, when the
  comparison is methodologically justified;
- ask for mechanisms that contradict the AI's dominant frame;
- compare assumptions, predictions, and causal structure—not only wording;
- preserve pre-AI ideas and record which ideas changed after exposure;
- include non-AI domain, methods, stakeholder, ethics, and safety perspectives;
- do not infer independent support from many outputs of the same model.

Multiple AI samples are correlated products of a system, not independent
experts or replications.

## Automation bias and false authority

Fluent language, technical detail, and confident formatting are not evidence.
To reduce deference:

- hide model branding during idea review when feasible;
- evaluate ideas against the same predeclared criteria;
- require a human rationale and uncertainty statement;
- assign a non-originating human challenger;
- verify with primary evidence and domain experts;
- retain a “no decision / insufficient evidence” outcome;
- prohibit automatic advancement based only on an AI or matrix score.

Do not ask an AI system to assign a probability it cannot calibrate and then
treat the number as measured uncertainty.

## Confidentiality, privacy, and intellectual property

Do not submit the following to an external AI service unless an authorized
policy and agreement explicitly permit that data class:

- patient, participant, employee, student, or other personal information;
- unpublished manuscripts, peer reviews, grants, invention disclosures, or
  partner materials;
- proprietary protocols, source code, compounds, sequences, or business data;
- controlled unclassified, export-controlled, classified, or
  security-sensitive information;
- credentials, tokens, private links, or internal system details;
- community-governed or Indigenous data outside agreed governance.

Data minimization and abstraction are still required with an approved tool.
Check retention, training use, access, location, deletion, audit, and incident
terms. If the work cannot be safely abstracted, use an approved local/closed
process or do not use AI.

## Bias, representation, and participation

AI output may reproduce gaps and stereotypes in training data and overrepresent
well-indexed, English-language, high-resource perspectives. It cannot consent
on behalf of affected communities.

- Ask which populations, languages, geographies, disciplines, and negative
  findings are missing.
- Involve relevant people directly and compensate them where applicable.
- Distinguish biological variables from social identities and avoid
  essentialist mechanisms.
- Examine whether a proposed measurement or intervention transfers across
  settings.
- Treat accessibility, equity, and distribution of benefits and burdens as
  review criteria and possible gates.

## Research integrity and disclosure

Humans remain responsible for accuracy, attribution, originality, permissions,
and the research record. AI systems should not be listed as authors. Record and
disclose AI use at the level required by the institution, funder, venue, and
applicable guidance.

A useful internal disclosure includes:

```text
Tool/service and model or version (if exposed):
Date used:
Purpose:
Information classification and approved environment:
Human-first idea set frozen before use: yes/no
Outputs retained or used:
Verification performed:
Material changes made by humans:
Known limitations:
```

Disclosure does not cure inappropriate data sharing, plagiarism, fabricated
citations, or unverified content.

## Dual-use and misuse review

AI can make technical ideation faster and more accessible. Screen both the
research idea and the AI interaction for misuse potential.

Escalate before generating operational detail when an idea could materially
enable:

- pathogen enhancement, immune evasion, host-range change, or harmful delivery;
- synthesis, acquisition, concealment, scaling, or dissemination of hazardous
  agents or toxins;
- bypassing safety, monitoring, access, or security controls;
- dangerous chemical, biological, cyber, autonomous, or surveillance
  capability;
- targeting vulnerable populations or critical systems.

Use high-level risk framing while waiting for institutional biosafety,
biosecurity, research-security, legal, ethics, or funding-agency guidance.
Do not rely on a model's refusal behavior as a risk-management control.

WHO's responsible life-sciences framework treats risk mitigation as a shared,
multi-stakeholder responsibility. U.S. DURC/PEPP oversight has been under
revision following the May 2025 executive order; verify current policy rather
than copying a superseded threshold.

## Incident handling

If sensitive information or unsupported AI content entered the workflow:

1. stop further sharing and preserve only the minimum audit information;
2. notify the appropriate institutional privacy, security, integrity, or
   research office under local policy;
3. do not copy the sensitive content into additional systems;
4. remove or quarantine unverified claims from downstream artifacts;
5. document affected decisions and re-review them;
6. follow approved deletion and incident-response procedures.

Do not conceal the event by silently editing provenance.

## Evidence and policy basis

See `sources.md` for the dated primary evidence and official guidance used
here, including:

- Doshi and Hauser (2024) on individual creativity and collective similarity
  in a constrained writing task;
- Walters and Wilder (2023) on fabricated and erroneous citations from tested
  model versions;
- European Commission/ERA Forum living guidance (2024);
- UNESCO guidance (2023, page updated 2026);
- ICMJE recommendations on AI in publishing (2026);
- ALLEA's 2023 European Code of Conduct for Research Integrity;
- WHO and current U.S. official dual-use resources.
