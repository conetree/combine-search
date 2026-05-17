from __future__ import annotations

import json
from typing import ClassVar, Dict, Optional

from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate

from app.core.config import settings
from app.core.logging import logger
from app.services.llm import InternalLLM, OpenAICompatibleLLM


class ConversationManager:
    """会话管理：内部网关或 OpenAI 兼容 API。"""

    _sessions: ClassVar[Dict[str, "ConversationManager"]] = {}

    def __init__(self, session_id: str):
        self.session_id = session_id
        if settings.INTERNAL_AI_API_URL and settings.INTERNAL_AI_API_URL.strip():
            self.llm = InternalLLM(session_id=session_id)
        else:
            self.llm = OpenAICompatibleLLM(provider=settings.LLM_DEFAULT_PROVIDER)

        custom_prompt = PromptTemplate(
            input_variables=["chat_history", "input"],
            template='{{"chat_history":"{chat_history}","input":{input}}}',
        )
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            max_token_limit=settings.MAX_CONTEXT_LENGTH,
        )
        self.chain = ConversationChain(
            llm=self.llm,
            memory=self.memory,
            prompt=custom_prompt,
            verbose=False,
        )
        ConversationManager._sessions[session_id] = self

    async def get_response(
        self, user_input: Dict[str, str], context: Optional[Dict] = None
    ) -> str:
        try:
            response = await self.chain.arun(input=json.dumps(user_input))
            return response
        except Exception as e:
            logger.error(f"Error in get_response: {str(e)}")
            raise e

    def clear_context(self) -> None:
        self.memory.clear()

    @classmethod
    def clear_session(cls, session_id: str) -> None:
        inst = cls._sessions.pop(session_id, None)
        if inst is not None:
            inst.memory.clear()
