---
name: verify
description: Launch pack of skillhead — how to run, seed, probe and stop the application locally, per loop slot. Read before any QA, e2e run or local launch of the app.
---

# Launch pack — skillhead

Authoritative for `/loop-issues` (Step 0, QA launch pack) and for `qa`.
Every missing value is a line to add in the next lot. `<s>` = slot
number (1, 2…); slot 0 is kept for repairing the default branch.

## Gates

- Merge gate: `python3 ci/check.py`
- Command that merges a lot into the integration branch: <command>
- Certifying gate (status posted on a pushed sha): <script and status name | none>
- Lint scope: <whole-file | added-lines>

## Slot

- Disk threshold (GB): 20
- Test clone sweep command: <command | ->
- Test clone pattern: <pattern | none>
- Stale-schema signal (regex on the gate output): <regex | none>
- Slot database recreation: <command | none>
- Slot env block (`KEY=value`, `<s>` substituted):

```
DATABASE_URL=<database url of slot <s>>
PORT=<base port + <s>>
```

## QA stack

- Database preparation: <command>
- Versioned seed recipe: <path>
- Launch: <command, with the slot's port>
- Ports per slot: <list>
- Ready when: <probe, e.g. `curl -sf http://127.0.0.1:<port>/health`>
- Dependency probes (`<dependency>=<command>`): <idp=…, cors=…>
- Dev sign-in: <how to sign in without the real provider>
- Report directory: <path>
