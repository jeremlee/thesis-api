from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

model_path = "all-mpnet-base-v2"

model = SentenceTransformer(model_path)

# Example usage
resume_text = "Python developer with machine learning experience"
job_text = "Machine learning engineer skilled in Python"

resume_emb = model.encode(resume_text, normalize_embeddings=True)
job_emb = model.encode(job_text, normalize_embeddings=True)

score = cosine_similarity([resume_emb], [job_emb])[0][0]
print(score)