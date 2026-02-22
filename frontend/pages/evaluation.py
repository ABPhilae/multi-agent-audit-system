import streamlit as st
import requests

EVAL_URL = 'http://evaluation:8001'
st.title('📈 RAG Evaluation (RAGAS)')
st.markdown('Run the RAGAS evaluation suite to measure retrieval and answer quality.')

if st.button('▶️ Run Evaluation Now', type='primary'):
    with st.spinner('Running RAGAS evaluation on 20 test questions... (~5 minutes)'):
        try:
            resp = requests.post(f'{EVAL_URL}/evaluate', timeout=600)
            result = resp.json()
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric('Faithfulness',      f'{result.get("faithfulness",0):.3f}')
            c2.metric('Answer Relevancy',  f'{result.get("answer_relevancy",0):.3f}')
            c3.metric('Context Precision', f'{result.get("context_precision",0):.3f}')
            c4.metric('Context Recall',    f'{result.get("context_recall",0):.3f}')
            c5.metric('Overall Score',     f'{result.get("overall_score",0):.3f}')
            if result.get('passed_quality_gate'):
                st.success('✅ Quality gate PASSED (score >= 0.7)')
            else:
                st.error('❌ Quality gate FAILED (score < 0.7) — investigate retrieval')
            st.markdown(f'Questions evaluated: {result.get("questions_evaluated", 0)}')
        except Exception as e:
            st.error(f'Evaluation service unavailable: {e}')

st.info('The evaluation suite runs automatically on every GitHub push via CI/CD.')
