from __future__ import annotations

import json
import math
import os


def cost_trace(provider: str, model: str, input_tokens: int | None,
               output_tokens: int | None) -> dict:
    """Estimate generation cost from explicitly configured USD-per-million rates.

    No baked-in prices: deployments supply their negotiated/effective rates.
    Unknown usage or missing rates remains unknown, never zero.
    """
    config = json.loads(os.getenv("PROMPTOPS_TOKEN_PRICES", "{}"))
    rates = config.get(f"{provider}:{model}")
    if rates is None or input_tokens is None or output_tokens is None:
        return {}
    values = [rates.get("input"), rates.get("output")]
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in values):
        raise ValueError("Token prices must be finite non-negative input/output USD-per-million rates")
    return {"cost_usd": (input_tokens * values[0] + output_tokens * values[1]) / 1_000_000,
            "cost_source": "configured_token_rate_estimate"}
