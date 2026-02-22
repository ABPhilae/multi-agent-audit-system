import streamlit as st
import requests
import json
import uuid

API_URL = 'http://api:8000'
st.title('🔍 Compliance Review')

# Session state
if 'thread_id' not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'pending_approval' not in st.session_state:
    st.session_state.pending_approval = False
if 'agent_steps' not in st.session_state:
    st.session_state.agent_steps = []
if 'last_report' not in st.session_state:
    st.session_state.last_report = ''

# Sidebar: review configuration
with st.sidebar:
    st.subheader('Review Parameters')
    scope = st.selectbox('Scope', ['APAC', 'Hong Kong', 'Singapore', 'Japan'])
    quarter = st.selectbox('Quarter', ['Q3 2025', 'Q4 2025', 'Q1 2026'])
    require_approval = st.checkbox('Require approval for critical findings', value=True)
    if st.button('New Session'):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.pending_approval = False
        st.session_state.agent_steps = []
        st.rerun()
    st.caption(f'Thread: {st.session_state.thread_id[:8]}...')

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg['role']):
        st.markdown(msg['content'])

# Human-in-the-loop approval UI
if st.session_state.pending_approval:
    st.warning('⚠️ CRITICAL FINDINGS — The agent is waiting for your approval')
    reviewer = st.text_input('Reviewer name', value='Chief Audit Executive')
    notes = st.text_area('Approval notes (optional)')
    col1, col2 = st.columns(2)
    with col1:
        if st.button('✅ Approve and Generate Report', type='primary'):
            resp = requests.post(f'{API_URL}/supervisor/approve', json={
                'thread_id': st.session_state.thread_id,
                'decision': 'approved',
                'reviewer': reviewer,
                'notes': notes
            })
            data = resp.json()
            report = data.get('report', 'Report approved and generated.')
            st.session_state.messages.append({'role': 'assistant', 'content': report})
            st.session_state.last_report = report
            st.session_state.pending_approval = False
            st.rerun()
    with col2:
        if st.button('❌ Reject', type='secondary'):
            requests.post(f'{API_URL}/supervisor/approve', json={
                'thread_id': st.session_state.thread_id,
                'decision': 'rejected', 'reviewer': reviewer, 'notes': notes
            })
            st.session_state.messages.append({'role': 'assistant', 'content': 'Report generation rejected.'})
            st.session_state.pending_approval = False
            st.rerun()

# Example prompts
st.caption('💡 Try: "What is finding HK-2024-001?" or "Perform a full compliance review for Q3 2025"')

# Chat input
if prompt := st.chat_input('Ask a question or submit a review task...'):
    st.session_state.messages.append({'role': 'user', 'content': prompt})
    with st.chat_message('user'):
        st.markdown(prompt)

    with st.chat_message('assistant'):
        status_ph = st.empty()
        report_ph = st.empty()
        steps_so_far, final_report, needs_approval = [], '', False

        with requests.post(f'{API_URL}/supervisor/stream', json={
            'task': prompt, 'scope': scope, 'quarter': quarter,
            'thread_id': st.session_state.thread_id,
            'require_approval': require_approval
        }, stream=True, timeout=600) as resp:  # 10min timeout for full crew
            for line in resp.iter_lines():
                if line and line.startswith(b'data: '):
                    data = json.loads(line[6:])
                    steps_so_far.extend(data.get('steps', []))
                    if steps_so_far:
                        status_ph.info('🤖 ' + ' → '.join(steps_so_far[-2:]))
                    if data.get('report'):
                        final_report = data['report']
                        report_ph.markdown(final_report)
                    if data.get('needs_approval'):
                        needs_approval = True

        st.session_state.agent_steps = steps_so_far
        if needs_approval:
            st.session_state.pending_approval = True
            st.session_state.messages.append({'role': 'assistant', 'content': '⏸️ Paused — awaiting human approval...'})
        elif final_report:
            st.session_state.last_report = final_report
            st.session_state.messages.append({'role': 'assistant', 'content': final_report})
        st.rerun()

# Download button for last report
if st.session_state.last_report:
    st.download_button(
        label='⬇️ Download Report as .txt',
        data=st.session_state.last_report,
        file_name=f'audit_report_{quarter.replace(" ", "_")}.txt',
        mime='text/plain'
    )
