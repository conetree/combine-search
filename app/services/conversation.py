from typing import List, Dict, Optional
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from app.services.llm import InternalLLM
from app.core.config import settings
from app.core.logging import logger
from langchain.prompts import PromptTemplate
import json

class ConversationManager:
    def __init__(self, session_id: str):
        """
        初始化会话管理器
        :param session_id: 会话ID，用于区分不同用户
        """
        self.session_id = session_id
        self.llm = InternalLLM(session_id=session_id)
        custom_prompt = PromptTemplate(
            input_variables=["chat_history", "input"],  # 兼容 chat_history
            template='{{"chat_history":"{chat_history}","input":{input}}}'
            # template='{json.dumps({"chat_history":chat_history,"input":input})}'
        )
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            max_token_limit=settings.MAX_CONTEXT_LENGTH
        )
        self.chain = ConversationChain(
            llm=self.llm,
            memory=self.memory,
            prompt=custom_prompt,  # 传入自定义 prompt
            verbose=False # 是否启用详细的日志输出功能
        )
    
    async def get_response(self, user_input: Dict[str, str], context: Optional[Dict] = None) -> Dict[str, str]:
        """
        处理用户输入并返回响应
        :param user_input: 用户输入
        :param context: 额外上下文信息
        :return: 包含响应和会话历史的字典
        """
        try:
            # logger.info(f"Request get_response start - user_input: {json.dumps(user_input)}")
            # 使用 InternalLLM 处理用户输入
            response = await self.chain.arun(input=json.dumps(user_input))
            # logger.info(f"Request get_response end - response: {response}")
            return response
        except Exception as e:
            logger.error(f"Error in get_response: {str(e)}")
            raise e
    
    def clear_context(self):
        """清除对话上下文"""
        self.memory.clear() 