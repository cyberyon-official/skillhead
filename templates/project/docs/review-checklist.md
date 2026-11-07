# Review checklist

Read before any review finding. A finding cites its number. Numbers are
stable: a retired rule keeps its line, struck through, and its number is
never reused (guard `review_checklist_is_numbered`).

1. Built beyond the need, "just in case" → remove.
2. Abstraction with a single caller → inline it.
3. Block copied elsewhere, changed without merging → one function.
4. Hollow intermediate layer → remove it.
5. Abbreviation in an identifier → whole word.
6. State stored instead of derived → derive it.
7. Illegal state representable → make the type forbid it.
8. Independent async calls made in series → run them together.
9. Statuses as strings instead of a union → closed union.
10. Closed value validated by regex, not by list → list.
11. Error without "what, why, what to do" → all three.
12. Flaky test: sleep, clock, network, order → make it deterministic.
13. Behaviour changed without updating the doc that describes it → same MR.
