"""Multi-Agent Orchestrator for Phase 3 (Work Mode)."""

import logging
import json
import asyncio
from typing import AsyncGenerator
from uuid import UUID
from datetime import datetime, UTC
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.schemas.agent_run import AgentRun, AgentRunStatus
from db.schemas.agent_task import AgentTask, TaskStatus
from rain_brain.providers.base import ChatRequest
from rain_brain.orchestrator.prompt_templates import get_temperature

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """You are a Planner Agent in Project Rain's multi-agent system.
Your job: break down a user's goal into actionable, ordered steps.

Output ONLY valid JSON. No markdown.

{
  "steps": [
    {
      "label": "short label",
      "description": "what to do",
      "role": "Worker" | "Critic"
    }
  ]
}

Rules:
- Each step must be concrete and actionable
- Worker steps: execution, generation, research
- Critic steps: review, validate, verify
- Order matters: plan dependencies correctly
"""

WORKER_SYSTEM_PROMPT = """You are a Worker Agent in Project Rain's multi-agent system.

Your job: execute the assigned task and produce a complete, concrete result.

Rules:
- Read the task description carefully. Deliver exactly what is asked — no more, no less.
- Be thorough: cover all requirements, handle edge cases, do not leave placeholders.
- For code: write complete, runnable code. Explain only what is non-obvious.
- For research: synthesize findings into clear, structured output with key takeaways.
- For writing: produce polished, final-quality output ready for use.
- Be precise, not creative. Stay on target.
- Output plain text. Use markdown only when it clearly improves readability."""

CRITIC_SYSTEM_PROMPT = """You are a Critic Agent in Project Rain's multi-agent system.

Your job: review the previous step's output and identify issues.

Rules:
- Check for factual errors, logical gaps, missing edge cases, and quality issues.
- Be specific: name exactly what is wrong and why — no vague feedback.
- Suggest concrete, actionable improvements.
- If the output is acceptable as-is, say so explicitly in one sentence and stop.
- Output plain text. Be concise."""


class WorkModeOrchestrator:
    """Orchestrates the Reasoning-Planning-Execution loop with real LLM calls."""

    def __init__(self, db: AsyncSession, providers: dict):
        self.db = db
        self.providers = providers

    async def broadcast_status(self, run_id: UUID, status: str, message: str = ""):
        """Send a real-time update over WebSocket."""
        from rain_backend.api.v1.agent_runs import manager
        await manager.broadcast(run_id, {
            "type": "status_update",
            "status": status,
            "message": message,
            "timestamp": datetime.now(UTC).isoformat(),
        })

    async def start_run(self, run_id: UUID) -> AsyncGenerator[dict, None]:
        """Execute a multi-agent run with real LLM calls."""

        run = await self.db.get(AgentRun, run_id)
        if not run:
            logger.error(f"AgentRun {run_id} not found.")
            return

        run.status = AgentRunStatus.running
        await self.db.commit()
        await self.broadcast_status(run_id, "running", "Orchestrator initialized. Waking up Planner...")

        try:
            yield {"type": "status", "phase": "planning", "message": "Planner starting..."}

            await self._run_planner(run)

            yield {"type": "status", "phase": "execution", "message": "Planner complete. Starting execution..."}

            async for progress in self._run_execution_loop(run):
                yield progress

            run.status = AgentRunStatus.completed
            await self.db.commit()
            await self.broadcast_status(run_id, "completed", "Workflow completed successfully.")
            yield {"type": "done", "status": "completed"}

        except Exception as e:
            logger.exception(f"Run {run_id} failed: {e}")
            run.status = AgentRunStatus.failed
            await self.db.commit()
            await self.broadcast_status(run_id, "failed", f"Workflow failed: {e}")
            yield {"type": "error", "message": str(e)}

    async def _run_planner(self, run: AgentRun):
        """The Planner agent analyzes the goal and creates AgentTasks using LLM."""
        await self.broadcast_status(run.id, "planning", "Planner is breaking down the objective...")

        provider = self.providers.get("ollama")
        if provider:
            req = ChatRequest(
                messages=[
                    {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Goal: {run.goal}\n\nGenerate a plan."},
                ],
                model="glm-5.1:cloud",
                temperature=0.2,
                response_format={"type": "json_object"},
                stream=False,
                max_tokens=2048,
            )

            result_text = ""
            async for chunk in provider.chat(req):
                if chunk.type == "token":
                    result_text += str(chunk.data)
                elif chunk.type == "done":
                    if chunk.data and isinstance(chunk.data, dict):
                        full_text = chunk.data.get("content", "")
                        if full_text:
                            result_text = str(full_text)

            try:
                plan = json.loads(result_text.strip())
            except json.JSONDecodeError:
                if "```json" in result_text:
                    block = result_text.split("```json")[1].split("```")[0]
                    plan = json.loads(block.strip())
                elif "```" in result_text:
                    block = result_text.split("```")[1].split("```")[0]
                    plan = json.loads(block.strip())
                else:
                    plan = {"steps": [{"label": "Execute", "description": run.goal, "role": "Worker"}]}
        else:
            plan = {"steps": [{"label": "Execute", "description": run.goal, "role": "Worker"}]}

        run.plan = plan

        # Create tasks in DB
        for i, step in enumerate(plan["steps"]):
            task = AgentTask(
                run_id=run.id,
                position=i,
                label=step["label"],
                description=step["description"],
                agent_role=step["role"],
                status=TaskStatus.pending,
            )
            self.db.add(task)

        await self.db.commit()
        await self.broadcast_status(run.id, "planning", f"Planner created {len(plan['steps'])} tasks.")

    async def _run_execution_loop(self, run: AgentRun) -> AsyncGenerator[dict, None]:
        """Executes tasks sequentially with real LLM calls."""

        query = select(AgentTask).where(AgentTask.run_id == run.id).order_by(AgentTask.position)
        result = await self.db.execute(query)
        tasks = result.scalars().all()

        provider = self.providers.get("ollama")

        for task in tasks:
            task.status = TaskStatus.running
            await self.db.commit()

            await self.broadcast_status(run.id, "task_started", f"{task.agent_role.capitalize()} started: {task.label}")
            yield {"type": "task_started", "task_id": str(task.id), "label": task.label, "role": task.agent_role}

            if provider:
                system_prompt = CRITIC_SYSTEM_PROMPT if task.agent_role == "Critic" else WORKER_SYSTEM_PROMPT
                req = ChatRequest(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Task: {task.description}\nContext: {run.goal}"},
                    ],
                    model="glm-5.1:cloud",
                    temperature=get_temperature("code" if task.agent_role == "Worker" else "general_chat"),
                    stream=True,
                    max_tokens=2048,
                )

                output_buffer = ""
                async for chunk in provider.chat(req):
                    if chunk.type == "token":
                        token = str(chunk.data)
                        output_buffer += token
                        yield {"type": "token", "task_id": str(task.id), "data": token}
                    elif chunk.type == "done":
                        if chunk.data and isinstance(chunk.data, dict):
                            full_text = chunk.data.get("content", "")
                            if full_text:
                                output_buffer = str(full_text)
                    elif chunk.type == "error":
                        logger.error(f"Worker error: {chunk.data}")

                task.output_data = {"result": output_buffer}
            else:
                task.output_data = {"result": f"Completed {task.label} (no provider available)"}

            task.status = TaskStatus.completed
            await self.db.commit()

            await self.broadcast_status(run.id, "task_completed", f"{task.agent_role.capitalize()} finished: {task.label}")
            yield {"type": "task_completed", "task_id": str(task.id), "label": task.label}
