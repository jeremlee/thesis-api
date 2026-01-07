import asyncio
from fastapi import APIRouter, HTTPException
from typing import Any
import numpy as np
import faiss
import json
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from app.dependencies import (
    get_gemma_pipe,
    GEMMA_SEMAPHORE,
    chatbot_prompt,
    embedding_model,
    documents_to_index,
    extract_json_text,
)
from app.executor import _executor



class ChatRequest(BaseModel):
    user_input: str
FAISS_PATH = "D:/Documents/A_College/alliance thesis/ai_api/rag.faiss"
index = faiss.read_index(FAISS_PATH)
router = APIRouter(prefix="/chatbot", tags=["Chatbot"])




def retrieve_context(query: str, k: int = 3) -> str:
    query_embedding = embedding_model.encode([query])
    query_embedding = np.array(query_embedding).astype("float32")

    distances, indices = index.search(query_embedding, k)

    retrieved_docs = [
        documents_to_index[i] for i in indices[0] if i != -1
    ]

    return "\n".join(retrieved_docs)

@router.post("/")
async def use_chatbot(request: ChatRequest):
    user_input = request.user_input
    try:
      
        context = retrieve_context(user_input, k=3)[:1500]
        prompt = chatbot_prompt.format(context=context, question=user_input)
        gemma_pipe = await get_gemma_pipe()
        async with GEMMA_SEMAPHORE:
            loop = asyncio.get_running_loop()
            raw_output = await loop.run_in_executor(
                _executor,
                lambda: gemma_pipe(
                    prompt,
                    max_new_tokens=900,
                    return_full_text=True
                )
            )
        print(raw_output)

        return {
            "message": "Chatbot executed successfully",
            "rag_context": context,
            "gemma_output": raw_output
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))