import streamlit as st

st.set_page_config(
    page_title='Multi-Agent Audit System',
    page_icon='🏛',
    layout='wide',
    initial_sidebar_state='expanded'
)

st.sidebar.title('🏛 Multi-Agent Audit')
st.sidebar.markdown('---')
st.sidebar.page_link('pages/dashboard.py',         label='📊 Dashboard')
st.sidebar.page_link('pages/compliance_review.py', label='🔍 Compliance Review')
st.sidebar.page_link('pages/agent_trace.py',       label='🤖 Agent Trace')
st.sidebar.page_link('pages/cost_monitor.py',      label='💰 Cost Monitor')
st.sidebar.page_link('pages/upload.py',            label='📤 Upload Documents')
st.sidebar.page_link('pages/evaluation.py',        label='📈 RAG Evaluation')
st.sidebar.markdown('---')
st.sidebar.caption('Phase 4 Project 2 | LangGraph + CrewAI')

st.title('Multi-Agent Audit Compliance System')
st.markdown("""
A production-grade multi-agent AI system for APAC audit compliance reviews.

**How it works:**
- **Compliance Review**: Submit a review task → the Supervisor delegates to 4 specialists
- **Agent Trace**: See each agent's reasoning step by step
- **Cost Monitor**: Track per-agent token usage and cost in real time
- **Evaluation**: View RAGAS quality scores from the latest CI/CD run
""")
