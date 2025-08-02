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
usernames = {}  # websocket: username


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await websocket.accept()

    if room_id not in rooms:
        rooms[room_id] = set()

    if len(rooms[room_id]) >= 2:
        await websocket.send_text("ROOM_FULL")
        await websocket.close()
        return

    rooms[room_id].add(websocket)

    try:
        while True:
            data = await websocket.receive_text()

            # Lazy import to avoid JSON error on text check
            import json
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                continue

            if payload["type"] == "name":
                usernames[websocket] = payload["data"]

                # Inform the other peer of this user's name
                for conn in rooms[room_id]:
                    if conn != websocket:
                        await conn.send_text(json.dumps({
                            "type": "name",
                            "data": payload["data"]
                        }))

                # Also inform this websocket of the other user's name (if any)
                for conn in rooms[room_id]:
                    if conn != websocket and conn in usernames:
                        await websocket.send_text(json.dumps({
                            "type": "name",
                            "data": usernames[conn]
                        }))

            else:
                # Broadcast to other peer
                for conn in rooms[room_id]:
                    if conn != websocket:
                        await conn.send_text(data)

    except WebSocketDisconnect:
        rooms[room_id].remove(websocket)
        if websocket in usernames:
            del usernames[websocket]

        if not rooms[room_id]:
            del rooms[room_id]
        else:
            for conn in rooms[room_id]:
                await conn.send_text('{"type":"peer_left"}')
