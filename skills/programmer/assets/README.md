# assets/

The raw book PDFs are **not shipped** with this skill (no copies, no download
links). Tier-2 deep reference lookups (`scripts/read_book.py`) read PDFs from
this directory, so to use Tier 2 you must supply them yourself.

For each book you need, obtain a copy **you are entitled to** of the edition
listed in `SKILL.md` → *Additional Resources* — prefer a legitimate source
(publisher, library, your own copy; for *A Philosophy of Software Design*, the
author's free Stanford extract). Save it at `assets/<slug>.pdf`, e.g.
`assets/clean-code.pdf`.

The slugs and required editions are in the *Additional Resources* table in
`SKILL.md`; they must match what `references/*.md` and `read_book.py` expect.
Edition matters — several books renumber chapters between editions. Cite by
**heading text, not page or number**.
