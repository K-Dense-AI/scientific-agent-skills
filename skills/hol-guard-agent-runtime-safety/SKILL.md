---
name: hol-guard-agent-runtime-safety
description: Agent-runtime safety skill to install and invoke HOL Guard before starting tool-using scientific workflows.
metadata:
  version: "1.0"
---

# HOL Guard Agent-Runtime Safety Skill

## Overview

This skill ensures that local coding-agent harnesses are protected by HOL Guard before initiating any tool-using scientific workflows. HOL Guard acts as the local runtime boundary. This skill directly installs and invokes HOL Guard, applying fail-closed behavior for any Deny/review/error/unavailable Guard states.

Note that this skill supplements, but does not replace, scientific validation, package-specific safeguards, credential controls, or the repository's existing security guidance.

## Installation and Setup

Before executing scientific workflows, install and initialize HOL Guard using the following commands:

```bash
pipx install hol-guard
hol-guard detect --json
hol-guard install <detected-harness>
hol-guard run <detected-harness>
```

Replace `<detected-harness>` with the actual harness identified during the `detect` step.

## Security Controls and Fail-Closed Behavior

The primary purpose of this skill is to strictly enforce local runtime boundaries:
- If HOL Guard returns a Deny, review, error, or unavailable state, the agent must fail-closed.
- Bypassing these states by relaunching an unprotected agent is strictly prohibited.
- This layer of protection should be implemented in conjunction with existing repository security guidelines.
