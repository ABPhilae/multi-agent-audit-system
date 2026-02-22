from crewai import Agent
from src.config import get_settings
from src.crew.tools import (
    search_audit_findings, check_hkma_compliance,
    check_mas_compliance, assess_risk_severity, get_deadline_status
)

settings = get_settings()

# Use the model name string for CrewAI (it handles instantiation internally)
MODEL_NAME = ('ollama/llama3.2' if settings.use_local_models
               else f'openai/{settings.openai_model}')


def make_auditor() -> Agent:
    return Agent(
        role='Senior Internal Auditor',
        goal=('Conduct a thorough review of audit findings, identify control',
              ' weaknesses, and verify completeness of remediation plans.'),
        backstory=(
            'You are a Senior Internal Auditor with 15 years of experience across',
            ' APAC financial institutions. You have worked at Big Four firms and',
            ' major investment banks. You specialise in operational risk, technology',
            ' audit, and AML compliance. You are methodical, evidence-driven, and',
            ' always cite specific finding IDs and document sources. You never make',
            ' claims without supporting evidence from the documents.'
        ),
        tools=[search_audit_findings, get_deadline_status],
        llm=MODEL_NAME,
        verbose=True,
        memory=True,                      # Remembers across tasks
        max_iter=5,                        # Max reasoning iterations
        allow_delegation=False,            # Stays in their lane
    )


def make_compliance_officer() -> Agent:
    return Agent(
        role='Regional Compliance Officer',
        goal=('Map every audit finding to its relevant regulatory requirement',
              ' and determine the precise compliance status under HKMA and MAS.'),
        backstory=(
            'You are the Regional Compliance Officer for APAC, responsible for',
            ' HKMA (Hong Kong), MAS (Singapore), and JFSA (Japan) regulatory',
            ' obligations. You have a law degree and 12 years of compliance',
            ' experience at Tier-1 banks. You always cite exact regulation names',
            ' and section numbers. You are careful to distinguish between',
            ' confirmed breaches and areas requiring further review.'
        ),
        tools=[check_hkma_compliance, check_mas_compliance, search_audit_findings],
        llm=MODEL_NAME,
        verbose=True,
        memory=True,
        max_iter=5,
        allow_delegation=False,
    )


def make_risk_analyst() -> Agent:
    return Agent(
        role='Risk Analyst',
        goal=('Assess the severity and business impact of each audit finding',
              ' using a structured risk matrix, and prioritise by risk score.'),
        backstory=(
            'You are a quantitative Risk Analyst specialising in operational',
            ' and technology risk at financial institutions. You hold FRM and',
            ' CRISC certifications. You use Basel III, RCSA frameworks, and',
            ' standard risk matrices to score findings objectively. You always',
            ' consider both the probability of occurrence and the financial,',
            ' reputational, and regulatory impact of each risk.'
        ),
        tools=[assess_risk_severity, search_audit_findings],
        llm=MODEL_NAME,
        verbose=True,
        memory=True,
        max_iter=4,
        allow_delegation=False,
    )


def make_report_writer() -> Agent:
    return Agent(
        role='Chief Report Writer',
        goal=('Synthesise inputs from the audit team into a professional,',
              ' executive-ready compliance report with clear structure and actionable recommendations.'),
        backstory=(
            'You are a specialist in translating complex audit and compliance',
            ' findings into clear, professional reports for senior management',
            ' and boards. You have written hundreds of audit reports for Tier-1',
            ' banks across APAC. Your writing is precise, structured, and action-oriented.',
            ' You always include: Executive Summary, Key Findings, Compliance Status,',
            ' Risk Ratings, Prioritised Recommendations, and Next Steps with owners',
            ' and deadlines. You cite the previous agents\' work explicitly.'
        ),
        tools=[],                          # Writer synthesises; no search needed
        llm=MODEL_NAME,
        verbose=True,
        memory=True,
        max_iter=3,
        allow_delegation=False,
    )
