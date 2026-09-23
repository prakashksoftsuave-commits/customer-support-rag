# Week 7 Deliverable: Agent Loops vs. Fixed Sequence Workflow

Race between a hand-built **ReAct Agent** (plan -> act -> observe loop) and a **Fixed Sequence Workflow** on multi-step customer support tickets.

## 1. Executive Comparison

| Metric | Hand-Built ReAct Agent | Fixed Sequence Workflow | Winner / Trade-off |
|---|---|---|---|
| **Average Latency** | **1.79s** | **4.64s** | **ReAct Agent** (2.6x faster) |
| **LLM Calls (Cost)** | **5 calls** | **4 calls** | **Fixed Workflow** |
| **Tool Calling Flexibility** | Dynamic (selects only relevant tools) | Rigid (runs predetermined checks) | **ReAct Agent** |
| **Reliability / Loop Safety** | Guarded by max 5 steps & timeout budget | 100% deterministic execution | **Fixed Workflow** for known paths |
| **Trajectory correctness** (did it call the tools this ticket actually needed?) | **12%** avg tool-choice recall | 100% (deterministic) | **Fixed Workflow** — it can't skip a step |
| **Outcome correctness** (rule-checked against facts only a tool call could know) | **50%** | see per-ticket detail | — |

Winners are computed from the numbers above, not assumed — an earlier version of this report
hardcoded "Fixed Workflow" as the speed winner regardless of which side actually ran faster.
**Outcome-vs-trajectory gap found**: ticket_01_account_lock, ticket_03_simple_share_link — the agent's final answer passed the rule-based outcome check even though it didn't call every tool this ticket needed. See Week 8's `results/agent_failure_modes.md` for the full writeup.

## 2. When to Use Which? (Engineering Decision)

### When to use the Fixed Workflow (Recommended for Production Support):
1. **Predetermined Pathways**: When customer tickets follow a standard sequence (e.g., extract user ID -> check account status -> retrieve error code -> answer).
2. **Speed & Budget**: Fixed workflows require only 1 LLM generation call + direct deterministic tool calls, saving cost and eliminating multi-turn latency.
3. **Determinism**: Zero risk of an agent hallucinatory loop or tool misdirection.

### When to use the ReAct Agent:
1. **Dynamic & Unpredictable Problems**: When the next investigation step depends completely on unexpected observations from prior steps.
2. **Ad-Hoc Tool Exploration**: When the search space has dozens of specialized tools and running all of them in a fixed pipeline would be wasteful.

## 3. Test Cases & Step Visibility

### Ticket: Account locked & 2FA issue (`ticket_01_account_lock`)
> **User Ticket**: "Hi, I'm maria@startup.io and my account is locked out after getting error NB-AUTH-500. Can you tell me what happened and how to unlock it?"

- **ReAct Agent**: 2.5s, 2 LLM calls, 2 steps.
- **Fixed Workflow**: 10.41s, 1 LLM call.
- **Trajectory**: expected tools `['account_status', 'error_lookup']`, agent actually called `['error_lookup']` (recall=0.5), outcome_correct=True -> **RIGHT ANSWER, WRONG PATH**


#### Visible ReAct Step Trace:
- **Step 1**: Thought: *I need to find out what error NB-AUTH-500 means, so I will look it up.* -> **Action**: `error_lookup`(`NB-AUTH-500`) -> Observation: `{
  "meaning": "Account locked due to suspicious activity",
  "cause": "Multiple failed sign-in attempts",
  "resolution": "Unlock via admin console o`
- **Step 2**: Thought: *Question: Hi, I'm maria@startup.io and my account is locked out after getting error NB-AUTH-500. Can you tell me what happened and how to unlock it?
 * -> **Produced Final Answer**

---

### Ticket: Sync upload error & storage check (`ticket_02_sync_quota_conflict`)
> **User Ticket**: "User john@domain.com here. I'm trying to upload a file and getting error NB-UP-330. Is my account full or what is the issue?"

- **ReAct Agent**: 0.75s, 1 LLM calls, 1 steps.
- **Fixed Workflow**: 1.68s, 1 LLM call.
- **Trajectory**: expected tools `['account_status', 'error_lookup', 'kb_search']`, agent actually called `[]` (recall=0.0), outcome_correct=False -> **both_wrong**


#### Visible ReAct Step Trace:
- **Step 1**: Thought: *Answered directly, without the Final Answer: marker.* -> **Produced Final Answer**

---

### Ticket: Simple KB permission question (`ticket_03_simple_share_link`)
> **User Ticket**: "How do I share a folder so that only specific invited users can edit it, and commenters cannot?"

- **ReAct Agent**: 2.39s, 1 LLM calls, 1 steps.
- **Fixed Workflow**: 2.6s, 1 LLM call.
- **Trajectory**: expected tools `['kb_search']`, agent actually called `[]` (recall=0.0), outcome_correct=True -> **RIGHT ANSWER, WRONG PATH**


#### Visible ReAct Step Trace:
- **Step 1**: Thought: **** -> **Produced Final Answer**

---

### Ticket: Password reset error code diagnostic (`ticket_04_complex_auth_reset`)
> **User Ticket**: "I attempted to reset my password but got error NB-AUTH-410. Why did this happen and what should I do next?"

- **ReAct Agent**: 1.5s, 1 LLM calls, 1 steps.
- **Fixed Workflow**: 3.87s, 1 LLM call.
- **Trajectory**: expected tools `['error_lookup']`, agent actually called `[]` (recall=0.0), outcome_correct=False -> **both_wrong**


#### Visible ReAct Step Trace:
- **Step 1**: Thought: *I now know the final answer* -> **Produced Final Answer**

---

