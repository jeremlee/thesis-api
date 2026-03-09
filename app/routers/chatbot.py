import asyncio

import json
import re

from fastapi import APIRouter, HTTPException

from app.dependencies import (
    chatbot_gemini_model,
    chatbot_prompt,
)
from app.response_schemas.chatbot_format import (
    ChatRequest,
    Message,
    UseChatBotResponse,
)
from app.services.supabase_service import get_supabase_admin_client
from entities.fastapi.schema_public_latest import PublicConversationMessages

FAISS_PATH = "D:/Documents/A_College/alliance thesis/ai_api/rag.faiss"
router = APIRouter(prefix="/chatbot", tags=["Chatbot"])


def format_history(messages: list[PublicConversationMessages]) -> str:
    return "\n".join(f"{m.role.capitalize()}: {m.message}" for m in messages)


def format_guest_history(messages: list[Message]) -> str:
    return "\n".join(f"{m.role.capitalize()}: {m.content}" for m in messages)


async def get_conversation_messages(
    conversation_id: str,
) -> list[PublicConversationMessages]:
    return [
        PublicConversationMessages.model_validate(message)
        for message in await asyncio.to_thread(
            lambda: (
                get_supabase_admin_client()
                .table("conversation_messages")
                .select("id, role, message, created_at")
                .eq("conversation_id", conversation_id)
                .order("created_at")
                .limit(5)
                .execute()
                .data
            ),
        )
    ]


@router.post("/use/{conversation_id}")
async def use_chatbot(conversation_id: str, request: ChatRequest) -> UseChatBotResponse:
    user_input: str = request.user_input
    supabase_client = get_supabase_admin_client()
    try:
        prompt = (
            chatbot_prompt
            + "\n\nConversation so far:\n"
            + format_history(await get_conversation_messages(conversation_id))
            + "\n\nUser:\n"
            + user_input
        )

        raw_output: str = await asyncio.to_thread(
            lambda: chatbot_gemini_model.generate_content(prompt).text or "",
        )

        raw_output = raw_output.strip()

        if raw_output.startswith("```"):
            raw_output = re.sub(r"```json|```", "", raw_output).strip()

        try:
            reply = json.loads(raw_output).get("reply", "")
        except json.JSONDecodeError:
            reply = raw_output

        if not [
            PublicConversationMessages.model_validate(message)
            for message in await asyncio.to_thread(
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
                    .data
                ),
            )
        ]:
            raise HTTPException(status_code=500, detail="Insert failed")

        resp_assistant: list[PublicConversationMessages] = [
            PublicConversationMessages.model_validate(message)
            for message in await asyncio.to_thread(
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
        ]

        if not resp_assistant:
            raise HTTPException(
                status_code=500, detail="Insertion to database of assistant failed"
            )

        return UseChatBotResponse(
            message="Chatbot successfully replied",
            reply=reply,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
