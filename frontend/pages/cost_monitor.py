import streamlit as st
import requests
import pandas as pd

API_URL = 'http://api:8000'
st.title('💰 Cost Monitor')
st.markdown('Real-time token usage and cost breakdown by agent.')

col1, col2 = st.columns([3, 1])
with col2:
    if st.button('🔄 Refresh'):
        st.rerun()
    if st.button('🗑️ Reset Costs'):
        requests.delete(f'{API_URL}/costs/reset')
        st.rerun()

try:
    resp = requests.get(f'{API_URL}/costs/summary', timeout=5)
    data = resp.json()

    c1, c2, c3 = st.columns(3)
    c1.metric('Total Cost', f'${data["total_cost_usd"]:.4f} USD')
    c2.metric('Total Requests', data['total_requests'])
    c3.metric('Avg Cost/Request',
              f'${data["total_cost_usd"]/max(data["total_requests"],1):.4f}')

    st.markdown('---')

    if data.get('cost_by_agent'):
        st.subheader('Cost by Agent')
        df = pd.DataFrame(list(data['cost_by_agent'].items()),
                           columns=['Agent', 'Cost (USD)'])
        df = df.sort_values('Cost (USD)', ascending=False)
        st.bar_chart(df.set_index('Agent'))
        st.dataframe(df, use_container_width=True)

    if data.get('records'):
        st.subheader('Recent Requests')
        df_records = pd.DataFrame(data['records'])
        if not df_records.empty:
            cols = ['timestamp', 'agent_name', 'input_tokens', 'output_tokens', 'cost_usd']
            st.dataframe(df_records[[c for c in cols if c in df_records.columns]],
                         use_container_width=True)
except Exception as e:
    st.error(f'Cannot reach API: {e}')
