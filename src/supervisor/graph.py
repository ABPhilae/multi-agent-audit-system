import logging
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt
from langchain_core.messages import HumanMessage, AIMessage
from src.supervisor.state import SupervisorState
from src.config import get_llm, get_settings, get_embeddings
from src.security.presidio_service import presidio
from src.crew.flow import run_audit_flow
from src.services.cost_tracker import CostTracker
from qdrant_client import QdrantClient
import time

logger = logging.getLogger(__name__)
settings = get_settings()
cost_tracker = CostTracker()


# ─── NODES ──────────────────────────────────────────────────────────────────

def classify_task(state: SupervisorState) -> dict:
    """
    NODE 1: Classify the user's request.
    quick_question = a specific question about a finding or document
    full_review    = a request for a comprehensive compliance review
    """
    user_msg = state['messages'][-1].content
    # Mask PII in user input before sending to LLM
    safe_msg = presidio.anonymize(user_msg)
    llm = get_llm(temperature=0)
    prompt = f"""Classify this request as 'quick_question' or 'full_review'.
    quick_question: asking about one specific finding, document, or fact.
    full_review: requesting a comprehensive audit review, compliance analysis,
                 or full report generation for a scope/quarter.
    Request: {safe_msg}
    Answer with only: quick_question or full_review"""
    response = llm.invoke([HumanMessage(content=prompt)])
    t = response.content.strip().lower()
    if t not in ['quick_question', 'full_review']:
        t = 'quick_question'
    return {
        'task_type': t,
        'steps_taken': state.get('steps_taken', []) + [f'Task classified: {t}']
    }


def quick_rag_answer(state: SupervisorState) -> dict:
    """
    NODE 2 (quick path): Direct RAG retrieval for simple questions.
    Same as Phase 3 RAG but with Presidio masking on both sides.
    """
    user_msg = state['messages'][-1].content
    safe_msg = presidio.anonymize(user_msg)
    embeddings = get_embeddings()
    client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    vector = embeddings.embed_query(safe_msg)
    results = client.search(
        collection_name=settings.qdrant_collection,
        query_vector=vector, limit=5, with_payload=True
    )
    context = '\n'.join([
        presidio.anonymize(r.payload.get('page_content', ''))[:600]
        for r in results
    ])
    llm = get_llm(temperature=0)
    prompt = f"""Answer this question using only the provided context.
    Question: {safe_msg}
    Context: {context}
    If not found in context, say so."""
    response = llm.invoke([HumanMessage(content=prompt)])
    answer = presidio.anonymize(response.content)
    return {
        'quick_answer': answer,
        'final_report': answer,
        'needs_human_approval': False,
        'steps_taken': state.get('steps_taken', []) + ['Quick RAG answer generated']
    }


def run_crew_review(state: SupervisorState) -> dict:
    """
    NODE 3 (full review path): Launch the CrewAI Flow.
    This is the main work node — it can take 5-15 minutes.
    """
    scope = state.get('scope', 'APAC')
    quarter = state.get('quarter', 'Q3 2025')
    logger.info(f'Launching CrewAI flow: {scope} {quarter}')
    start = time.time()
    result = run_audit_flow(scope=scope, quarter=quarter)
    duration = time.time() - start
    report = result.get('report', 'Crew completed — no report generated')
    report = presidio.anonymize(report)   # Mask PII in final report
    return {
        'crew_report': report,
        'requires_escalation': result.get('requires_escalation', False),
        'needs_human_approval': result.get('requires_escalation', False),
        'steps_taken': state.get('steps_taken', []) + [
            f'CrewAI flow completed in {duration:.0f}s',
            f'Escalation required: {result.get("requires_escalation", False)}'
        ]
    }


def human_approval_gate(state: SupervisorState) -> dict:
    """
    NODE 4: Pause for human approval when critical findings are detected.
    LangGraph interrupt() pauses execution; /supervisor/approve resumes it.
    """
    report_preview = state['crew_report'][:300] + '...'
    decision = interrupt(
        f'CRITICAL FINDINGS DETECTED — Human approval required before finalising report.\n'
        f'Report preview: {report_preview}'
    )
    if decision == 'approved':
        return {
            'approval_granted': True,
            'steps_taken': state.get('steps_taken', []) + ['Human approval: GRANTED']
        }
    return {
        'approval_granted': False,
        'final_report': 'Report generation rejected by reviewer.',
        'steps_taken': state.get('steps_taken', []) + ['Human approval: REJECTED']
    }


def finalise_report(state: SupervisorState) -> dict:
    """
    NODE 5: Set the final_report field. Only runs if approved or not requiring approval.
    """
    if state.get('final_report'):   # Already set (quick answer or rejected)
        return {}
    return {
        'final_report': state['crew_report'],
        'steps_taken': state.get('steps_taken', []) + ['Report finalised']
    }


# ─── ROUTING ─────────────────────────────────────────────────────────────────

def route_after_classify(state: SupervisorState) -> str:
    return 'quick_rag' if state['task_type'] == 'quick_question' else 'run_crew'


def route_after_crew(state: SupervisorState) -> str:
    return 'human_gate' if state.get('needs_human_approval') else 'finalise'


# ─── GRAPH ───────────────────────────────────────────────────────────────────

def build_supervisor_graph():
    builder = StateGraph(SupervisorState)

    builder.add_node('classify_task',    classify_task)
    builder.add_node('quick_rag',        quick_rag_answer)
    builder.add_node('run_crew',         run_crew_review)
    builder.add_node('human_gate',       human_approval_gate)
    builder.add_node('finalise',         finalise_report)

    builder.add_edge(START, 'classify_task')
    builder.add_conditional_edges('classify_task', route_after_classify,
        {'quick_rag': 'quick_rag', 'run_crew': 'run_crew'})
    builder.add_edge('quick_rag', 'finalise')
    builder.add_conditional_edges('run_crew', route_after_crew,
        {'human_gate': 'human_gate', 'finalise': 'finalise'})
    builder.add_edge('human_gate', 'finalise')
    builder.add_edge('finalise', END)

    return builder.compile(checkpointer=MemorySaver())


supervisor_graph = build_supervisor_graph()
