import inspect
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(slots=True)
class AgentTestDefinition:
    func: Callable[..., Any]
    name: str
    runs: int
    agent_factory: Callable[[], Any] | None = None
    parallel: bool = False
    max_workers: int | None = None


REGISTERED_TESTS: list[AgentTestDefinition] = []


def agent_test(
    *,
    runs: int = 1,
    agent_factory: Callable[[], Any] | None = None,
    parallel: bool = False,
    max_workers: int | None = None,
):
    """Register a behavioral test.

    Args:
        runs: How many times to execute the test (stability sampling).
        agent_factory: Zero-arg factory called once per run to build a fresh agent.
        parallel: If True (or ``max_workers`` > 1), execute the ``runs`` repetitions
            concurrently on a thread pool instead of sequentially. Each run is
            independent (its own agent + result), so this cuts wall-clock time for
            live-model tests roughly N-fold. Defaults to False to preserve behavior
            and avoid surprising provider rate limits.
        max_workers: Cap on concurrent runs. Defaults to ``runs`` when parallel.
    """
    if max_workers is not None and max_workers < 1:
        raise ValueError("max_workers must be >= 1 when provided.")

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        definition = AgentTestDefinition(
            func=func,
            name=func.__name__,
            runs=runs,
            agent_factory=agent_factory,
            parallel=parallel,
            max_workers=max_workers,
        )
        setattr(func, "__invarium_test__", definition)
        setattr(func, "__test__", False)
        REGISTERED_TESTS.append(definition)
        return func

    return decorator


def resolve_test_argument(definition: AgentTestDefinition) -> tuple[list[Any], dict[str, Any]]:
    signature = inspect.signature(definition.func)
    if not signature.parameters:
        return [], {}
    if len(signature.parameters) != 1:
        raise TypeError(
            f"Test `{definition.name}` must accept zero or one argument."
        )
    if definition.agent_factory is None:
        raise TypeError(
            f"Test `{definition.name}` expects an agent argument, but no `agent_factory` was provided."
        )
    return [definition.agent_factory()], {}
