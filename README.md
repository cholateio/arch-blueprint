# arch-blueprint

You open a repo, yours or someone else's, and want one picture of how its parts connect. Ask your coding agent to draw its architecture, and you get a single black-and-white, blueprint-style SVG at `docs/architecture/overview.svg` that a script has checked before it reaches you.

![Example overview of a document-search app drawn in thin black lines on cream: a browser SPA calls an API server and a query service, which reads PostgreSQL and a vector database and calls an LLM API, while an offline ingest pipeline fills object storage and the vector index](skills/arch-blueprint/assets/example-overview.svg)

- **Proposal first**: the agent reads the README, entry points, folder layout and imports, then lists zones, nodes and data flows as text and waits for your confirmation before drawing.
- **One page**: at most 12 nodes, 12 connectors and 6 flow labels. A project that does not fit goes back to the proposal for a coarser breakdown, never to a smaller font.
- **Fixed style**: cream paper `#faf8f4` and ink `#1a1a1a` only, dashed rounded boxes for layers, 24 px line icons from a bundled set of 13, open V-shaped arrowheads, JetBrains Mono, and English text whatever language you prompt in.
- **Script-checked**: `check.py` measures colours, language, counts, 60 px margins, the 4 px grid, text overflow, icons copied verbatim, and connector rules such as right angles only, no lines through nodes or labels, and a hop at every unavoidable crossing. It exits with 1 on any error.

The checker on a draft with a stray colour and a Chinese label:

```
$ python3 skills/arch-blueprint/scripts/check.py overview.svg
```

```
✗ overview.svg  (11 錯誤, 0 警告)
    E-LANG: 文字「瀏覽器」含中日韓字元；圖內文字一律英文
    E-COLOR: <path > stroke="#d33" 不是米白 #faf8f4 或墨黑 #1a1a1a
    E-COLOR: <symbol icon-browser> stroke="#d33" 不是米白 #faf8f4 或墨黑 #1a1a1a
    …
```

The skill's instructions and the checker's messages are written in Traditional Chinese; the diagrams are always in English.

## How it works

```
"draw the architecture" ──► agent reads README, entry points, imports
                                    │
              proposal: zones × nodes × flows ──► you confirm or adjust
                                    │
          docs/architecture/overview.svg ──► check.py ──► fixes until 0 errors
```

The skill is a text file of instructions plus one Python script. Nothing is installed and nothing connects to the network.

## Install

You need a coding agent that reads [Agent Skills](https://agentskills.io), such as Claude Code, Codex, Cursor or Gemini CLI, and Python 3 for the checker.

1. Add the skill with `npx skills add cholateio/arch-blueprint`. In Claude Code you can instead run `/plugin marketplace add cholateio/arch-blueprint`, then `/plugin install arch-blueprint@arch-blueprint`. Or copy `skills/arch-blueprint/` into your host's skills folder (`~/.claude/skills/` for Claude Code).
2. Read `skills/arch-blueprint/SKILL.md` once. It is everything your agent will be told to do.
3. In any project, ask "draw an architecture overview of this repo" and answer the proposal.

## Privacy & security

- A skill is plain-text instructions that your agent follows with your permissions. Read `SKILL.md` before installing it.
- `check.py` uses only the Python standard library. It reads the SVG files you pass it and nothing else.
- The skill sends nothing anywhere itself; your agent reads the repo inside your own session.
- The diagram is one self-contained SVG. The checker rejects external images, gradients, filters and shadows.

## License

[MIT](LICENSE). The structure and the idea of a script-verified taste gate were inspired by [cathrynlavery/diagram-design](https://github.com/cathrynlavery/diagram-design); the visual style is its own.
