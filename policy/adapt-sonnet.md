# Session model adaptation: Sonnet

This session's chair is Sonnet, not Fable. These overrides win over the base policy:

- Implementation is your own tier: do scoped edits inline, using `executor` only for context isolation or parallel edit streams.
- Discovery and bulk reading still go to `scout` (Haiku) — that keeps your context lean, which is the main win at this tier.
- `architect` (Opus) now costs MORE than you: reserve it for problems you attempted and could not solve, and for high-risk review.
- The Ledger and fresh-eyes verification rules apply unchanged — they protect quality, not just cost.
