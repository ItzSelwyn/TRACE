from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["ws"])

@router.websocket("/ws/live-updates")
async def live_updates_ws(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"type": "connected", "message": "TRACE live updates"})
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        pass
