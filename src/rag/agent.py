import os
import re
import json
import time
from dataclasses import dataclass, field
from typing import Callable, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq

from src.rag.config import GROQ_API_KEY, GROQ_MODEL, SECTION_AWARE
from src.rag.vectorstore import get_vectorstore
from src.rag.tracing import with_tracing

# ==========================================
# 1. TOOL DEFINITIONS
# ==========================================

_vectorstore = None

def get_kb_retriever():
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = get_vectorstore(SECTION_AWARE.collection)
    return _vectorstore

def kb_search_tool(query: str) -> str:
    """Search the customer support knowledge base for policy, troubleshooting, and feature details."""
    vs = get_kb_retriever()
    docs = vs.similarity_search(query, k=3)
    if not docs:
        return "No relevant KB articles found."
    return "\n\n".join([f"[{d.metadata.get('chunk_id', 'doc')}] {d.page_content}" for d in docs])


MOCK_ERROR_CODES = {
    "NB-SYNC-101": {
        "meaning": "Local file changed while previous upload still in flight",
        "cause": "Concurrent edit on the same device",
        "resolution": "Wait for the current upload to finish; the app will automatically sync the newer version"
    },
    "NB-SYNC-204": {
        "meaning": "Folder deleted in cloud before local sync completed",
        "cause": "Remote deletion from another device",
        "resolution": "Move the file out of the missing folder locally, then re-add it to a valid folder and sync"
    },
    "NB-UP-330": {
        "meaning": "Upload exceeds 2 GB single-file limit",
        "cause": "Large file size",
        "resolution": "Compress into a zip archive or split into smaller parts before uploading"
    },
    "NB-UP-317": {
        "meaning": "Upload interrupted by network change",
        "cause": "Switching from Wi-Fi to cellular mid-upload",
        "resolution": "Re-connect to a stable network; the app will resume the upload from where it stopped"
    },
    "NB-AUTH-410": {
        "meaning": "Password reset link expired",
        "cause": "Link older than 30 minutes",
        "resolution": "Request a new reset link from the sign-in screen"
    },
    "NB-AUTH-423": {
        "meaning": "Too many incorrect 2FA codes entered",
        "cause": "Brute-force attempts or user typo",
        "resolution": "Wait 15 minutes before retrying or use a backup code"
    },
    "NB-AUTH-500": {
        "meaning": "Account locked due to suspicious activity",
        "cause": "Multiple failed sign-in attempts",
        "resolution": "Unlock via admin console or advise user to contact security team"
    },
    "NB-SHARE-512": {
        "meaning": "Share link opened after owner disabled link sharing",
        "cause": "Owner changed sharing settings to 'Invited people only'",
        "resolution": "Ask the owner to re-create a new share link or send a direct invite"
    },
    "NB-SHARE-600": {
        "meaning": "Permission denied when accessing shared file",
        "cause": "User lacks sufficient role (Viewer/Commenter/Editor)",
        "resolution": "Verify the user's role in the sharing settings and adjust if needed"
    }
}

def error_lookup_tool(error_code: str) -> str:
    """Lookup exact diagnostic meaning, root cause, and recommended resolution for Nimbus error codes (e.g. NB-SYNC-101, NB-AUTH-410)."""
    code = error_code.strip().upper()
    info = MOCK_ERROR_CODES.get(code)
    if not info:
        return f"Error code '{code}' is not recognized in official documentation."
    return json.dumps(info, indent=2)


MOCK_USER_ACCOUNTS = {
    "alex@company.com": {"status": "active", "tier": "enterprise", "2fa_enabled": True, "failed_logins": 0, "storage_used_gb": 45, "storage_limit_gb": 100},
    "maria@startup.io": {"status": "locked", "tier": "pro", "2fa_enabled": True, "failed_logins": 5, "storage_used_gb": 18, "storage_limit_gb": 20},
    "john@domain.com": {"status": "active", "tier": "free", "2fa_enabled": False, "failed_logins": 0, "storage_used_gb": 2.1, "storage_limit_gb": 2.0}
}

def account_status_tool(email: str) -> str:
    """Inspect account health, lock status, storage quota, and subscription tier for a user by email."""
    email_clean = email.strip().lower()
    acc = MOCK_USER_ACCOUNTS.get(email_clean)
    if not acc:
        return f"No customer account found for email: '{email_clean}'."
    return json.dumps(acc, indent=2)


AVAILABLE_TOOLS = {
    "kb_search": {
        "fn": kb_search_tool,
        "description": "kb_search(query: str) -> Search documentation for feature guides, sync limits, sharing rules, and support articles."
    },
    "error_lookup": {
        "fn": error_lookup_tool,
        "description": "error_lookup(error_code: str) -> Get direct meaning, cause, and fix for error codes like NB-AUTH-410 or NB-SYNC-101."
    },
    "account_status": {
        "fn": account_status_tool,
        "description": "account_status(email: str) -> Check user account status (locked, active), subscription tier, and storage usage."
    }
}


# ==========================================
# 2. HAND-BUILT ReAct AGENT (Visible Loop)
# ==========================================

@dataclass
class AgentStep:
    step_num: int
    thought: str
    action: str | None
    action_input: str | None
    observation: str | None
    timestamp: float = field(default_factory=time.time)

@dataclass
class AgentResult:
    final_answer: str
    steps: list[AgentStep]
    total_duration_sec: float
    llm_calls: int
    stopped_by_limit: bool = False

REACT_PROMPT = """You are an expert customer support agent resolving complex customer tickets.
You have access to the following tools:
{tool_descriptions}

Use the following format:

Question: the input ticket to resolve
Thought: you should always think about what to do next
Action: the action to take, exactly one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat up to {max_steps} times)
Thought: I now know the final answer
Final Answer: the complete, polite, and actionable response for the customer

Begin!

{agent_memory}
Question: {question}
{scratchpad}"""

def _invoke_with_retry(llm, prompt: str, max_retries: int = 6) -> str:
    delay = 1.5
    for attempt in range(max_retries):
        try:
            return llm.invoke(prompt).content
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "rate limit" in err_str:
                time.sleep(delay)
                delay *= 2
            elif attempt == max_retries - 1:
                raise e
            else:
                time.sleep(delay)
    return ""


class SupportReActAgent:
    def __init__(self, model_name: str = GROQ_MODEL, max_steps: int = 5, timeout_sec: float = 40.0):
        self.llm = ChatGroq(model=model_name, api_key=GROQ_API_KEY, temperature=0)
        self.max_steps = max_steps
        self.timeout_sec = timeout_sec
        self.tools = AVAILABLE_TOOLS

    def _render_tool_descriptions(self) -> str:
        return "\n".join([f"- {name}: {meta['description']}" for name, meta in self.tools.items()])

    def solve(self, ticket_text: str, memory_context: str = "") -> AgentResult:
        start_time = time.time()
        steps: list[AgentStep] = []
        scratchpad = ""
        llm_calls = 0

        tool_descriptions = self._render_tool_descriptions()
        tool_names = ", ".join(self.tools.keys())

        for step_i in range(1, self.max_steps + 1):
            if time.time() - start_time > self.timeout_sec:
                return AgentResult(
                    final_answer="Request timed out while reasoning.",
                    steps=steps,
                    total_duration_sec=time.time() - start_time,
                    llm_calls=llm_calls,
                    stopped_by_limit=True
                )

            # Build full prompt
            prompt_content = REACT_PROMPT.format(
                tool_descriptions=tool_descriptions,
                tool_names=tool_names,
                max_steps=self.max_steps,
                agent_memory=f"Context/User Memory: {memory_context}\n" if memory_context else "",
                question=ticket_text,
                scratchpad=scratchpad
            )

            # Invoke LLM with retry/backoff
            llm_calls += 1
            response = _invoke_with_retry(self.llm, prompt_content)
            
            # Check for Final Answer
            if "Final Answer:" in response:
                thought_part = response.split("Final Answer:")[0].replace("Thought:", "").strip()
                final_answer = response.split("Final Answer:", 1)[1].strip()
                steps.append(AgentStep(
                    step_num=step_i,
                    thought=thought_part if thought_part else "Found complete answer.",
                    action=None,
                    action_input=None,
                    observation=None
                ))
                return AgentResult(
                    final_answer=final_answer,
                    steps=steps,
                    total_duration_sec=time.time() - start_time,
                    llm_calls=llm_calls,
                    stopped_by_limit=False
                )

            # Parse Action and Action Input
            thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", response, re.DOTALL)
            action_match = re.search(r"Action:\s*([a-zA-Z0-9_-]+)", response)
            input_match = re.search(r"Action Input:\s*(.*?)(?=\nObservation:|$|\nThought:)", response, re.DOTALL)

            thought = thought_match.group(1).strip() if thought_match else response.strip()
            action = action_match.group(1).strip() if action_match else None
            action_input = input_match.group(1).strip().strip('"\'') if input_match else ""

            if not action or action not in self.tools:
                scratchpad += f"{response}\nObservation: Invalid tool name. Available: [{tool_names}]. Please provide Thought and Action or Final Answer.\n"
                steps.append(AgentStep(step_num=step_i, thought=thought, action=action, action_input=action_input, observation="Invalid action"))
                continue

            # Execute tool safely
            try:
                obs = self.tools[action]["fn"](action_input)
            except Exception as e:
                obs = f"Error executing {action}: {str(e)}"

            step_obj = AgentStep(
                step_num=step_i,
                thought=thought,
                action=action,
                action_input=action_input,
                observation=obs
            )
            steps.append(step_obj)

            # Append to scratchpad
            scratchpad += f"Thought: {thought}\nAction: {action}\nAction Input: {action_input}\nObservation: {obs}\n"

        return AgentResult(
            final_answer="Reached maximum reasoning step budget without completing.",
            steps=steps,
            total_duration_sec=time.time() - start_time,
            llm_calls=llm_calls,
            stopped_by_limit=True
        )


# ==========================================
# 3. FIXED WORKFLOW (Deterministic Sequence)
# ==========================================

FIXED_WORKFLOW_SYSTEM = """You are a customer support agent. Answer the customer ticket based on the extracted diagnostics and KB search results.
Synthesize the ticket details and provided information clearly and concisely."""

FIXED_PROMPT = ChatPromptTemplate.from_messages([
    ("system", FIXED_WORKFLOW_SYSTEM),
    ("human", "Customer Ticket:\n{ticket}\n\nAccount Info:\n{account_info}\n\nError Diagnostic:\n{error_diag}\n\nKB Context:\n{kb_context}\n\nGenerate resolution:")
])

class FixedSupportWorkflow:
    def __init__(self, model_name: str = GROQ_MODEL):
        self.llm = ChatGroq(model=model_name, api_key=GROQ_API_KEY, temperature=0)

    def execute(self, ticket_text: str, email: str | None = None, error_code: str | None = None) -> AgentResult:
        start_time = time.time()
        steps: list[AgentStep] = []

        if not email:
            email_m = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", ticket_text)
            email = email_m.group(0) if email_m else None

        if not error_code:
            code_m = re.search(r"NB-[A-Z]+-\d+", ticket_text, re.IGNORECASE)
            error_code = code_m.group(0) if code_m else None

        # Step 1: Fixed account check
        acc_obs = "N/A"
        if email:
            acc_obs = account_status_tool(email)
            steps.append(AgentStep(step_num=1, thought="Fixed workflow: fetch account status", action="account_status", action_input=email, observation=acc_obs))

        # Step 2: Fixed error lookup
        err_obs = "N/A"
        if error_code:
            err_obs = error_lookup_tool(error_code)
            steps.append(AgentStep(step_num=2, thought="Fixed workflow: lookup error code", action="error_lookup", action_input=error_code, observation=err_obs))

        # Step 3: Fixed single KB retrieval
        kb_obs = kb_search_tool(ticket_text)
        steps.append(AgentStep(step_num=3, thought="Fixed workflow: search KB", action="kb_search", action_input=ticket_text, observation=kb_obs))

        # Step 4: Fixed synthesis with retry
        prompt_val = FIXED_PROMPT.format(
            ticket=ticket_text,
            account_info=acc_obs,
            error_diag=err_obs,
            kb_context=kb_obs
        )
        final_answer = _invoke_with_retry(self.llm, prompt_val)

        return AgentResult(
            final_answer=final_answer,
            steps=steps,
            total_duration_sec=time.time() - start_time,
            llm_calls=1,
            stopped_by_limit=False
        )
