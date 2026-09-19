def merge_decision_universe(
    configured: list[str],
    held: list[str],
) -> list[str]:
    """Stable configured-first union so every held asset stays monitored."""
    result: list[str] = []
    seen: set[str] = set()

    for raw in [*configured, *held]:
        value = str(raw).strip().upper()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)

    return result
