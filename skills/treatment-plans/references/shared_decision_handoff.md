# Shared Decisions, Informed Preferences, and Handoffs

Last reviewed: **2026-10-01**

## Documentation-only role

AHRQ describes shared decision-making as a clinician-led process that explores options, benefits, harms, risks, and what matters to the person. NICE similarly describes healthcare professionals and people working together on treatment and care decisions and communicating risks, benefits, and consequences.

NICE NG197 addresses adults and excludes unexpected emergencies requiring immediate life-saving care and decisions when an adult lacks capacity at the relevant time; separate local processes apply.

This skill records that process after it occurred. It does not conduct the conversation, generate options, quantify risks, assess capacity, obtain consent, or decide the outcome.

## Shared-decision record

For each decision, the authorized clinician supplies:

- the decision topic;
- options actually presented;
- source facts for each option;
- whether benefits, harms, and uncertainty were discussed;
- the preference as documented;
- the agreed or clinician-recorded outcome;
- participant roles;
- author role and time;
- acknowledgment status.

Use the person's words only when necessary and permitted. Prefer a bounded structured summary over copied narrative.

Do not:

- add an option the clinician did not document;
- characterize an option as preferred, safer, better, first-line, standard, or equivalent;
- calculate or restate probabilities;
- infer preference from adherence, demographics, prior care, or silence;
- treat a checked box as proof of understanding, voluntariness, capacity, or informed consent;
- create a consent form or legal attestation.

## Informed preference versus informed consent

The template documents an informed preference and shared-decision process. It does not replace:

- jurisdiction-specific informed-consent requirements;
- procedure- or product-specific consent;
- capacity evaluation;
- surrogate or guardian authority review;
- language-access or accessibility requirements;
- research consent;
- local refusal or declination documentation.

The authorized local team decides which separate records are required.

## Communication quality

The record may note whether the clinician documented:

- benefits, harms, and material uncertainty;
- alternatives, including no action, when actually discussed;
- questions and responses;
- language, interpreter, communication, or accessibility support;
- decision aid identity and version;
- need for revisiting the decision.

Do not infer quality from presence alone. Do not score the conversation.

## Transition handoff

WHO transition guidance supports timely, accurate information transfer, medication reconciliation, patient/carer involvement, clear ownership, standardized processes, checklists, and tracking.

A handoff record should identify:

- sending and receiving settings and responsible roles;
- exact handoff date supplied by the clinical team;
- source records and their versions;
- interventions, goals, monitoring, checkpoints, and pending results that were actually supplied;
- ownership of each item;
- reconciliation status;
- unresolved items and route;
- sender and recipient acknowledgment;
- local follow-up and escalation references.

The skill does not decide which clinical items are important enough to hand off. The responsible clinicians do.

## Medication reconciliation boundary

Medication reconciliation is a clinical process, not a list-diff script. The authorized team must obtain and compare the relevant lists, make clinical decisions about discrepancies, communicate the result, and document completion in approved systems.

This package may record:

- source-list fact IDs;
- destination-list fact IDs;
- `pending_authorized_review`, `completed_by_authorized_clinician`, or `not_applicable_by_authorized_clinician`;
- discrepancy status;
- reviewer role and completion time.

It must not:

- parse medication text to normalize products;
- identify duplicates, interactions, contraindications, omissions, or dose differences;
- decide which list is correct;
- propose changes;
- mark reconciliation complete automatically.

If a discrepancy is detected outside the authorized clinical workflow, leave it unresolved and route it to the named medication-reconciliation owner.

## Pending and unresolved items

Every unresolved item needs:

- a stable item ID;
- a bounded description supplied by the local team;
- source-fact references;
- responsible local role;
- route status.

An item may be `open_routed`, `acknowledged_by_owner`, or `resolved_by_authorized_professional`. The skill never selects the owner or resolution.

## Emergency routing

Do not include generated warning signs, thresholds, destinations, emergency numbers, or instructions.

Record only:

> If a concern may be urgent or emergent, stop this documentation workflow and use the institution's current clinical escalation or emergency process; this package does not determine urgency or provide emergency instructions.

The authorized institution supplies and verifies the local process reference.

## Handoff release

Before authorized documentation handoff:

- source and destination roles are named;
- all included items link to verified facts;
- reconciliation status is verified;
- unresolved items are routed;
- the recipient acknowledgment is complete;
- privacy and local governance checks pass;
- the clinician sign-off is complete;
- the release gate has no blocker codes.

These gates document process completion. They do not prove safe care, successful communication, or recipient action.
