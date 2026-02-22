from crewai import Crew, Process
from src.crew.agents import (
    make_auditor, make_compliance_officer, make_risk_analyst, make_report_writer
)
from src.crew.tasks import (
    make_finding_review_task, make_compliance_check_task,
    make_risk_assessment_task, make_executive_report_task
)


def build_audit_crew(scope: str = 'APAC', quarter: str = 'Q3 2025') -> Crew:
    """
    Assemble the 4-agent audit crew with sequential task execution.
    Task hand-offs: Auditor → Compliance Officer → Risk Analyst → Report Writer
    Each agent reads the previous agent's output via context=[previous_task].
    """
    # Instantiate agents
    auditor = make_auditor()
    compliance_officer = make_compliance_officer()
    risk_analyst = make_risk_analyst()
    report_writer = make_report_writer()

    # Instantiate tasks with context chain
    t1 = make_finding_review_task(auditor, scope, quarter)
    t2 = make_compliance_check_task(compliance_officer, scope, finding_task=t1)
    t3 = make_risk_assessment_task(risk_analyst, finding_task=t1, compliance_task=t2)
    t4 = make_executive_report_task(report_writer, finding_task=t1,
                                     compliance_task=t2, risk_task=t3)

    return Crew(
        agents=[auditor, compliance_officer, risk_analyst, report_writer],
        tasks=[t1, t2, t3, t4],
        process=Process.sequential,        # Tasks run in order: t1 → t2 → t3 → t4
        verbose=True,
        memory=True,                       # Crew-level shared memory
        max_rpm=20,                        # Rate limit to avoid API throttling
    )
