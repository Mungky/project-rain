"""WebSocket API endpoints for Agent Runs."""

import asyncio
import json
import logging
from uuid import UUID
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from pydantic import BaseModel, Field
from datetime import datetime, UTC

from rain_backend.api.deps import get_db, get_db_engine, get_providers
from db.schemas.agent_run import AgentRun, AgentRunStatus
from db.schemas.user import User

logger = logging.getLogger(__name__)
router = APIRouter(tags=["agent_runs"])

DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


class CreateRunRequest(BaseModel):
    goal: str = Field(..., max_length=5000)
    title: str = Field(..., max_length=200)


class RunResponse(BaseModel):
    id: UUID
    title: str
    goal: str
    status: str
    created_at: datetime


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[UUID, list[WebSocket]] = {}

    async def connect(self, run_id: UUID, websocket: WebSocket):
        await websocket.accept()
        if run_id not in self.active_connections:
            self.active_connections[run_id] = []
        self.active_connections[run_id].append(websocket)

    def disconnect(self, run_id: UUID, websocket: WebSocket):
        if run_id in self.active_connections:
            self.active_connections[run_id].remove(websocket)
            if not self.active_connections[run_id]:
                del self.active_connections[run_id]

    async def broadcast(self, run_id: UUID, message: dict):
        if run_id in self.active_connections:
            for connection in self.active_connections[run_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {run_id}: {e}")

manager = ConnectionManager()


async def _run_orchestrator_bg(run_id: UUID, db_engine: AsyncEngine, providers: dict):
    """Background task to run the orchestrator."""
    from rain_brain.orchestrator.work_mode import WorkModeOrchestrator
    from sqlalchemy.ext.asyncio import AsyncSession
    
    async with AsyncSession(db_engine) as session:
        orchestrator = WorkModeOrchestrator(session, providers)
        # We start the run and consume its generator just to execute it
        async for _ in orchestrator.start_run(run_id):
            pass


@router.post("/v1/agent-runs", response_model=RunResponse)
async def create_agent_run(
    request: CreateRunRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    db_engine: AsyncEngine = Depends(get_db_engine),
    providers: dict = Depends(get_providers),
):
    """Create a new autonomous Agent Run and start it in the background."""
    run = AgentRun(
        user_id=DEFAULT_USER_ID,
        title=request.title,
        goal=request.goal,
        status=AgentRunStatus.pending,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # Fire background task
    background_tasks.add_task(_run_orchestrator_bg, run.id, db_engine, providers)

    return RunResponse(
        id=run.id,
        title=run.title,
        goal=run.goal,
        status=run.status,
        created_at=run.created_at,
    )


@router.websocket("/ws/v1/agent-runs/{run_id}")
async def websocket_agent_run(websocket: WebSocket, run_id: UUID, db: AsyncSession = Depends(get_db)):
    """WebSocket endpoint for real-time updates of an Agent Run."""
    await manager.connect(run_id, websocket)
    
    try:
        # Acknowledge connection
        await websocket.send_json({"type": "connected", "run_id": str(run_id)})
        
        while True:
            # We can receive messages from the client if needed (e.g. abort signals)
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                if payload.get("action") == "abort":
                    logger.info(f"Received abort signal for run {run_id}")
                    # Handle abort logic
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        manager.disconnect(run_id, websocket)
        logger.info(f"WebSocket disconnected for run {run_id}")

