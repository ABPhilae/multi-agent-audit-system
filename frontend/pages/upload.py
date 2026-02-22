import streamlit as st
import requests

API_URL = 'http://api:8000'
st.title('📤 Upload Audit Documents')
st.markdown('Upload PDF or TXT audit documents. PII is automatically masked during indexing.')

files = st.file_uploader('Choose files', type=['pdf', 'txt'], accept_multiple_files=True)
if files and st.button('Upload and Index', type='primary'):
    for f in files:
        with st.spinner(f'Indexing {f.name}...'):
            ext = f.name.split('.')[-1]
            mime = 'application/pdf' if ext == 'pdf' else 'text/plain'
            resp = requests.post(
                f'{API_URL}/documents/upload',
                files={'file': (f.name, f.getvalue(), mime)}
            )
            if resp.status_code == 200:
                d = resp.json()
                st.success(f'✅ {f.name}: {d["chunks_indexed"]} chunks indexed (PII masked)')
            else:
                st.error(f'❌ {f.name}: {resp.text}')

st.info('📌 PII (names, phone numbers, emails) is automatically masked before storing.')
