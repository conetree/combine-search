from typing import Any, Dict
from http import HTTPStatus


def response_success(message: str = "成功", data: Any = None) -> Dict[str, Any]:
    return {
        "code": 200,
        "message": message,
        "data": data,
    }

def response_error(code: int = HTTPStatus.INTERNAL_SERVER_ERROR, message: str = "失败", data: Any = None) -> Dict[str, Any]:
    error_code = 501 if code > 500 else 500
    return {
        "code": error_code,
        "message": message,
        "data": data,
    }