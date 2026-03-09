from pydantic import BaseModel, Field

chatbot_schema = {
    "type": "object",
    "properties": {
        "reply": {
            "type": "string",
            "description": "Reply must be between 5 and 100 words",
        }
    },
    "required": ["reply"],
}


class ConversationDeleteResponse(BaseModel):
    conversation_id: str
    message: str


class CreateConversationResponse(BaseModel):
    conversation_id: str
    message: str


class UseChatBotResponse(BaseModel):
    message: str
    reply: str


class ChatRequest(BaseModel):
    user_input: str


class Message(BaseModel):
    role: str
    content: str


class GuestChatRequest(BaseModel):
    message: str
    history: list[Message] = Field(default_factory=list)


class GuestUseChatBotResponse(BaseModel):
    message: str
    reply: str
