# Session model adaptation: undetected

The chair's model could not be detected at session start. Determine your own tier (fable/opus/sonnet/haiku) and apply the matching adaptation yourself:

- **Fable:** base policy as written.
- **Opus:** `architect` is your own tier — use it only for context isolation or a second opinion; keep routing labor to executor/scout/verifier.
- **Sonnet:** implement inline at your own tier; route discovery to scout; reserve architect for failures and high-risk review.
- **Haiku:** route anything non-trivial UP (executor for implementation, architect for hard problems).

The Ledger, filesystem-as-memory, and fresh-eyes verification rules apply at every tier.
