"""
WebSocket endpoint — real-time push to frontend clients.
Subscribes to Redis pub/sub channels per tenant.
Celery workers publish events; this handler fans them out to connected browsers.
"""
import json
import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active: Dict[str, List[WebSocket]] = {}

    async def connect(self, ws: WebSocket, tenant_id: str):
        await ws.accept()
        self.active.setdefault(tenant_id, []).append(ws)
        logger.info(f"WS connected: tenant={tenant_id}, total={len(self.active[tenant_id])}")

    def disconnect(self, ws: WebSocket, tenant_id: str):
        if tenant_id in self.active:
            self.active[tenant_id] = [w for w in self.active[tenant_id] if w != ws]

    async def broadcast(self, tenant_id: str, message: dict):
        dead = []
        for ws in self.active.get(tenant_id, []):
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, tenant_id)


manager = ConnectionManager()


async def _redis_listener(tenant_id: str):
    """
    Background task: subscribe to Redis channel ws:{tenant_id}
    and broadcast messages to all connected WebSocket clients.
    """
    import redis.asyncio as aioredis
    from app.core.config import settings

    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        pubsub = r.pubsub()
        await pubsub.subscribe(f"ws:{tenant_id}")

        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    await manager.broadcast(tenant_id, data)
                except json.JSONDecodeError:
                    pass

                # Stop if no clients remain
                if not manager.active.get(tenant_id):
                    break

        await pubsub.unsubscribe(f"ws:{tenant_id}")
        await r.close()

    except Exception as e:
        logger.error(f"Redis listener error (tenant={tenant_id}): {e}")


@router.websocket("/ws/{tenant_id}")
async def websocket_endpoint(websocket: WebSocket, tenant_id: str):
    """
    Real-time event stream for a tenant's dashboard.
    Events: job_progress | job_complete | new_review | new_alert | dashboard_update
    """
    await manager.connect(websocket, tenant_id)

    # Start Redis listener if this is the first client for this tenant
    is_first = len(manager.active.get(tenant_id, [])) == 1
    listener_task = None
    if is_first:
        listener_task = asyncio.create_task(_redis_listener(tenant_id))

    try:
        await websocket.send_text(json.dumps({
            "event": "connected",
            "tenant_id": tenant_id,
            "message": "Real-time updates active",
        }))

        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"event": "pong"}))

    except WebSocketDisconnect:
        manager.disconnect(websocket, tenant_id)
        logger.info(f"WS disconnected: tenant={tenant_id}")
    finally:
        if listener_task and not manager.active.get(tenant_id):
            listener_task.cancel()
