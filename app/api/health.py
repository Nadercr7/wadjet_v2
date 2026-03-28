from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    return {"status": "ok", "version": "3.0.0-beta"}
