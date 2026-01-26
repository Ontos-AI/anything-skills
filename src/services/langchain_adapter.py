"""LangChain adapters for Agent Arena."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.runnables import RunnableLambda


@dataclass
class LangChainEventHandler(BaseCallbackHandler):
    events: List[Dict[str, Any]] = field(default_factory=list)

    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any) -> None:
        self.events.append({"stage": "thought", "message": "LangChain: chain started"})

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        self.events.append({"stage": "thought", "message": "LangChain: chain completed"})


def _plan_step(task: str) -> str:
    return f"Plan: break down '{task[:80]}' into sources and extraction steps."


def run_plan_chain(task: str) -> Tuple[List[Dict[str, Any]], str]:
    handler = LangChainEventHandler()
    chain = RunnableLambda(_plan_step)
    result = chain.invoke(task, config={"callbacks": [handler]})
    return handler.events, result
