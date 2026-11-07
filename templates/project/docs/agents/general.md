# Guide: general

Applies to every code change.

- **Build the need, not "just in case".** Speculative code is read and maintained without serving anyone. Check: review.
- **An abstraction has at least two callers.** With one, it only adds a layer to climb. Check: review.
- **A block copied elsewhere gets merged into one.** Two copies diverge at the first fix. Check: review.
- **State is derived rather than stored.** Stored state drifts out of sync. Check: review.
- **An illegal state is not representable.** The type forbids it instead of a runtime test. Check: review.
- **A status is a closed union, not a free string.** The compiler sees the forgotten cases. Check: review.
- **Independent async calls run together.** In series, their latencies add up. Check: review.
- **Identifiers use whole words.** An abbreviation is a guess for the reader. Check: review.
- **Names come from `CONTEXT.md`.** One concept has one name, from code to database. Check: review.
