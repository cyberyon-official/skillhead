# {{PROJECT}}

<One sentence: what the project does and for whom.>

## Getting started

<Prerequisites and launch command: see `.claude/skills/verify/SKILL.md`.>

## Verify

```sh
python3 ci/check.py          # merge gate: steps of ci/gates.json + guards
python3 ci/check.py --guards # guards only
```

Instructions for agents and humans start from `CLAUDE.md`.
