from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from src.config import get_settings, get_embeddings
from src.security.presidio_service import presidio
import uuid


async def index_document(file_path: str, filename: str) -> int:
    settings = get_settings()
    loader = PyPDFLoader(file_path)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks = splitter.split_documents(docs)
    for chunk in chunks:
        chunk.metadata['source'] = filename
        # Mask PII in document chunks before storing
        chunk.page_content = presidio.anonymize(chunk.page_content)
    embeddings = get_embeddings()
    client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    try:
        client.get_collection(settings.qdrant_collection)
    except Exception:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
        )
    points = [PointStruct(
        id=str(uuid.uuid4()),
        vector=embeddings.embed_query(c.page_content),
        payload={'page_content': c.page_content, **c.metadata}
    ) for c in chunks]
    if points:
        client.upsert(collection_name=settings.qdrant_collection, points=points)
    return len(points)
