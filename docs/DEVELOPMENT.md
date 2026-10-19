# Development

## Layout

```
.claude-plugin/               # Claude Code plugin + marketplace manifests
skills/arch-blueprint/
├── SKILL.md                  # the skill: workflow, content rules, style spec, checklist
├── assets/icons.svg          # 13 line icons as <symbol>s — copied verbatim into diagrams
├── assets/example-overview.svg
└── scripts/check.py          # stdlib-only verifier
tests/test_check.py
```

## Commands

```bash
python3 -m unittest discover -s tests -v
python3 skills/arch-blueprint/scripts/check.py skills/arch-blueprint/assets/example-*.svg
python3 skills/arch-blueprint/scripts/check.py --help    # every rule the checker enforces
```

`check.py` accepts several files and exits with 1 if any has an error. Warnings are printed but do not change the exit code.

CI (`.github/workflows/ci.yml`) runs both the unit tests and the checker on the shipped example on every push to `main` and every pull request, so a change to `SKILL.md` rules, `icons.svg` or the example must keep all three in agreement.

## Rules that live in two places

The style spec in `SKILL.md` is enforced numerically by `check.py`: two colours only, English-only text, node/edge/label limits (12 / 12 / 6), 60 px margins, container padding, node spacing, the 4 px grid, text overflow estimates, icons identical to `assets/icons.svg`, flow labels beside their own edge, and the connector rules (orthogonal only, no transit through nodes or labels, arrowheads stopping 6 px short, fan-out attach points at least 12 px apart, no overlapping strokes, a hop at every unavoidable crossing). Change a rule in one place and the other in the same commit.
