from fastapi import WebSocket
from collections import defaultdict


class ConnectionManager:
    def __init__(self):
        self.connections: dict[str,list[WebSocket]] = defaultdict(list)

    
    async def connect(self,user_id:str, websocket: WebSocket):
        await websocket.accept()
        self.connections[user_id].append(websocket)

    def disconnect(self,user_id:str,websocket: WebSocket):
        self.connections[user_id].remove(websocket)
        if not self.connections[user_id]:
            del self.connections[user_id]

    async def send(self,user_id:str,message: dict):
        for ws in self.connections.get(user_id,[]):
            try:
                await ws.send_json(message)

            except Exception:
                pass


    async def disconnect_all(self):
        for user_id,sockets in list(self.connections.items()):
            for ws in sockets:
                try:
                    await ws.close(code=1001)

                except Exception:
                    pass


        self.connections.clear()


        
manager = ConnectionManager()