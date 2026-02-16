import asyncio
from fastapi import APIRouter, HTTPException
import numpy as np
# import faiss
import json
import re

from app.dependencies import (
    chatbot_prompt,
    chatbot_gemini_model,
    embedding_model,
    # documents_to_index,
)
from app.executor import _executor
from app.services.supabase_service import get_supabase_admin_client
from app.response_schemas.chatbot_format import (
    ConversationMessage,
    ChatRequest,
    UseChatBotResponse,
    Message,
    GetConversationMessagesResponse,
)


FAISS_PATH = "D:/Documents/A_College/alliance thesis/ai_api/rag.faiss"
# index = faiss.read_index(FAISS_PATH)
router = APIRouter(prefix="/chatbot", tags=["Chatbot"])


def format_history(messages: list[ConversationMessage]) -> str:
    return "\n".join(f"{m.role.capitalize()}: {m.message}" for m in messages)

def format_guest_history(messages: list[Message]) -> str:
    return "\n".join(f"{m.role.capitalize()}: {m.content}" for m in messages)


def retrieve_context(query: str, k: int = 3) -> str:
    query_embedding = embedding_model.encode([query])
    query_embedding = np.array(query_embedding).astype("float32")

    # _, indices = index.search(query_embedding, k)

    # retrieved_docs = [documents_to_index[i] for i in indices[0] if i != -1]

    # return "\n".join(retrieved_docs)
    return ""


async def get_conversation_messages(
    conversation_id: str,
) -> GetConversationMessagesResponse:
    supabase_client = get_supabase_admin_client()
    resp = await asyncio.get_running_loop().run_in_executor(
        _executor,
        lambda: (
            supabase_client.table("conversation_messages")
            .select("id, role, message, created_at")
            .eq("conversation_id", conversation_id)
            .order("created_at")
            .execute()
        ),
    )

    if resp.data is None:
        raise HTTPException(status_code=500, detail="Supabase query failed")

    messages = [ConversationMessage.model_validate(row) for row in resp.data]

    return GetConversationMessagesResponse(
        conversation_id=conversation_id,
        messages=messages,
    )


@router.post("/use/{conversation_id}")
async def use_chatbot(conversation_id: str, request: ChatRequest) -> UseChatBotResponse:
    user_input = request.user_input
    supabase_client = get_supabase_admin_client()
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
        history = await get_conversation_messages(conversation_id)
        messages = history.messages

        last_5 = messages[-5:]

        history_text = format_history(last_5)

        prompt = (
            chatbot_prompt
            + "\n\nConversation so far:\n"
            + history_text
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

        resp_user = await asyncio.get_running_loop().run_in_executor(
            _executor,
            lambda: (
                supabase_client.table("conversation_messages")
                .insert(
                    {
                        "conversation_id": conversation_id,
                        "role": "user",
                        "message": user_input,
                    }
                )
                .execute()
            ),
        )

        if resp_user.data is None:
            raise HTTPException(status_code=500, detail="Insert failed")

        resp_assistant = await asyncio.get_running_loop().run_in_executor(
            _executor,
            lambda: (
                supabase_client.table("conversation_messages")
                .insert(
                    {
                        "conversation_id": conversation_id,
                        "role": "assistant",
                        "message": reply,
                    }
                )
                .execute()
            ),
        )

        if resp_assistant.data is None:
            raise HTTPException(status_code=500, detail="Insert failed")

        return UseChatBotResponse(
            message="Chatbot successfully replied",
            reply=reply,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
