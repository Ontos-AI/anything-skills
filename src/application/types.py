from __future__ import annotations

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


class SkillSpec(BaseModel):
    name: str
    description: str
    tags: List[str] = Field(default_factory=list)
    content: str


class TestCaseSpec(BaseModel):
    name: str
    input: str
    expected: str
    environment: str = ""
    edge_cases: List[str] = Field(default_factory=list)


class ExecutionReport(BaseModel):
    passed: bool
    issues: List[str] = Field(default_factory=list)
    notes: str = ""
    outputs: Dict[str, Any] = Field(default_factory=dict)


class AgentOutput(BaseModel):
    status: Literal["ok", "fail"]
    next_agent: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    trace_id: str
