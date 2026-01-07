#note that this file is only run once every after changing the information
import faiss
from app.dependencies import embedding_model, documents_to_index

embedding_dim = embedding_model.get_sentence_embedding_dimension()

doc_embeddings = embedding_model.encode(
    documents_to_index,
    convert_to_numpy=True
).astype("float32")

index = faiss.IndexFlatL2(embedding_dim)
index.add(doc_embeddings)
faiss.write_index(index, "rag.faiss")