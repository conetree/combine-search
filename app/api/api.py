from fastapi import APIRouter, Depends, UploadFile, File, Form, Request
from typing import List, Optional
from app.services.conversation import ConversationManager
from app.services.scraper import WebScraper
from uuid import uuid4
from app.core.logging import logger
from pydantic import BaseModel, Field
import json
import pandas as pd
import os
from docx import Document
import pdfplumber
import aiofiles
import time
from pathlib import Path
import mimetypes

# ====================
# 子模型定义
# ====================
class PromptItemModel(BaseModel):
    answer: Optional[str] = Field(None, description="答案")
    question: Optional[str] = Field(None, description="问题")

class ExtraInfoModel(BaseModel):
    type: Optional[int] = Field(None, description="额外信息类型，例如1为URL抓取")
    value: Optional[str] = Field(None, description="额外信息的值")

# ====================
# 参数模型定义
# ====================
class ChatParamModel(BaseModel):
    input: Optional[str] = None
    name: str = Field(default='', min_length=0, max_length=50)
    channel: str = Field(default='', min_length=0, max_length=50)
    channelName: Optional[str] = Field(None, max_length=100)
    promptList: List[PromptItemModel] = Field(default_factory=list)
    conversationTitle: Optional[str] = Field(None, max_length=200)
    hasScraper: Optional[bool] = False
    extraInfo: List[ExtraInfoModel] = Field(default_factory=list)

# ====================
# 路由配置
# ====================
router = api_router = APIRouter()

# ====================
# 工具函数生成sessionid
# ====================
def get_session_id() -> str:
    """生成唯一会话ID"""
    return str(uuid4())

async def validate_file_type(filename: str) -> str:
    """验证并返回安全的文件类型"""
    allowed_types = {
        'text/plain': 'txt',
        'application/pdf': 'pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        'application/vnd.ms-excel': 'xls',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx'
    }
    
    file_type, _ = mimetypes.guess_type(filename)
    return allowed_types.get(file_type, 'unsupported')

async def process_file(file_path: Path, file_type: str) -> str:
    """统一文件处理函数"""
    try:
        if not file_path.exists():
            return ""
        
        if file_type == 'xlsx':
            df = pd.read_excel(file_path)
            return df.to_csv(index=False)
            
        elif file_type == 'docx':
            doc = Document(file_path)
            return "\n".join(para.text for para in doc.paragraphs if para.text)
            
        elif file_type == 'txt':
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                return await f.read()
                
        elif file_type == 'pdf':
            with pdfplumber.open(file_path) as pdf:
                texts = [page.extract_text() for page in pdf.pages if page.extract_text]
                return "\n".join(filter(None, texts))
                
        return ""
    except Exception as e:
        logger.error(f"File processing error: {str(e)}", exc_info=True)
        return ""
    
async def handle_uploaded_file(file: UploadFile) -> str:
    """封装文件处理流程：类型验证、保存、解析、清理"""
    # 类型验证（由 validate_file_type 负责）
    file_type = await validate_file_type(file.filename)
    if file_type == 'unsupported':
        raise ValueError(f"Unsupported file type: {file.filename}")

    # 创建上传目录并生成安全文件名
    upload_dir = Path("./uploads")
    upload_dir.mkdir(exist_ok=True, parents=True)
    safe_name = f"{uuid4().hex}.{file_type}"
    file_path = upload_dir / safe_name
    logger.info("handle_uploaded_file->file_path: %s", file_path)

    # 异步保存文件
    async with aiofiles.open(file_path, "wb") as out_file:
        await out_file.write(await file.read())

    # 处理文件内容
    content = await process_file(file_path, file_type)

    # 删除临时文件
    try:
        file_path.unlink()
    except Exception as e:
        logger.error(f"File deletion error: {e}")

    return content

# ====================
# API 路由
# ====================
@router.post("/chat")
async def chat_post(
    request: Request,
    params: str = Form(...),
    file: Optional[UploadFile] = File(None),
    session_id: str = Depends(get_session_id)
):
    """大模型对话接口（POST）"""
    try:
        start_time = time.time()
        knowledge = ""
        logger.info(f"params: , {params}")
        params_dict = json.loads(params)
        logger.info(f"params_dict: , {params_dict}")
        chat_params = ChatParamModel(**params_dict)
        logger.info(f"chat_params: , {chat_params}")
        
        logger.info(
            f"Chat request received - Session: {session_id}",
            extra={
                "params": params_dict,
                "has_file": file is not None
            }
        )
        
        # 由 handle_uploaded_file 统一处理上传
        if file and file.filename:
            try:
                knowledge = await handle_uploaded_file(file)
            except ValueError:
                return {"response": "不支持的文件类型", "session_id": session_id, "code": 500}

        # 网页抓取处理
        web_scraper = WebScraper()
        
        # ExtraInfo 处理
        if chat_params.extraInfo:
            try:
                extra_info = chat_params.extraInfo[0]
                if extra_info.type == 1 and extra_info.value:
                    scraped_content = await web_scraper.scrape_web_url(
                        url=extra_info.value,
                        headers=dict(request.headers)
                    )
                    knowledge += f"\n{scraped_content or ''}"
            except Exception as e:
                logger.error(f"ExtraInfo processing error: {str(e)}")

        # 智能搜索处理
        if not chat_params.promptList and not chat_params.hasScraper and chat_params.conversationTitle:
            try:
                channel_name = chat_params.channelName or ""
                conv_title = chat_params.conversationTitle or ""
                query = f"{conv_title} {channel_name} 豆瓣 百科"
                
                logger.debug(f"Search query: {query}")
                # spider_content = await web_scraper.baidu_search_web(query = query, links_num=3, headers = dict(request.headers))  
                logger.info(f"API /chat before bing_search_web cost: {time.time() - start_time}")
                spider_content = await web_scraper.bing_search_web(
                    query=query,
                    links_num=2,
                    headers=dict(request.headers)
                )
                logger.info(f"API /chat after bing_search_web cost: {time.time() - start_time}")
                
                knowledge = f"{spider_content or ''}\n{knowledge}"
            except Exception as e:
                logger.error(f"Search processing error: {str(e)}")

        # 构建最终输入
        final_input = chat_params.input or ""
        if knowledge:
            final_input = f"***{knowledge}***{final_input}"

        # 对话处理
        conversation_manager = ConversationManager(session_id=session_id)
        response = await conversation_manager.get_response({
            **chat_params.model_dump(),
            "input": final_input
        })

        logger.info(
            f"Request processed - Duration: {time.time() - start_time:.2f}s",
            extra={"session_id": session_id}
        )

        return {
            "response": response,
            "session_id": session_id,
            "code": 200
        }

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        return {
            "response": "参数格式错误",
            "session_id": session_id,
            "code": 500
        }
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return {
            "response": "服务器内部错误",
            "session_id": session_id,
            "code": 502
        }

@router.get("/chat")
async def chat_get(
    message: str,
    name: str,
    channel: str,
    session_id: str = Depends(get_session_id)
):
    """聊天接口（GET）"""
    try:
        conversation_manager = ConversationManager(session_id=session_id)
        
        input_data = {
            "input": message,
            "name": name,
            "channel": channel
        }
        
        response = await conversation_manager.get_response(input_data)
        
        return {
            "response": response,
            "session_id": session_id,
            "code": 200
        }
        
    except Exception as e:
        logger.error(f"GET chat error: {str(e)}")
        return {
            "response": "服务器内部错误",
            "session_id": session_id,
            "code": 502
        }

@router.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}

@router.post("/clear-context")
async def clear_context(session_id: str = Depends(get_session_id)):
    """清除对话上下文"""
    try:
        # 假设 ConversationManager 有清除上下文的实现
        ConversationManager.clear_session(session_id)
        return {"code": 200}
    except Exception as e:
        logger.error(f"Clear context error: {str(e)}")
        return {"code": 500}

