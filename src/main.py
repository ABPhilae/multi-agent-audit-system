import logging
import uuid
import os
import tempfile
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from src.supervisor.graph import supervisor_graph
from src.models import ReviewRequest, ReviewResponse, ApprovalRequest, UploadResponse
from src.services.cost_tracker import CostTracker
from src.security.presidio_service import presidio
from src.security.guardrails_client import guardrails
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title='Multi-Agent Audit Compliance System',
    description='LangGraph Supervisor + CrewAI Specialists + Presidio + NeMo',
    version='1.0.0'
)

cost_tracker = CostTracker()


@app.get('/health')
def health():
    from src.config import get_settings
    s = get_settings()
    return {
        'status': 'ok',
        'model_mode': 'local' if s.use_local_models else 'cloud',
        'guardrails': s.use_guardrails,
    }


@app.post('/supervisor/invoke', response_model=ReviewResponse)
async def invoke_supervisor(request: ReviewRequest):
    """
    Main endpoint: send a task to the LangGraph Supervisor.
    For quick questions: returns fast RAG answer.
    For full reviews: runs the CrewAI 4-agent pipeline.
    """
    thread_id = request.thread_id or str(uuid.uuid4())

    # Step 1: Guardrails input check
    guard_result = await guardrails.validate_input(request.task)
    if not guard_result['safe']:
        raise HTTPException(status_code=400,
            detail=f'Input blocked by guardrails: {guard_result["blocked_reason"]}')

    # Step 2: Presidio PII mask user input
    safe_task = presidio.anonymize(request.task)

    config = {'configurable': {'thread_id': thread_id}}
    initial_state = {
        'messages': [HumanMessage(content=safe_task)],
        'task_type': '',
        'scope': request.scope,
        'quarter': request.quarter,
        'quick_answer': '',
        'crew_report': '',
        'requires_escalation': False,
        'needs_human_approval': False,
        'approval_granted': False,
        'final_report': '',
        'steps_taken': [],
        'agent_steps': [],
        'total_cost_usd': 0.0,
        'total_tokens': 0,
        'thread_id': thread_id,
    }
    try:
        result = supervisor_graph.invoke(initial_state, config)

        # Step 3: Guardrails output check
        final = result.get('final_report', '')
        guard_out = await guardrails.validate_output(final)
        safe_final = guard_out.get('response', final)

        return ReviewResponse(
            report=safe_final,
            thread_id=thread_id,
            scope=request.scope,
            quarter=request.quarter,
            agent_steps=result.get('agent_steps', []),
            total_cost_usd=result.get('total_cost_usd', 0.0),
            total_tokens=result.get('total_tokens', 0),
            requires_human_approval=result.get('needs_human_approval', False),
        )
    except Exception as e:
        logger.error(f'Supervisor invocation failed: {e}')
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/supervisor/stream')
async def stream_supervisor(request: ReviewRequest):
    """Stream supervisor execution steps as Server-Sent Events."""
    thread_id = request.thread_id or str(uuid.uuid4())
    safe_task = presidio.anonymize(request.task)
    config = {'configurable': {'thread_id': thread_id}}
    initial_state = {
        'messages': [HumanMessage(content=safe_task)],
        'task_type': '', 'scope': request.scope, 'quarter': request.quarter,
        'quick_answer': '', 'crew_report': '', 'requires_escalation': False,
        'needs_human_approval': False, 'approval_granted': False,
        'final_report': '', 'steps_taken': [], 'agent_steps': [],
        'total_cost_usd': 0.0, 'total_tokens': 0, 'thread_id': thread_id,
    }

    def event_gen():
        for chunk in supervisor_graph.stream(initial_state, config, stream_mode='updates'):
            for node_name, node_output in chunk.items():
                event = {
                    'node': node_name,
                    'steps': node_output.get('steps_taken', []),
                    'report': node_output.get('final_report', ''),
                    'needs_approval': node_output.get('needs_human_approval', False),
                    'requires_escalation': node_output.get('requires_escalation', False),
                }
                yield f'data: {json.dumps(event)}\n\n'

    return StreamingResponse(event_gen(), media_type='text/event-stream')


@app.post('/supervisor/approve')
async def approve_report(request: ApprovalRequest):
    """Resume paused supervisor after human approval/rejection."""
    config = {'configurable': {'thread_id': request.thread_id}}
    try:
        result = supervisor_graph.invoke(
            None, config, command={'resume': request.decision}
        )
        final = presidio.anonymize(result.get('final_report', ''))
        return {
            'status': 'resumed',
            'decision': request.decision,
            'reviewer': request.reviewer,
            'notes': request.notes,
            'report': final,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/documents/upload', response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    from src.services.rag_service import index_document
    if not file.filename.endswith(('.pdf', '.txt')):
        raise HTTPException(status_code=400, detail='PDF or TXT files only')
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    try:
        chunks = await index_document(tmp_path, file.filename)
        return UploadResponse(filename=file.filename, chunks_indexed=chunks, status='indexed')
    finally:
        os.unlink(tmp_path)


@app.get('/costs/summary')
def get_cost_summary():
    return cost_tracker.get_summary()


@app.delete('/costs/reset')
def reset_costs():
    cost_tracker.reset()
    return {'status': 'reset'}
