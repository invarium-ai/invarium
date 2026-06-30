"""A real LangGraph ReAct agent — the agent pattern most people actually ship.

``langgraph.prebuilt.create_react_agent`` + a real LLM (OpenAI or Gemini) +
real tools (Tavily web search and a calculator). No mocks: this makes live model
and search calls.

Configure via environment (defaults in parentheses):

- ``RW_LLM_PROVIDER``  openai | gemini      (openai)
- ``RW_OPENAI_MODEL``  e.g. gpt-4o-mini      (gpt-4o-mini)
- ``RW_GEMINI_MODEL``  e.g. gemini-2.5-flash (gemini-2.5-flash)

Keys are read from the repo-root ``.env`` (gitignored). Swapping the provider or
model lets you bless one configuration as a baseline and catch real behavioral
drift in another — e.g. a cheaper model that stops grounding its answers with search.
"""

from __future__ import annotations

import ast
import operator
import os

from dotenv import find_dotenv, load_dotenv
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

load_dotenv(find_dotenv(usecwd=True))

_SYSTEM_PROMPT = (
    "You are a helpful research assistant. "
    "For any question about current or real-world facts (people, prices, events, "
    "definitions you are unsure of), you MUST call the `tavily_search` tool before "
    "answering — do not answer factual questions from memory. "
    "For any arithmetic, call the `calculator` tool instead of computing it yourself. "
    "Keep the final answer to one or two short sentences."
)


def _require_key(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value or "REPLACE" in value:
        raise RuntimeError(
            f"{name} is not set. Add your real key to the repo-root `.env` "
            f"(see real_world_examples/README.md)."
        )
    return value


_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPERATORS:
        return _ALLOWED_OPERATORS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPERATORS:
        return _ALLOWED_OPERATORS[type(node.op)](_eval_node(node.operand))
    raise ValueError("Unsupported expression.")


@tool
def calculator(expression: str) -> str:
    """Evaluate a basic arithmetic expression, e.g. '1234 * 5678' or '(3+4)/2'."""
    try:
        result = _eval_node(ast.parse(expression, mode="eval").body)
    except Exception as exc:  # noqa: BLE001
        return f"Could not evaluate '{expression}': {exc}"
    return str(result)


def _build_llm():
    provider = os.environ.get("RW_LLM_PROVIDER", "openai").strip().lower()
    if provider == "gemini":
        _require_key("GOOGLE_API_KEY")
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=os.environ.get("RW_GEMINI_MODEL", "gemini-2.5-flash"),
            temperature=0,
        )
    _require_key("OPENAI_API_KEY")
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=os.environ.get("RW_OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
    )


def build_search_agent():
    """Build a real ReAct agent with web search + calculator tools."""
    _require_key("TAVILY_API_KEY")
    from langchain_tavily import TavilySearch

    llm = _build_llm()
    tools = [TavilySearch(max_results=3), calculator]
    return create_react_agent(llm, tools=tools, prompt=_SYSTEM_PROMPT)
