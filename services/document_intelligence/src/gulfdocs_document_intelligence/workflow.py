from typing import Any, TypedDict, cast

from langgraph.graph import END, START, StateGraph

from .extraction import StructuredExtraction
from .models import DocumentType
from .providers.ports import AIProvider
from .security import detect_prompt_injection
from .validation import DeterministicIssue, validate_extraction


class ProcessingState(TypedDict, total=False):
    page_text: list[str]
    document_type: DocumentType
    extraction: StructuredExtraction
    issues: list[DeterministicIssue]
    security_signals: list[dict[str, Any]]


class DeterministicDocumentWorkflow:
    def __init__(self, provider: AIProvider) -> None:
        self.provider = provider
        graph = StateGraph(ProcessingState)
        graph.add_node("inspect_security", self._inspect_security)
        graph.add_node("classify", self._classify)
        graph.add_node("extract", self._extract)
        graph.add_node("validate", self._validate)
        graph.add_edge(START, "inspect_security")
        graph.add_edge("inspect_security", "classify")
        graph.add_edge("classify", "extract")
        graph.add_edge("extract", "validate")
        graph.add_edge("validate", END)
        self.graph = graph.compile()

    async def run(self, page_text: list[str]) -> ProcessingState:
        return cast(ProcessingState, await self.graph.ainvoke({"page_text": page_text}))

    @staticmethod
    def _inspect_security(state: ProcessingState) -> dict[str, Any]:
        signals = []
        for page_number, text in enumerate(state["page_text"], start=1):
            for signal in detect_prompt_injection(text):
                signals.append({"code": signal.code, "page": page_number})
        return {"security_signals": signals}

    async def _classify(self, state: ProcessingState) -> dict[str, Any]:
        return {"document_type": await self.provider.classify(state["page_text"])}

    async def _extract(self, state: ProcessingState) -> dict[str, Any]:
        return {
            "extraction": await self.provider.extract(state["document_type"], state["page_text"])
        }

    @staticmethod
    def _validate(state: ProcessingState) -> dict[str, Any]:
        return {"issues": validate_extraction(state["extraction"])}
