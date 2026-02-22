from typing import TypedDict, Annotated, Optional, List
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class SupervisorState(TypedDict):
    """Shared state flowing through the LangGraph Supervisor."""
    messages: Annotated[List[BaseMessage], add_messages]

    # Classification
    task_type: str              # 'quick_question' or 'full_review'

    # Review parameters
    scope: str
    quarter: str

    # Quick RAG answer (for simple questions)
    quick_answer: str

    # Full crew output (for compliance reviews)
    crew_report: str
    requires_escalation: bool

    # Approval gate
    needs_human_approval: bool
    approval_granted: bool

    # Final output
    final_report: str

    # Execution trace
    steps_taken: List[str]
    agent_steps: List[dict]     # Per-agent detail for UI

    # Cost tracking
    total_cost_usd: float
    total_tokens: int

    thread_id: str
