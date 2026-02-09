import asyncio
from fastapi import APIRouter, HTTPException
from typing import Any
import numpy as np
import faiss
import json
import re
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from app.dependencies import (
    get_gemma_pipe,
    GEMMA_SEMAPHORE,
    chatbot_prompt,
    chatbot_gemini_model,
    embedding_model,
    documents_to_index,
    extract_json_text,
)
from app.executor import _executor
import supabase



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



def get_last_messages(conversation_id: str, limit: int = 5) -> str:
    resp = (
        supabase
        .table("conversation_messages")
        .select("message")
        .eq("conversation_id", conversation_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    if resp.error:
        return ""
    messages = [row["message"] for row in reversed(resp.data)]

    return "\n".join(messages)

    

@router.post("/{conversation_id}")
async def use_chatbot(conversation_id: str, request: ChatRequest):
    user_input = request.user_input

    try:

        # context = retrieve_context(user_input, k=3)[:1500]
        # prompt = chatbot_prompt.format(context=context, question=user_input)
        # gemma_pipe = await get_gemma_pipe()
        # async with GEMMA_SEMAPHORE:
        #     loop = asyncio.get_running_loop()
        #     raw_output = await loop.run_in_executor(
        #         _executor,
        #         lambda: gemma_pipe(
        #             prompt,
        #             max_new_tokens=900,
        #             return_full_text=True
        #         )
        #     )
        # print(raw_output)

        # return {
        #     "message": "Chatbot executed successfully",
        #     "rag_context": context,
        #     "gemma_output": raw_output
        # }
       
       
        history = get_last_messages(conversation_id)

        prompt = (
            chatbot_prompt
            + "\n\nConversation so far:\n"
            + history
            + "\n\nUser:\n"
            + user_input
        )

        raw_output = await asyncio.get_running_loop().run_in_executor(
            _executor,
            lambda: chatbot_gemini_model.generate_content(prompt).text or "",
        )

        raw_output = raw_output.strip()

        if raw_output.startswith("```"):
            raw_output = re.sub(r"```json|```", "", raw_output).strip()

        try:
            parsed = json.loads(raw_output)
            reply = parsed.get("reply", "")
        except json.JSONDecodeError:
            reply = raw_output

        supabase.rpc(
            "add_message_and_keep_5",
            {"p_conversation_id": conversation_id, "p_message": f"User: {user_input}"},
        ).execute()

        supabase.rpc(
            "add_message_and_keep_5",
            {"p_conversation_id": conversation_id, "p_message": f"Assistant: {reply}"},
        ).execute()

        return {
            "message": "Chatbot successfully replied",
            "reply": reply,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))