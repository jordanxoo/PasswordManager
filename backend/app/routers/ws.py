from fastapi import APIRouter,WebSocket,WebSocketDisconnect,Query,HTTPException
from jose import JWTError,jwt
from app.config import settings
from app.websocket_manager import manager


router = APIRouter()

def verify_ws_token(token:str) -> str:
    try:
        payload = jwt.decode(token,settings.JWT_SECRET,algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401)
        
        return user_id
    except JWTError:
        raise HTTPException(status_code=401,detail="Invalid token")
    


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...)
):
    try:
        user_id = verify_ws_token(token)

    except HTTPException:
        await websocket.close(code=1008)
        return
    
    await manager.connect(user_id,websocket)
    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(user_id,websocket)
