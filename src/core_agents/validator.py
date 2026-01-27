"""Skill validation agent (quality gate)."""
from __future__ import annotations

from typing import List

from src.application.types import SkillSpec, TestCaseSpec, ExecutionReport


class ValidatorAgent:
    name = "validator"

    async def run(self, skill: SkillSpec, tests: List[TestCaseSpec], emit) -> ExecutionReport:
        await emit(self.name, "plan", "Validate skill quality and test completeness.", {})
        issues: List[str] = []

        if not skill.content.strip():
            issues.append("Skill content is empty.")
        if len(skill.content.splitlines()) < 3:
            issues.append("Skill content is too short to be executable.")
        if not tests:
            issues.append("No test cases generated.")

        keywords = ["步骤", "step", "1.", "- "]
        if not any(token in skill.content for token in keywords):
            issues.append("Skill content lacks step-by-step structure.")

        for test in tests:
            if not test.input or not test.expected:
                issues.append(f"Test '{test.name}' missing input/expected.")

        passed = not issues
        notes = "Skill validation passed." if passed else "Skill validation failed."
        await emit(self.name, "observation", notes, {"issues": issues})
        return ExecutionReport(passed=passed, issues=issues, notes=notes)
