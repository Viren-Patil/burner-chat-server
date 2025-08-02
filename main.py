from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow React frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rooms = {}  # room_id: set of WebSocket connections

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await websocket.accept()

    if room_id not in rooms:
        rooms[room_id] = set()

    # Reject if room already has 2 users
    if len(rooms[room_id]) >= 2:
        await websocket.send_text("ROOM_FULL")
        await websocket.close()
        return

    rooms[room_id].add(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            for conn in rooms[room_id]:
                if conn != websocket:
                    await conn.send_text(data)
    except WebSocketDisconnect:
        rooms[room_id].remove(websocket)
        if not rooms[room_id]:
            del rooms[room_id]

