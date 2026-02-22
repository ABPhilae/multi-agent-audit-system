import streamlit as st

st.title('🤖 Agent Execution Trace')
st.markdown('See exactly what each agent did — step by step.')

if 'agent_steps' not in st.session_state or not st.session_state.agent_steps:
    st.info('No trace available yet. Run a Compliance Review first.')
else:
    steps = st.session_state.agent_steps
    st.markdown(f'### {len(steps)} steps executed')

    # Agent colour coding
    agent_colors = {
        'Auditor': '🔵',
        'Compliance': '🟢',
        'Risk': '🟠',
        'Report': '🟣',
        'Supervisor': '🔴',
        'classify': '⚪',
        'quick': '⚪',
    }

    for i, step in enumerate(steps, 1):
        # Match step to agent
        icon = '⚪'
        for key, emoji in agent_colors.items():
            if key.lower() in step.lower():
                icon = emoji
                break
        st.markdown(f'**{i}.** {icon} {step}')

    if st.session_state.get('pending_approval'):
        st.warning('⏸️ Supervisor paused — waiting for human approval')
