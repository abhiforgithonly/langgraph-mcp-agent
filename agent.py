# agent.py
from __future__ import annotations

import argparse
import json
import requests
import yaml
from typing import Any, Dict, List, Literal, TypedDict

from typing_extensions import NotRequired
from rich.console import Console
from rich.table import Table

# LangGraph
from langgraph.graph import StateGraph, END


# ---------------------------
# State definition
# ---------------------------

class SupportState(TypedDict, total=False):
    # Input schema
    customer_name: str
    email: str
    query: str
    priority: str
    ticket_id: str

    # Derived fields
    parsed: NotRequired[Dict[str, Any]]
    entities: NotRequired[Dict[str, Any]]
    normalized: NotRequired[Dict[str, Any]]
    enriched: NotRequired[Dict[str, Any]]
    flags: NotRequired[Dict[str, Any]]

    # AI-enhanced fields
    intent: NotRequired[str]
    sentiment: NotRequired[str]
    ai_response: NotRequired[str]
    customer_history: NotRequired[List[Dict[str, Any]]]

    # Clarification loop
    clarification_question: NotRequired[str]
    clarification_answer: NotRequired[str]

    # Retrieval
    kb_results: NotRequired[List[Dict[str, Any]]]

    # Decide
    solution_score: NotRequired[int]
    escalated: NotRequired[bool]
    decision_notes: NotRequired[str]

    # Ticket updates
    ticket_updates: NotRequired[Dict[str, Any]]
    closed: NotRequired[bool]

    # Output / messaging
    draft_response: NotRequired[str]
    api_actions: NotRequired[List[str]]
    notifications: NotRequired[List[str]]

    # Logging
    logs: NotRequired[List[str]]


def log(state: SupportState, message: str) -> None:
    state.setdefault("logs", []).append(message)


# ---------------------------
# MCP HTTP client
# ---------------------------

class MCPClientHTTP:
    def __init__(self, name: str, base_url: str, api_key: str | None = None):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def call(self, ability: str, payload: Dict[str, Any], state: SupportState) -> Dict[str, Any]:
        url = f"{self.base_url}/abilities/{ability}"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        body = {"payload": payload, "state": state}

        try:
            resp = requests.post(url, headers=headers, json=body, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            log(state, f"[{self.name}] {ability} → {json.dumps(result, ensure_ascii=False)}")
            return result
        except Exception as e:
            log(state, f"[{self.name}] {ability} failed: {str(e)}")
            return {}


# ---------------------------
# Load configuration
# ---------------------------

def load_config(path: str = "agent_config.yaml") -> Dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


CONFIG = load_config()

# Build clients from config
CLIENTS = {
    "COMMON": MCPClientHTTP("COMMON", CONFIG["servers"]["COMMON"]),  # OpenAI MCP
    "ATLAS": MCPClientHTTP("ATLAS", CONFIG["servers"]["ATLAS"]),     # MongoDB MCP
}

# Build ability mapping dynamically from stages in config
ABILITY_TO_CLIENT: Dict[str, str] = {}
for stage in CONFIG["stages"]:
    abilities = stage.get("abilities", [])
    servers = stage.get("servers") or stage.get("server")
    if isinstance(servers, list):
        for ab, srv in zip(abilities, servers):
            ABILITY_TO_CLIENT[ab] = srv
    else:
        for ab in abilities:
            ABILITY_TO_CLIENT[ab] = servers


def call_ability(ability: str, payload: Dict[str, Any], state: SupportState) -> Dict[str, Any]:
    server = ABILITY_TO_CLIENT.get(ability, "COMMON")
    client = CLIENTS[server]
    return client.call(ability, payload, state)


# ---------------------------
# Stage node functions
# ---------------------------

def node_intake(state: SupportState) -> Dict[str, Any]:
    call_ability("accept_payload", {}, state)
    log(state, "INTAKE complete.")
    return {}


def node_understand(state: SupportState) -> Dict[str, Any]:
    update = {}
    update.update(call_ability("parse_request_text", {}, state))
    update.update(call_ability("extract_entities", {}, state))
    update.update(call_ability("extract_intent", {}, state))
    update.update(call_ability("sentiment_analysis", {}, state))
    log(state, "UNDERSTAND complete.")
    return update


def node_prepare(state: SupportState) -> Dict[str, Any]:
    update = {}
    update.update(call_ability("normalize_fields", {}, state))
    update.update(call_ability("enrich_records", {}, state))
    update.update(call_ability("add_flags_calculations", {}, state))
    
    # Get customer history from MongoDB
    history_result = call_ability("get_customer_history", {}, state)
    if history_result:
        update.update(history_result)
    
    log(state, "PREPARE complete.")
    return update


def node_ask(state: SupportState) -> Dict[str, Any]:
    update = call_ability("clarify_question", {}, state)
    log(state, "ASK complete.")
    return update


def node_wait(state: SupportState) -> Dict[str, Any]:
    update = {}
    update.update(call_ability("extract_answer", {}, state))
    update.update(call_ability("store_answer", {}, state))
    log(state, "WAIT complete.")
    return update


def node_retrieve(state: SupportState) -> Dict[str, Any]:
    update = {}
    # Search knowledge base using both Atlas and MongoDB
    update.update(call_ability("knowledge_base_search", {}, state))
    update.update(call_ability("search_knowledge_base", {}, state))
    update.update(call_ability("store_data", {}, state))
    log(state, "RETRIEVE complete.")
    return update


def node_decide(state: SupportState) -> Dict[str, Any]:
    update = call_ability("solution_evaluation", {}, state)
    log(state, "DECIDE scored solution.")
    return update


def decide_router(state: SupportState) -> Literal["UPDATE", "CREATE"]:
    score = state.get("solution_score", 0)
    if score < 90:
        state.update(call_ability("escalation_decision", {}, state))
        state.update(call_ability("update_payload", {}, state))
        log(state, f"Router: score {score} < 90 → UPDATE.")
        return "UPDATE"
    else:
        state.update({"escalated": False})
        state.update(call_ability("update_payload", {}, state))
        log(state, f"Router: score {score} ≥ 90 → CREATE.")
        return "CREATE"


def node_update(state: SupportState) -> Dict[str, Any]:
    update = {}
    # Update ticket in both Atlas and MongoDB
    update.update(call_ability("update_ticket", {}, state))
    update.update(call_ability("close_ticket", {}, state))
    update.update(call_ability("update_ticket_status", {}, state))
    
    # Store ticket data in MongoDB
    call_ability("store_ticket", {}, state)
    
    log(state, "UPDATE complete.")
    return update


def node_create(state: SupportState) -> Dict[str, Any]:
    update = {}
    # Generate response using both COMMON and OpenAI
    update.update(call_ability("response_generation", {}, state))
    
    # Use OpenAI for enhanced response generation
    openai_response = call_ability("generate_response", {
        "system_message": "You are a professional customer support agent. Generate a helpful, empathetic response."
    }, state)
    
    if openai_response.get("draft_response"):
        # Use OpenAI response if available, fallback to common response
        update["draft_response"] = openai_response["draft_response"]
    
    log(state, "CREATE complete.")
    return update


def node_do(state: SupportState) -> Dict[str, Any]:
    update = {}
    update.update(call_ability("execute_api_calls", {}, state))
    update.update(call_ability("trigger_notifications", {}, state))
    
    # Store conversation log in MongoDB
    call_ability("store_conversation_log", {}, state)
    
    log(state, "DO complete.")
    return update


def node_complete(state: SupportState) -> Dict[str, Any]:
    out = call_ability("output_payload", {}, state)
    log(state, "COMPLETE done.")
    return out


# ---------------------------
# Build the graph
# ---------------------------

def build_graph():
    graph = StateGraph(SupportState)

    graph.add_node("INTAKE", node_intake)
    graph.add_node("UNDERSTAND", node_understand)
    graph.add_node("PREPARE", node_prepare)
    graph.add_node("ASK", node_ask)
    graph.add_node("WAIT", node_wait)
    graph.add_node("RETRIEVE", node_retrieve)
    graph.add_node("DECIDE", node_decide)
    graph.add_node("UPDATE", node_update)
    graph.add_node("CREATE", node_create)
    graph.add_node("DO", node_do)
    graph.add_node("COMPLETE", node_complete)

    graph.set_entry_point("INTAKE")
    graph.add_edge("INTAKE", "UNDERSTAND")
    graph.add_edge("UNDERSTAND", "PREPARE")
    graph.add_edge("PREPARE", "ASK")
    graph.add_edge("ASK", "WAIT")
    graph.add_edge("WAIT", "RETRIEVE")
    graph.add_edge("RETRIEVE", "DECIDE")

    graph.add_conditional_edges("DECIDE", decide_router, {"UPDATE": "UPDATE", "CREATE": "CREATE"})

    graph.add_edge("UPDATE", "DO")
    graph.add_edge("CREATE", "DO")
    graph.add_edge("DO", "COMPLETE")
    graph.add_edge("COMPLETE", END)

    return graph.compile()


# ---------------------------
# Demo runner
# ---------------------------

DEMO_INPUT = {
    "customer_name": "Aisha Jain",
    "email": "AISHA@EXAMPLE.COM ",
    "query": "My order #A123 arrived damaged. Need a replacement ASAP.",
    "priority": "High",
    "ticket_id": "TCK-1001",
    "clarification_answer": "Ship replacement to: 221B Baker Street, London."
}


def print_summary(final_state: SupportState) -> None:
    console = Console()
    console.rule("[bold]Final Structured Payload[/bold]")
    payload = final_state.get("output", final_state)

    table = Table(show_lines=True)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    
    # Enhanced fields to display
    fields_to_show = [
        "customer_name", "email", "priority", "ticket_id", "intent", "sentiment", 
        "entities", "normalized", "enriched", "flags", "customer_history",
        "solution_score", "escalated", "ticket_updates", "closed", 
        "draft_response", "ai_response", "api_actions", "notifications"
    ]
    
    for key in fields_to_show:
        if key in payload and payload[key] not in (None, [], {}):
            value = payload[key]
            if isinstance(value, (dict, list)):
                display_value = json.dumps(value, ensure_ascii=False, indent=2)
            else:
                display_value = str(value)
            table.add_row(key, display_value)
    
    console.print(table)

    console.rule("[bold]Execution Logs[/bold]")
    for line in payload.get("logs", []):
        console.print(f"- {line}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="Run a demo with sample input.")
    parser.add_argument("--input", type=str, help='JSON string with input payload.')
    args = parser.parse_args()

    app = build_graph()

    if args.demo:
        state: SupportState = dict(DEMO_INPUT)
        final_state = app.invoke(state)
        print_summary(final_state)
        return

    if args.input:
        state = json.loads(args.input)
        final_state = app.invoke(state)
        print_summary(final_state)
        return

    print("Use --demo or --input '{...json...}'")


if __name__ == "__main__":
    main()