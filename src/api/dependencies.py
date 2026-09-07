"""Model loading dependency — sesuai Spec 03."""
from fastapi import HTTPException, Request


async def get_app_state(request: Request):
    """Dependency to ensure model is loaded."""
    if request.app.state.model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return request.app.state
