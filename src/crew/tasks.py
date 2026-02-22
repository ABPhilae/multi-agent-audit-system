from crewai import Task
from typing import Optional


def make_finding_review_task(agent, scope: str = 'APAC', quarter: str = 'Q3 2025') -> Task:
    return Task(
        description=f"""
        Conduct a comprehensive review of audit findings for {scope} region, {quarter}.

        Your deliverable:
        1. Retrieve all critical and significant findings from the document database
        2. For each finding, verify and record:
           - Finding ID, title, severity, and description
           - Remediation owner (named individual)
           - Target completion date
           - Current status (Open / In Progress / Closed)
           - Budget allocated
           - Evidence of progress (if In Progress)
        3. Flag any finding where required attributes are MISSING
        4. Check deadline status for all open findings
        5. Note any findings that are OVERDUE

        Be specific. Cite finding IDs. Do not paraphrase without evidence.
        """,
        expected_output=(
            'A structured table of all findings with: ID, Severity, Title, Owner, '
            'Deadline, Status, and a clear list of gaps (missing attributes or overdue items).'
        ),
        agent=agent,
    )


def make_compliance_check_task(agent, scope: str = 'APAC', finding_task: Optional[Task] = None) -> Task:
    return Task(
        description=f"""
        Based on the findings identified by the Senior Auditor, perform a
        regulatory compliance mapping for all {scope} findings.

        For each finding from the auditor's report:
        1. Identify the primary regulation(s) applicable
        2. Determine compliance status: COMPLIANT / NON-COMPLIANT / NEEDS REVIEW
        3. Cite the exact regulation reference (e.g., 'HKMA SPM TM-G-1 Section 4.2')
        4. Note the required regulatory action if non-compliant
        5. Flag any finding that represents a reportable breach to the regulator

        Jurisdictions to cover based on finding origin:
        - HK findings: HKMA guidelines
        - SG findings: MAS notices
        - JP findings: JFSA regulations
        - All findings: FATF recommendations (if AML-related)
        """,
        expected_output=(
            'A compliance mapping table: Finding ID | Regulation | Section | '
            'Status | Required Action | Reportable? — with executive conclusions.'
        ),
        agent=agent,
        context=[finding_task] if finding_task else [],
    )


def make_risk_assessment_task(agent, finding_task: Optional[Task] = None,
                               compliance_task: Optional[Task] = None) -> Task:
    return Task(
        description="""
        Perform a quantitative risk assessment of all findings using the
        standard risk matrix (Likelihood x Impact).

        Using the auditor's findings AND the compliance officer's mapping:
        1. Score each finding: Likelihood (1-5) x Impact (1-5)
        2. Assign risk rating: Low / Medium / High / Critical
        3. Rank findings by risk score (highest first)
        4. Consider:
           - Financial impact (regulatory fines, operational losses)
           - Reputational impact (regulatory censure, media exposure)
           - Operational impact (business disruption)
           - Regulatory impact (reportable breaches, licence risk)
        5. Identify top 3 risks requiring IMMEDIATE escalation
        """,
        expected_output=(
            'Risk register: Finding ID | L-Score | I-Score | Risk-Score | Rating | '
            'Priority Rank | Escalate? — sorted by risk score descending.'
        ),
        agent=agent,
        context=[t for t in [finding_task, compliance_task] if t],
    )


def make_executive_report_task(agent, finding_task=None,
                                compliance_task=None, risk_task=None) -> Task:
    return Task(
        description="""
        Synthesise all inputs from the audit team into a professional
        executive compliance report suitable for the Chief Audit Executive
        and the Board Audit Committee.

        Use the outputs from ALL three previous agents.

        Report structure (mandatory):
        # AUDIT COMPLIANCE REVIEW — [SCOPE] [QUARTER]

        ## Executive Summary (3-4 sentences maximum)

        ## Key Findings Overview
        (Summary table of all findings by severity)

        ## Compliance Status
        (Which findings are non-compliant and under which regulation)

        ## Risk Register
        (Top risks ranked by risk score from the Risk Analyst)

        ## Critical Items Requiring Immediate Action
        (Any finding rated Critical or with missed deadline)

        ## Prioritised Recommendations
        (Numbered list, highest risk first, each with: owner, deadline, action)

        ## Upcoming Deadline Alerts
        (Findings due within 30 days)

        ## Conclusion

        Keep the total report under 800 words. Be direct and specific.
        """,
        expected_output='A complete, professionally formatted executive audit compliance report.',
        agent=agent,
        context=[t for t in [finding_task, compliance_task, risk_task] if t],
    )
