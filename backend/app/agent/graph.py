import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from app.agent.state import AgentState
from app.agent.nodes import (
    extract_card_node,
    check_duplicate_node,
    save_contact_node,
    send_notification_node,
    process_voice_node,
    general_chat_node
)

logger = logging.getLogger(__name__)

def router_condition(state: AgentState) -> str:
    """
    Determines where to route next based on the current state.
    """
    last_message = state["messages"][-1]
    
    # Check if this message contains file attachments or approvals
    if hasattr(last_message, "additional_kwargs"):
        file_type = last_message.additional_kwargs.get("file_type")
        if file_type == "image":
            return "extract_card"
        elif file_type == "audio":
            return "process_voice"
        elif last_message.additional_kwargs.get("approved"):
            return "check_duplicate"
            
    # Check if there is a pending action we are responding to
    action = state.get("action_required")
    
    if action == "awaiting_duplicate_choice":
        content = last_message.content.lower().strip()
        if "update" in content or "overwrite" in content or "yes" in content or "1" in content:
            return "save_contact"
        elif "cancel" in content or "no" in content or "2" in content:
            return "cancel"
            
    return "general_chat"

async def cancel_node(state: AgentState) -> Dict[str, Any]:
    from langchain_core.messages import AIMessage
    return {
        "messages": [AIMessage(content="❌ Operation cancelled. The card was not saved.")],
        "card_data": None,
        "is_duplicate": False,
        "duplicate_contact": None,
        "action_required": "idle",
        "status_message": "Cancelled"
    }

def build_workflow():
    workflow = StateGraph(AgentState)
    
    # Register all nodes
    workflow.add_node("extract_card", extract_card_node)
    workflow.add_node("check_duplicate", check_duplicate_node)
    workflow.add_node("save_contact", save_contact_node)
    workflow.add_node("send_notification", send_notification_node)
    workflow.add_node("process_voice", process_voice_node)
    workflow.add_node("general_chat", general_chat_node)
    workflow.add_node("cancel_operation", cancel_node)
    
    # Define routing logic from a router start node
    workflow.set_conditional_entry_point(
        router_condition,
        {
            "extract_card": "extract_card",
            "process_voice": "process_voice",
            "save_contact": "save_contact",
            "check_duplicate": "check_duplicate",
            "cancel": "cancel_operation",
            "general_chat": "general_chat"
        }
    )
    
    # Define standard transitions
    # Once user approves OCR, the endpoint will run starting at check_duplicate
    workflow.add_conditional_edges(
        "check_duplicate",
        lambda state: "save_contact" if not state.get("is_duplicate", False) else "end",
        {
            "save_contact": "save_contact",
            "end": END
        }
    )
    
    workflow.add_edge("save_contact", "send_notification")
    workflow.add_edge("send_notification", END)
    workflow.add_edge("process_voice", END)
    workflow.add_edge("general_chat", END)
    workflow.add_edge("cancel_operation", END)
    
    # Compile the graph
    # Note: We manage persistent state manually in our DB service,
    # which allows for highly customizable checkpoints across server restarts.
    return workflow.compile()

agent_graph = build_workflow()
