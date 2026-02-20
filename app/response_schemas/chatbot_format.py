from pydantic import BaseModel
from datetime import datetime
chatbot_schema = {
    "type": "object",
    "properties": {
        "reply": {
            "type": "string",
            "description": "Reply must be between 5 and 100 words"
        }
    },
    "required": ["reply"],
}

class ConversationMessage(BaseModel):
    id: str
    role: str
    message: str
    created_at: datetime

class ConversationDeleteResponse(BaseModel):
    conversation_id: str
    message: str

class CreateConversationResponse(BaseModel):
    conversation_id: str
    message: str

class UseChatBotResponse(BaseModel):
    message: str
    reply: str

class GetConversationMessagesResponse(BaseModel):
    conversation_id: str
    messages: list[dict]

class ChatRequest(BaseModel):
    user_input: str