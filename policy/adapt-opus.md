# Session model adaptation: Opus

This session's chair is Opus, not Fable. These overrides win over the base policy:

- `architect` runs on your own tier, so delegating to it saves no cost. Use it only for context isolation or an independent second opinion on high-risk work. Complex implementation and deep debugging stay with you (or in an `architect` spawn purely to keep your context lean).
- Everything else applies as written: `executor` (Sonnet), `scout` (Haiku), and `verifier` (Sonnet) are cheaper tiers — keep routing labor to them.
- High-risk closes still verify on `verifier` with `model: "opus"` — fresh eyes matter more than tier savings there.
