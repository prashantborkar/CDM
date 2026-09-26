"""THE ACTUAL AGENT -- a genuine reasoning loop, not a fixed script. This is the modern-agentic
piece requested: instead of orchestrator/run.py's fixed sequence (sync, then plan, then deploy,
then confirm, always in that order), the model itself decides what to check, what to deploy, what
to escalate, and in what order -- by calling the tools in agent/tools.py and reasoning over their
results, the same way this very conversation has been working.

What stays deterministic on purpose (see tools.py's docstring for the full rationale): the model
can never skip pre-check/backup/verify/rollback inside deploy_certificate(), and it can never
deploy an ambiguous match or a binding with no approved profile -- those guardrails are enforced
in code, not left to the model's judgement. The model's job is everything around that: deciding
what to look at, whether a situation is normal or needs a human, and explaining its reasoning.

Uses Groq (free tier, OpenAI-compatible tool-calling) so this runs with no billing setup. Only
this file talks to the model API; agent/tools.py has no idea which provider is in charge, so
swapping providers later (Anthropic, Gemini, a local Ollama model) only ever means changing this
one file's _call_model() function.

Requires a Groq API key. Get one free at console.groq.com, then set it:
  setx GROQ_API_KEY "gsk_..."          (Windows, permanent)
  $env:GROQ_API_KEY = "gsk_..."        (current PowerShell session only)

Run:  python agent/run_agent.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# The model's own natural-language replies can contain characters (smart dashes, quotes) the
# Windows console's default codepage can't print. Force UTF-8 so a crash here never masks a real
# agent result.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

from agent.tools import TOOLS, TOOL_SCHEMAS  # noqa: E402

MODEL = "openai/gpt-oss-120b"

SYSTEM_PROMPT = """You are the Certificate Deployment Manager agent. Your job, each time you run,
is to bring every certificate binding to a safe, correct, confirmed state -- with no human needing
to do the routine work.

Do this by calling your tools and reasoning over what they return. You decide the order and what
matters. Deployment is broken into separate steps you call one at a time, in order, for each
binding you decide to deploy:
  start_deployment_job -> precheck_deployment -> backup_current_certificate ->
  fetch_certificate_bundle -> install_certificate -> activate_certificate ->
  verify_deployment -> cleanup_deployment
You decide whether to proceed past each step based on its result -- for example, if
precheck_deployment fails, stop and escalate rather than continuing to backup and install anyway.

The one part of this NOT left to your judgement: verify_deployment enforces its own rollback in
code if verification fails -- you will get back "success" or "rolled_back", already handled, never
a raw failure with the target left broken. You cannot skip this because it happens inside the tool
itself, not as a step you choose to call.

Non-negotiable rules, regardless of what seems efficient:
1. Never call start_deployment_job for a binding without first confirming, via
   get_deployment_profile, that an approved profile exists. If none exists, call
   escalate_to_human instead -- never skip it silently.
2. Never deploy a binding that find_matches reported as ambiguous or unresolved. Escalate those too,
   with the specific reason.
3. Always call cleanup_deployment when you're done with a job, whether it succeeded or rolled back.
4. After a successful verify_deployment, at some point call check_confirmation for that binding. If
   it is not yet confirmed and not enough time may have passed, say so plainly rather than guessing.
5. If verify_deployment returns status "rolled_back", do not retry it in the same run. Escalate
   with the error so a human decides whether to retry.
6. THE WORD "ESCALATE" IN YOUR OWN TEXT DOES NOTHING. The only way a binding is actually escalated
   is by making a real escalate_to_human tool call for that exact binding_id. If you say in your
   summary that you escalated something, you must have actually called that tool for it in this
   same run -- never write that you escalated something you only intended to, or forgot to call
   the tool for. A claim with no matching tool call is treated as a false report.
7. Be concise. When you're done, give a short, plain-English summary of what you found and did --
   the kind of update someone could read in ten seconds and understand exactly what happened, and
   what (if anything) needs their attention.

Start by scanning the CMDB and checking what's newly available, then decide what to do from there."""


def _claims_completed_escalation(text: str) -> bool:
    """True only when the text claims escalation actually happened (e.g. 'I escalated X',
    'was escalated'), not when it merely mentions the concept (e.g. 'no escalation needed',
    'does not require escalation'). A plain substring check on 'escalat' can't tell these apart;
    this is deliberately still a heuristic, not a guarantee -- the real backstop is that
    escalate_to_human's own side effect (the file it writes) is what's actually checked."""
    t = text.lower()
    negation_patterns = ["no escalation", "not escalat", "n't escalat", "without escalat",
                          "no human escalation", "escalation is not", "escalation was not",
                          "does not require escalation", "doesn't require escalation",
                          "no need to escalat", "nothing to escalat", "none escalat"]
    if any(p in t for p in negation_patterns):
        return False
    action_patterns = ["i escalated", "escalated the", "escalated it", "was escalated",
                       "have escalated", "escalated binding", "escalated lab-", "escalation was made"]
    return any(p in t for p in action_patterns)


def _to_openai_tools():
    """Converts tools.py's Anthropic-shaped schemas into the OpenAI/Groq tool-calling shape."""
    out = []
    for t in TOOL_SCHEMAS:
        out.append({"type": "function", "function": {
            "name": t["name"], "description": t["description"], "parameters": t["input_schema"],
        }})
    return out


def run_agent_cycle():
    from groq import Groq
    client = Groq()  # reads GROQ_API_KEY from the environment
    groq_tools = _to_openai_tools()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Run your cycle now."},
    ]
    print("=" * 70)
    print("CDM AGENT -- reasoning cycle starting (Groq / " + MODEL + ")")
    print("=" * 70)

    escalated_bindings = set()  # ground truth: which bindings actually got a real tool call
    final_text = ""
    corrected_once = False

    for turn in range(20):  # hard cap so a confused loop can't run forever
        resp = None
        last_error = None
        for attempt in range(3):  # the model occasionally emits malformed tool-call JSON; retry a
                                    # few times before giving up -- this is a real, observed glitch,
                                    # not a hypothetical one
            try:
                resp = client.chat.completions.create(
                    model=MODEL, messages=messages, tools=groq_tools, tool_choice="auto",
                )
                break
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                print(f"\n[RETRY] Model API call failed (attempt {attempt + 1}/3): {exc}")
        if resp is None:
            print(f"\n[FATAL] Giving up after repeated API failures: {last_error}")
            print("[FATAL] No certificates were touched by this cycle -- nothing to roll back.")
            return
        msg = resp.choices[0].message
        assistant_msg = {"role": "assistant", "content": msg.content}
        if msg.tool_calls:  # omit the key entirely when empty -- Groq rejects an explicit null
            assistant_msg["tool_calls"] = [tc.model_dump() for tc in msg.tool_calls]
        messages.append(assistant_msg)

        if msg.content:
            print(f"\n[agent] {msg.content}")
            final_text = msg.content

        if not msg.tool_calls:
            # No more tool calls -- this is the model's final word. Before trusting it, check its
            # claims against what actually happened (see rule 5 in the system prompt). A plain
            # substring match on "escalat" also fires on "no escalation needed" -- so only treat
            # it as a claim when it looks like a completed action, not a statement that nothing
            # needed escalating.
            claims_escalation = _claims_completed_escalation(final_text)
            if claims_escalation and not escalated_bindings and not corrected_once:
                print("\n[VERIFY] The summary claims an escalation, but no escalate_to_human call "
                      "was made in this run. Giving the model one chance to correct this.")
                messages.append({"role": "user", "content": (
                    "You said you escalated something, but no escalate_to_human tool call was made "
                    "in this session. Either call escalate_to_human now for the specific binding(s) "
                    "you meant, or correct your summary to say no escalation actually happened."
                )})
                corrected_once = True
                continue
            break

        for call in msg.tool_calls:
            args = json.loads(call.function.arguments or "{}")
            print(f"\n[tool call] {call.function.name}({json.dumps(args)})")
            try:
                result = TOOLS[call.function.name](**args)
            except Exception as exc:  # noqa: BLE001 -- surface the error to the model, don't crash the loop
                result = {"error": str(exc)}
            print(f"[tool result] {json.dumps(result)[:300]}")
            if call.function.name == "escalate_to_human" and result.get("status") == "escalated":
                escalated_bindings.add(result.get("binding_id"))
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})

    print("\n" + "=" * 70)
    if _claims_completed_escalation(final_text) and not escalated_bindings:
        print("[VERIFY] WARNING: final summary still claims an escalation with no matching tool "
              "call ever made. Treat that claim as false -- nothing was actually escalated.")
    print("CDM AGENT -- cycle complete")
    print("=" * 70)


if __name__ == "__main__":
    run_agent_cycle()
