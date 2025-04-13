import hashlib
import json
from typing import Any, Dict
from datetime import datetime
import re
from urllib.parse import urlparse

def generate_session_id(user_id: str) -> str:
    """生成会话ID"""
    timestamp = datetime.now().isoformat()
    raw = f"{user_id}:{timestamp}"
    return hashlib.md5(raw.encode()).hexdigest()

def sanitize_text(text: str) -> str:
    """清理文本内容"""
    # 移除多余空白字符
    text = re.sub(r'\s+', ' ', text)
    # 移除特殊字符
    text = re.sub(r'[^\w\s\-.,?!]', '', text)
    return text.strip()

def validate_url(url: str) -> bool:
    """验证URL是否合法"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def truncate_text(text: str, max_length: int = 500) -> str:
    """截断文本"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def safe_json_dumps(obj: Any) -> str:
    """安全的JSON序列化"""
    def default(o):
        if isinstance(o, datetime):
            return o.isoformat()
        return str(o)
    return json.dumps(obj, ensure_ascii=False, default=default)

def merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """深度合并两个字典"""
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result 