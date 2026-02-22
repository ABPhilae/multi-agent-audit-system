from crewai.flow.flow import Flow, start, listen, router
from src.crew.crew import build_audit_crew
import logging

logger = logging.getLogger(__name__)


class AuditComplianceFlow(Flow):
    """
    Production CrewAI Flow wrapping the 4-agent audit crew.
    Adds event-driven orchestration and severity-based routing.
    """

    def __init__(self, scope: str = 'APAC', quarter: str = 'Q3 2025'):
        super().__init__()
        self.scope = scope
        self.quarter = quarter

    @start()
    def begin_review(self):
        """Entry point: initialise the flow state."""
        logger.info(f'Starting audit review: {self.scope} {self.quarter}')
        self.state['scope'] = self.scope
        self.state['quarter'] = self.quarter
        self.state['severity_level'] = 'standard'
        self.state['requires_escalation'] = False
        return 'review_started'

    @listen('review_started')
    def run_crew(self):
        """
        Run the 4-agent crew. This is the main work step.
        The crew runs sequentially: Auditor → Compliance → Risk → Report Writer.
        """
        logger.info('Launching CrewAI specialist team...')
        crew = build_audit_crew(
            scope=self.state['scope'],
            quarter=self.state['quarter']
        )
        result = crew.kickoff()
        self.state['crew_report'] = result.raw

        # Determine severity level from the report content
        report_lower = result.raw.lower()
        if 'critical' in report_lower or 'immediate escalation' in report_lower:
            self.state['severity_level'] = 'critical'
            self.state['requires_escalation'] = True
        else:
            self.state['severity_level'] = 'standard'

        return result

    @router('run_crew')
    def check_severity(self):
        """
        Conditional route based on severity detected in the crew report.
        Critical findings require CAE escalation; standard goes direct.
        """
        if self.state.get('requires_escalation'):
            logger.warning('CRITICAL findings detected — routing to escalation')
            return 'escalate'
        return 'standard_report'

    @listen('escalate')
    def escalate_to_cae(self):
        """Add escalation header to the report before finalising."""
        escalation_header = (
            '⚠️  ESCALATION REQUIRED — CRITICAL FINDINGS IDENTIFIED\n'
            'This report contains critical audit findings that require immediate '
            'attention from the Chief Audit Executive and Risk Committee.\n'
            f'Review period: {self.state["quarter"]} | Scope: {self.state["scope"]}\n'
            '━' * 60 + '\n\n'
        )
        self.state['final_report'] = escalation_header + self.state['crew_report']
        return 'finalised'

    @listen('standard_report')
    def standard_finalise(self):
        """Finalise standard report without escalation."""
        self.state['final_report'] = self.state['crew_report']
        return 'finalised'

    @listen('finalised')
    def complete(self):
        """Return the final report and escalation flag."""
        return {
            'report': self.state['final_report'],
            'requires_escalation': self.state.get('requires_escalation', False),
            'scope': self.state['scope'],
            'quarter': self.state['quarter'],
        }


def run_audit_flow(scope: str = 'APAC', quarter: str = 'Q3 2025') -> dict:
    """Run the full audit compliance flow. Returns the final report dict."""
    flow = AuditComplianceFlow(scope=scope, quarter=quarter)
    result = flow.kickoff()
    return result if isinstance(result, dict) else flow.state
