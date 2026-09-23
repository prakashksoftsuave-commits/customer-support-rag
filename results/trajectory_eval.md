# Week 8: Outcome-vs-Trajectory Gap

Each of the 4 tickets from Week 7's race was run 5 times through the fixed ReAct agent (same code as `race_agent_vs_workflow.py`, no injection defenses in play here — this is purely about trajectory correctness). Repeated trials, not a single run, because Week 6 already found this model isn't fully deterministic even at temperature=0.

## Summary

- Overall tool-choice recall across all 20 trials: **68%**
- Overall outcome-correct rate: **95%**
- **Right-answer-wrong-path cases: 9/20 (45%)** — the agent's final answer passed the rule-based outcome check without having called every tool the ticket needed to actually know that.

| Ticket | Trials | Avg tool recall | Outcome-correct rate | Right-answer-wrong-path | Both wrong |
|---|---|---|---|---|---|
| `ticket_01_account_lock` | 5 | 90% | 100% | 1 | 0 |
| `ticket_02_sync_quota_conflict` | 5 | 60% | 80% | 4 | 1 |
| `ticket_03_simple_share_link` | 5 | 20% | 100% | 4 | 0 |
| `ticket_04_complex_auth_reset` | 5 | 100% | 100% | 0 | 0 |

## Evidence: a real right-answer-wrong-path case

`ticket_01_account_lock`, trial 1: expected tools `['account_status', 'error_lookup']`, agent actually called `['error_lookup']` (recall=0.5), yet the final answer still passed the rule-based outcome check:

> Hello Maria,

I’m sorry you’re unable to access your account. The error **NB‑AUTH‑500** indicates that your account was automatically locked because the system detected suspicious activity – most commonly a series of failed sign‑in attempts.

**How to unlock your account**

1. **If you have an admin or IT team**  
   - Ask an admin to open the **Admin Console** → **User Management** → locate your user (maria@startup.io).  
   - Select the user and click **“Unlock Account.”**  
   - The admin should also review recent sign‑in activity to ensure there’s no ongoing security risk.

2. **If you don

This is the agent confidently answering from its own general knowledge/guesswork instead of the tool data it never actually fetched — it happened to be right this time, which is exactly why it's dangerous: nothing here would have caught it if it had guessed wrong.
