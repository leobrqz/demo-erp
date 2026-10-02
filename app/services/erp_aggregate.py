# Leonardo Briquezi
# github: https://github.com/leobrqz
# linkedin: https://www.linkedin.com/in/leonardobri
import asyncio
from collections.abc import Awaitable, Callable
from typing import Any


class TemporarySourceError(Exception):
    """Represents a retryable failure from one of the mocked ERP services."""


async def _inventory_source() -> dict[str, Any]:
    await asyncio.sleep(0.03)
    return {"available_units": 24, "reserved_units": 3}


async def _finance_source() -> dict[str, Any]:
    await asyncio.sleep(0.06)
    return {"open_invoices": 2, "balance_due": "1250.00"}


async def _customer_source() -> dict[str, Any]:
    await asyncio.sleep(0.04)
    return {"customer_id": "demo-customer-001", "credit_status": "approved"}


async def _with_timeout_retry(
    source_name: str,
    operation: Callable[[], Awaitable[dict[str, Any]]],
    *,
    timeout_seconds: float,
    retries: int,
) -> dict[str, Any]:
    for attempt in range(1, retries + 2):
        try:
            data = await asyncio.wait_for(operation(), timeout=timeout_seconds)
            return {"status": "ok", "attempts": attempt, "data": data, "error": None}
        except (TimeoutError, TemporarySourceError) as exc:
            if attempt <= retries:
                await asyncio.sleep(0.02 * attempt)
                continue
            error = "timeout" if isinstance(exc, TimeoutError) else "temporary_failure"
            return {"status": "unavailable", "attempts": attempt, "data": None, "error": error}
        except Exception:
            return {"status": "unavailable", "attempts": attempt, "data": None, "error": "source_error"}
    return {
        "status": "unavailable",
        "attempts": retries + 1,
        "data": None,
        "error": f"{source_name}_unavailable",
    }


async def get_erp_snapshot(timeout_ms: int = 250, retries: int = 1) -> dict[str, Any]:
    timeout_seconds = timeout_ms / 1000
    names_and_operations = (
        ("inventory", _inventory_source),
        ("finance", _finance_source),
        ("customer", _customer_source),
    )
    results = await asyncio.gather(
        *(
            _with_timeout_retry(
                name,
                operation,
                timeout_seconds=timeout_seconds,
                retries=retries,
            )
            for name, operation in names_and_operations
        ),
        return_exceptions=True,
    )
    sources = {
        name: result
        if isinstance(result, dict)
        else {"status": "unavailable", "attempts": 1, "data": None, "error": "source_error"}
        for (name, _), result in zip(names_and_operations, results, strict=True)
    }
    return {
        "sources": sources,
        "degraded": any(result["status"] != "ok" for result in sources.values()),
        "notice": "As três fontes são mocks locais para demonstrar agregação resiliente.",
    }

