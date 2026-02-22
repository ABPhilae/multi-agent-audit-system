from langchain_core.tools import tool
from src.config import get_settings, get_embeddings, get_llm
from src.security.presidio_service import presidio
from qdrant_client import QdrantClient
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


def get_qdrant():
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


@tool
def search_audit_findings(query: str, top_k: int = 6) -> str:
    """
    Search the audit document database for findings, observations,
    and recommendations. Use for: retrieving specific findings,
    comparing findings across regions, or finding evidence.
    """
    try:
        client = get_qdrant()
        embeddings = get_embeddings()
        vector = embeddings.embed_query(query)
        results = client.search(
            collection_name=settings.qdrant_collection,
            query_vector=vector, limit=top_k, with_payload=True
        )
        if not results:
            return 'No relevant findings found in the audit database.'
        output = []
        for i, hit in enumerate(results, 1):
            src = hit.payload.get('source', 'Unknown')
            content = hit.payload.get('page_content', '')[:700]
            # Mask PII in retrieved content before returning
            masked = presidio.anonymize(content)
            output.append(f'[{i}] {src} (score: {hit.score:.3f})\n    {masked}')
        return '\n'.join(output)
    except Exception as e:
        return f'Search failed: {str(e)}'


@tool
def check_hkma_compliance(finding_description: str) -> str:
    """
    Check an audit finding against HKMA guidelines.
    References: SPM modules, Supervisory Policy Manuals,
    AML/CFT guidelines, and Technology Risk Management guidelines.
    Use for: verifying Hong Kong regulatory alignment.
    """
    llm = get_llm(temperature=0)
    prompt = f"""As an expert in HKMA regulation, analyse this finding:
    {finding_description}

    Reference the most relevant HKMA guidelines:
    - SPM TM-G-1 (Technology Risk Management)
    - SPM SA-2 (Operational Risk)
    - AML/CFT Guideline (Anti-money laundering)
    - BCBS 239 (Risk data aggregation)

    Output:
    1. Primary regulation breach (if any)
    2. Regulatory reference (exact section)
    3. Compliance status: COMPLIANT / NON-COMPLIANT / NEEDS REVIEW
    4. Required remediation under HKMA rules"""
    from langchain_core.messages import HumanMessage
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content


@tool
def check_mas_compliance(finding_description: str) -> str:
    """
    Check an audit finding against MAS (Monetary Authority of Singapore) guidelines.
    References: MAS Notices, Technology Risk Management Guidelines (TRMG).
    Use for: Singapore regulatory alignment checks.
    """
    llm = get_llm(temperature=0)
    prompt = f"""As an expert in MAS regulation, analyse this finding:
    {finding_description}

    Reference the most relevant MAS guidelines:
    - MAS TRMG (Technology Risk Management)
    - MAS Notice 626 (AML/CFT)
    - MAS Notice 655 (PDPA obligations)
    - MAS Cyber Hygiene Notice

    Output:
    1. Primary regulation breach (if any)
    2. MAS Notice/section reference
    3. Compliance status: COMPLIANT / NON-COMPLIANT / NEEDS REVIEW
    4. Required remediation under MAS rules"""
    from langchain_core.messages import HumanMessage
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content


@tool
def assess_risk_severity(finding: str, context: str = '') -> str:
    """
    Assess the risk severity of an audit finding using a structured
    risk matrix (likelihood x impact). Returns severity rating and
    priority ranking.
    """
    llm = get_llm(temperature=0)
    prompt = f"""Perform a structured risk assessment for this finding:
    Finding: {finding}
    Context: {context or 'No additional context'}

    Use this risk matrix:
    Likelihood: 1 (Rare) to 5 (Almost Certain)
    Impact: 1 (Negligible) to 5 (Catastrophic)
    Risk Score = Likelihood x Impact

    Rating scale:
    1-4: Low | 5-9: Medium | 10-16: High | 17-25: Critical

    Output:
    - Likelihood score and justification
    - Impact score and justification
    - Risk score and rating (Low/Medium/High/Critical)
    - Business areas affected
    - Priority rank among peers (1=highest priority)"""
    from langchain_core.messages import HumanMessage
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content


@tool
def get_deadline_status(days_threshold: int = 60) -> str:
    """
    Retrieve audit findings with remediation deadlines within the
    specified number of days. Use to flag time-sensitive items.
    """
    today = datetime.now()
    # Simulated finding database (in production: query actual DB)
    findings = [
        {'id': 'HK-2024-001', 'title': 'Trade reconciliation control gap',
         'owner': 'Operations Head', 'deadline': '2026-03-15',
         'severity': 'Critical', 'status': 'In Progress'},
        {'id': 'HK-2024-007', 'title': 'AML monitoring threshold review',
         'owner': 'Chief Compliance Officer', 'deadline': '2026-02-28',
         'severity': 'Significant', 'status': 'Open'},
        {'id': 'SG-2024-003', 'title': 'Access control annual review',
         'owner': 'IT Security Manager', 'deadline': '2026-04-30',
         'severity': 'Significant', 'status': 'In Progress'},
        {'id': 'SG-2024-011', 'title': 'PDPA data retention review',
         'owner': 'Data Privacy Officer', 'deadline': '2026-06-30',
         'severity': 'Moderate', 'status': 'Open'},
        {'id': 'JP-2024-002', 'title': 'JFSA reporting automation gap',
         'owner': 'Regulatory Reporting Head', 'deadline': '2026-03-31',
         'severity': 'Significant', 'status': 'Open'},
    ]
    at_risk = []
    for f in findings:
        dl = datetime.strptime(f['deadline'], '%Y-%m-%d')
        days = (dl - today).days
        if days <= days_threshold:
            at_risk.append(
                f"{f['id']} [{f['severity']}] '{f['title']}' | "
                f"Owner: {f['owner']} | Deadline: {f['deadline']} ({days}d) | {f['status']}"
            )
    if not at_risk:
        return f'No findings due within {days_threshold} days.'
    return f'AT-RISK FINDINGS ({len(at_risk)} items):\n' + '\n'.join(at_risk)
