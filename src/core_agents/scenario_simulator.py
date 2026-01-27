"""Scenario simulation agent."""
from __future__ import annotations

from typing import List

from src.application.types import TestCaseSpec, SkillSpec


class ScenarioSimulatorAgent:
    name = "scenario_simulator"

    async def run(self, task: str, skill: SkillSpec, tools, emit) -> List[TestCaseSpec]:
        await emit(self.name, "plan", "Generate test cases for the skill.", {})
        await emit(self.name, "action", "Drafting test cases...", {})
        test_payloads = await tools.generate_test_cases(task, skill.model_dump())
        tests = [TestCaseSpec(**payload) for payload in test_payloads]
        await emit(self.name, "observation", f"Test cases generated: {len(tests)}", {})
        return tests
