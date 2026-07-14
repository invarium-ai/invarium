from invarium.adapters.python import PythonAdapter
from invarium.result import AgentResult


class SyncAgent:
    def run(self, prompt: str):
        return AgentResult(
            input=prompt,
            final_output="sync response",
        )


class AsyncAgent:
    async def run(self, prompt: str):
        return AgentResult(
            input=prompt,
            final_output="async response",
        )


class AsyncDictAgent:
    async def run(self, prompt: str):
        return {
            "input": prompt,
            "final_output": "async dict response",
        }

class SyncDictAgent:
    def run(self, prompt: str):
        return {
            "input": prompt,
            "final_output": "sync dict response",
        }

def test_python_adapter_sync_agent():
    adapter = PythonAdapter()

    result = adapter.run(SyncAgent(), "hello")

    assert isinstance(result, AgentResult)
    assert result.final_output == "sync response"


def test_python_adapter_async_agent():
    adapter = PythonAdapter()

    result = adapter.run(AsyncAgent(), "hello")

    assert isinstance(result, AgentResult)
    assert result.final_output == "async response"


def test_python_adapter_async_dict_result():
    adapter = PythonAdapter()

    result = adapter.run(AsyncDictAgent(), "hello")

    assert isinstance(result, AgentResult)
    assert result.final_output == "async dict response"



def test_python_adapter_sync_dict_result():
    adapter = PythonAdapter()

    result = adapter.run(SyncDictAgent(), "hello")

    assert isinstance(result, AgentResult)
    assert result.final_output == "sync dict response"