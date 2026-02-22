import logging
from dataclasses import dataclass, field
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)

# OpenAI pricing (gpt-4o-mini, per 1M tokens)
COST_PER_1K_INPUT = 0.000150
COST_PER_1K_OUTPUT = 0.000600


@dataclass
class RequestCost:
    thread_id: str
    agent_name: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class CostTracker:
    """Tracks per-agent, per-request token usage and cost."""

    def __init__(self):
        self._records: List[RequestCost] = []

    def record(self, thread_id: str, agent_name: str,
                input_tokens: int, output_tokens: int) -> float:
        cost = (input_tokens * COST_PER_1K_INPUT / 1000
                + output_tokens * COST_PER_1K_OUTPUT / 1000)
        self._records.append(RequestCost(
            thread_id=thread_id, agent_name=agent_name,
            input_tokens=input_tokens, output_tokens=output_tokens, cost_usd=cost
        ))
        return cost

    def get_summary(self) -> dict:
        total_cost = sum(r.cost_usd for r in self._records)
        by_agent: Dict[str, float] = {}
        for r in self._records:
            by_agent[r.agent_name] = by_agent.get(r.agent_name, 0) + r.cost_usd
        return {
            'total_cost_usd': round(total_cost, 6),
            'total_requests': len(self._records),
            'cost_by_agent': {k: round(v, 6) for k, v in by_agent.items()},
            'records': [r.__dict__ for r in self._records[-20:]],  # Last 20
        }

    def reset(self):
        self._records.clear()
