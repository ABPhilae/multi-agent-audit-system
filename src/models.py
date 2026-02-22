from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ReviewRequest(BaseModel):
    task: str                          # The compliance review task description
    scope: str = 'APAC'               # Geographic scope
    quarter: str = 'Q3 2025'          # Review period
    thread_id: str = 'default'
    require_approval: bool = True


class AgentStep(BaseModel):
    agent: str                         # Which agent ran
    action: str                        # What it did
    output_preview: str               # First 200 chars of output
    duration_seconds: float = 0.0
    cost_usd: float = 0.0


class ReviewResponse(BaseModel):
    report: str
    thread_id: str
    scope: str
    quarter: str
    agent_steps: List[AgentStep] = []
    total_cost_usd: float = 0.0
    total_tokens: int = 0
    requires_human_approval: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ApprovalRequest(BaseModel):
    thread_id: str
    decision: str                      # 'approved' or 'rejected'
    reviewer: str = 'Chief Audit Executive'
    notes: str = ''


class UploadResponse(BaseModel):
    filename: str
    chunks_indexed: int
    status: str


class EvaluationResult(BaseModel):
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
    overall_score: float
    questions_evaluated: int
    passed_quality_gate: bool          # True if overall_score >= 0.7
