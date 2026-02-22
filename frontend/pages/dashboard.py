import streamlit as st
import requests

API_URL = 'http://api:8000'
st.title('📊 System Dashboard')

# Health check
try:
    resp = requests.get(f'{API_URL}/health', timeout=5)
    health = resp.json()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric('System Status', '✅ Online')
    with col2:
        mode = health.get('model_mode', 'unknown')
        st.metric('Model Mode', '🏠 Local (Ollama)' if mode == 'local' else '☁️ Cloud (OpenAI)')
    with col3:
        gr = '✅ Active' if health.get('guardrails') else '⚠️ Disabled'
        st.metric('NeMo Guardrails', gr)
except:
    st.error('❌ Cannot connect to API. Is Docker running?')

st.markdown('---')
st.subheader('Recent Cost Summary')
try:
    resp = requests.get(f'{API_URL}/costs/summary', timeout=5)
    costs = resp.json()
    c1, c2 = st.columns(2)
    with c1:
        st.metric('Total Cost (session)', f'${costs.get("total_cost_usd", 0):.4f}')
    with c2:
        st.metric('Total Requests', costs.get('total_requests', 0))
    if costs.get('cost_by_agent'):
        st.bar_chart(costs['cost_by_agent'])
except:
    st.info('No cost data yet. Run a compliance review first.')

st.markdown('---')
st.subheader('Architecture Overview')
st.code("""
User → Streamlit → FastAPI
                      ├── LangGraph Supervisor
                      │       ├── Quick Question → RAG → Answer
                      │       └── Full Review → CrewAI Flow
                      │                  ├── Auditor Agent
                      │                  ├── Compliance Officer Agent
                      │                  ├── Risk Analyst Agent
                      │                  └── Report Writer Agent
                      ├── Presidio PII (every message)
                      ├── NeMo Guardrails (every LLM call)
                      └── Qdrant Vector DB (document search)
""", language='text')
