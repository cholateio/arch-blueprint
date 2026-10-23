<!-- Tool-neutral project memory. Never put local paths, costs or personal data here. -->
# arch-blueprint

## Project goal

A Claude Code plugin (skill) that draws a single black-and-white, blueprint-style architecture overview SVG of any software project, verified by a stdlib-only checker script before it reaches the user.

## Stack

- Language / framework: Markdown skill (`SKILL.md`) + Python 3 standard library (`check.py`); shipped as a Claude Code plugin / marketplace
- Services: none
- Test: `python3 -m unittest discover -s tests -v && python3 skills/arch-blueprint/scripts/check.py skills/arch-blueprint/assets/example-*.svg`

## File layout

- `.claude-plugin/` — Claude Code plugin + marketplace manifests
- `skills/arch-blueprint/SKILL.md` — the skill: workflow, content rules, style spec, checklist
- `skills/arch-blueprint/assets/` — `icons.svg` (13 line icons copied verbatim into diagrams) and the shipped example
- `skills/arch-blueprint/scripts/check.py` — stdlib-only verifier (exit 1 on any error)
- `tests/test_check.py` — unit tests for the checker

## Constraints

- The style spec in `SKILL.md` and its numeric enforcement in `check.py` must change together in the same commit; CI runs the unit tests and the checker on the shipped example, so `SKILL.md`, `icons.svg` and the example must stay in agreement.
- `check.py` stays standard-library only.
- Path-type constraints are mirrored in `kit.toml [protected]`; keep the two in sync (one glob per line).

## Conventions

- Conventional commits; run the test command above before committing.
- `README.md` and `README.zh-TW.md` mirror each other; update both in the same commit.
- GitHub Actions: top-level `permissions: contents: read`, raised per job only when needed.
- GitHub Actions: pin every `uses:` to a 40-character commit SHA with a trailing `# vX.Y.Z` comment.

## Where to look

- `skills/arch-blueprint/SKILL.md` — the authoritative workflow and style spec
- `docs/DEVELOPMENT.md` — layout, commands, rules that live in two places
- `python3 skills/arch-blueprint/scripts/check.py --help` — every rule the checker enforces
