from fastapi import FastAPI
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from datasets import Dataset
import json
import os

app = FastAPI(title='RAGAS Evaluation Service')

QDRANT_HOST = os.getenv('QDRANT_HOST', 'qdrant')
QDRANT_PORT = int(os.getenv('QDRANT_PORT', 6333))
COLLECTION = os.getenv('QDRANT_COLLECTION', 'audit_documents')
OPENAI_KEY = os.getenv('OPENAI_API_KEY', '')


@app.get('/health')
def health():
    return {'status': 'ok', 'service': 'ragas-evaluation'}


@app.post('/evaluate')
async def run_evaluation():
    with open('/app/test_questions.json') as f:
        test_data = json.load(f)
    questions = test_data['questions']

    embeddings = OpenAIEmbeddings(model='text-embedding-3-small', openai_api_key=OPENAI_KEY)
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    try:
        store = QdrantVectorStore(
            client=client, collection_name=COLLECTION, embedding=embeddings
        )
        retriever = store.as_retriever(search_kwargs={'k': 5})
    except Exception as e:
        return {'error': f'Qdrant unavailable: {e}', 'overall_score': 0.0, 'passed_quality_gate': False}

    llm = ChatOpenAI(model='gpt-4o-mini', openai_api_key=OPENAI_KEY)

    # Build RAGAS dataset
    data = {'question': [], 'answer': [], 'contexts': [], 'ground_truth': []}
    for item in questions:
        q = item['question']
        docs = retriever.invoke(q)
        contexts = [d.page_content for d in docs]
        prompt = f'Answer based on context only.\nContext: {chr(10).join(contexts[:3])}\nQuestion: {q}'
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=prompt)])
        data['question'].append(q)
        data['answer'].append(response.content)
        data['contexts'].append(contexts)
        data['ground_truth'].append(item['ground_truth'])

    dataset = Dataset.from_dict(data)
    result = evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=llm,
        embeddings=embeddings,
    )
    scores = result.to_pandas().mean().to_dict()
    overall = sum(scores.values()) / len(scores) if scores else 0.0
    return {
        'faithfulness': round(scores.get('faithfulness', 0), 4),
        'answer_relevancy': round(scores.get('answer_relevancy', 0), 4),
        'context_precision': round(scores.get('context_precision', 0), 4),
        'context_recall': round(scores.get('context_recall', 0), 4),
        'overall_score': round(overall, 4),
        'questions_evaluated': len(questions),
        'passed_quality_gate': overall >= 0.7,
    }
