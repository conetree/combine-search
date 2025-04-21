from fastapi import APIRouter

router = APIRouter()

@router.get("/hello")
async def read_root():
    return {"message": "Hello World"} 