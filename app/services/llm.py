from typing import List, Dict, Any
from langchain.llms.base import LLM
from langchain.callbacks.manager import CallbackManagerForLLMRun
from app.core.config import settings
from app.core.logging import logger
import requests
import json
from pydantic import PrivateAttr


class InternalLLM(LLM):
    """封装大模型API"""

    # 使用 PrivateAttr 来存储非 pydantic 字段
    _session_id: str = PrivateAttr()

    def __init__(self, session_id: str = None, **kwargs):
        super().__init__(**kwargs)
        self._session_id = session_id or "default_session"

    @property
    def _llm_type(self) -> str:
        return "internal_llm"

    def _call(
        self,
        prompt: str,
        stop: List[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> str:
        """调用内部AI接口"""
        headers = {
            # "Authorization": f"Bearer {settings.INTERNAL_AI_API_KEY}",
            "Content-Type": "application/json"
        }

        # logger.info(f"Request InternalLLM - prompt: {prompt}")
        promptObj = json.loads(prompt)["input"]

        # logger.info(f"Request InternalLLM - promptList: {promptObj["promptList"]}")

        data = {
            "service_name": "lego-catalog-generate",
            "prompt_id": "111828549",
            "prompt_version": "latest",
            "prompt_token": "f6286f9cf4701544c59847e68e0f6c59",
            # "prompt_variable": promptObj["variable"],
            "prompt_list": promptObj["promptList"],
            "job_id": self._session_id,
            "response_mode": 1,
            "prompt_variable": json.dumps({
                "input": promptObj["input"]
            })
            # "workflow_inputs": {"input": promptObj["input"]} # 使用实际的prompt
        }

        # logger.info(f"Request InternalLLM - data: {json.dumps(data)}")

        response = requests.post(
            settings.INTERNAL_AI_API_URL +
            '/prompt/api/completions?job_id={self._session_id}',
            headers=headers,
            json=data
        )

        # logger.info(f"Request InternalLLM - response: {response.text}")

        if response.status_code != 200:
            raise Exception(f"AI API调用失败: {response.text}")

        return response.json().get("data", [""])[0]

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """返回模型标识参数"""
        return {
            "model_name": "internal_llm",
            "api_url": settings.INTERNAL_AI_API_URL + '/prompt/api/completions?job_id=lagoaicatalog'
        }
