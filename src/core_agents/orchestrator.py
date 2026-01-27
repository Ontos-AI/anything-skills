"""Orchestrator for multi-agent workflow."""
from __future__ import annotations

import uuid
from typing import List, Optional

from src.application.types import AgentOutput, SkillSpec, TestCaseSpec, ExecutionReport
from src.core_agents.skill_generator import SkillGeneratorAgent
from src.core_agents.scenario_simulator import ScenarioSimulatorAgent
from src.core_agents.executor import ExecutorAgent
from src.core_agents.validator import ValidatorAgent
from src.services.skills_store import save_skill


class Orchestrator:
    name = "orchestrator"

    def __init__(self, max_rounds: int = 2) -> None:
        self.max_rounds = max_rounds
        self.skill_agent = SkillGeneratorAgent()
        self.scenario_agent = ScenarioSimulatorAgent()
        self.executor_agent = ExecutorAgent()
        self.validator_agent = ValidatorAgent()

    async def run(
        self,
        task: str,
        sources: List[str],
        tools,
        emit,
    ) -> AgentOutput:
        trace_id = str(uuid.uuid4())
        feedback: Optional[str] = None
        last_skill: Optional[SkillSpec] = None
        last_tests: List[TestCaseSpec] = []
        last_validation: Optional[ExecutionReport] = None
        execution_report: Optional[ExecutionReport] = None

        await emit(self.name, "plan", "Execute task first, then derive skill.", {})
        execution_report = await self.executor_agent.run(task, sources, tools, emit)
        if not execution_report.passed:
            return AgentOutput(
                status="fail",
                next_agent=None,
                payload={"execution": execution_report.model_dump()},
                errors=execution_report.issues,
                trace_id=trace_id,
            )

        execution_summary = execution_report.model_dump()

        for round_id in range(1, self.max_rounds + 1):
            await emit(self.name, "plan", f"Skill draft round {round_id}/{self.max_rounds}.", {})

            skill = await self.skill_agent.run(
                task,
                sources,
                tools,
                emit,
                feedback=feedback,
                execution_summary=execution_summary,
            )
            tests = await self.scenario_agent.run(task, skill, tools, emit)
            validation = await self.validator_agent.run(skill, tests, emit)

            last_skill = skill
            last_tests = tests
            last_validation = validation

            if validation.passed:
                await emit(self.name, "observation", "Skill validated successfully.", {})
                saved = save_skill(skill.name, skill.description, skill.content, source="generated")
                await emit(self.name, "observation", f"Skill saved: {saved.path}", {})
                return AgentOutput(
                    status="ok",
                    next_agent="final",
                    payload={
                        "execution": execution_report.model_dump(),
                        "skill": skill.model_dump(),
                        "tests": [test.model_dump() for test in tests],
                        "validation": validation.model_dump(),
                    },
                    errors=[],
                    trace_id=trace_id,
                )

            feedback = "; ".join(validation.issues)
            await emit(self.name, "action", "Skill validation failed; retrying with feedback.", {"feedback": feedback})

        return AgentOutput(
            status="fail",
            next_agent=None,
            payload={
                "execution": execution_report.model_dump() if execution_report else {},
                "skill": last_skill.model_dump() if last_skill else {},
                "tests": [test.model_dump() for test in last_tests],
                "validation": last_validation.model_dump() if last_validation else {},
            },
            errors=(last_validation.issues if last_validation else ["Unknown failure"]),
            trace_id=trace_id,
        )
