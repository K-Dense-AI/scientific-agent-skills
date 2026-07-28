# Summary

<!-- What changed, and why it matters. One or two sentences is fine. -->

## Type of change

<!-- Keep the lines that apply, delete the rest. -->

- [ ] New skill
- [ ] Update to an existing skill
- [ ] Tests
- [ ] Repository tooling or CI
- [ ] Documentation
- [ ] Other:

## Skills touched

<!-- Directory names under skills/, one per line. Write "none" if this PR does not touch skills/. -->

-

## How this was tested

<!-- The commands you ran and what they reported. -->

```
uv run skills-ref validate ./skills/<name>
uv run --with pytest python -m pytest tests/<name> -q
```

## Related issues and references

<!-- Closes #123. Link upstream docs, release notes, or security findings that justify the change. -->

---

## Checklist

Drawn from the [Pull Request Checklist](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/CONTRIBUTING.md#pull-request-checklist) in CONTRIBUTING.md. Items that do not apply to this PR can be left unchecked with a short note.

**Skill format**

- [ ] The skill directory name and the `name` frontmatter match exactly.
- [ ] The skill directory contains only `SKILL.md`, `references/`, `scripts/`, and `assets/` — no `tests/` directory and no `test_*.py` files.
- [ ] `SKILL.md` has valid YAML frontmatter and a Markdown body.
- [ ] Only the six spec-defined top-level fields are present; everything else lives under `metadata`.
- [ ] `metadata` is a block mapping, not single-line JSON, and scalar values are quoted where needed.
- [ ] Any `metadata.openclaw` or `metadata.hermes` block is a nested mapping, not a JSON string.
- [ ] `metadata.version` exists, is quoted, and is bumped if an existing skill changed.
- [ ] The `description` says both what the skill does and when an agent should use it.

**Validation and tests**

- [ ] `uv run skills-ref validate ./skills/<name>` passes.
- [ ] Tests live in `tests/<skill-name>/`, and any new `scripts/` skill has a `[skills.<name>]` entry in `tests/skill-requirements.toml`.
- [ ] Relevant test suites pass, or the failures are explained below.
- [ ] Security scanner results are clean or explained in this PR.

**Content and safety**

- [ ] Examples and scripts were tested, or are clearly marked as illustrative.
- [ ] No secrets, credentials, private data, or unsafe instructions are included.
- [ ] Credentials the skill needs are named in `compatibility` and declared in `metadata.openclaw.envVars`.
- [ ] Relevant official documentation is linked where useful.

## Notes for reviewers

<!-- Anything unresolved, deliberately out of scope, or worth a closer look. -->
