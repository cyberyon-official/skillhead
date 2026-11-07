# Guide: errors, validation, logs

- **An error says what, why and what to do.** The reader acts without opening the code. Check: review.
- **A closed value is validated against a list, not a regex.** A regex accepts what nobody planned. Check: review.
- **Input is validated once, at the boundary.** Past it, the type guarantees the shape. Check: review.
- **No secret and no personal data in logs.** Logs travel further than the database. Check: review.
