# Coding standards

Index of the guides. Each rule lives in one guide; this file only lists
them (guard `standards_index_matches_guides`).

| Guide | Domain |
|---|---|
| `docs/agents/general.md` | Any code change |
| `docs/agents/errors.md` | Errors, validation, logs |
| `docs/agents/toolchain.md` | Build, dependencies, caches, banned commands |

A new domain (database, API, frontend…) = a new guide in `docs/agents/`,
added to this table in the same MR.

## Rule format

```
- **<The rule, in the present tense.>** <Why, in one sentence.> Check: <guard | lint | review>.
```

"Check: review" marks a rule no machine checks yet: a candidate for
`ci/guards/` or the linter.
