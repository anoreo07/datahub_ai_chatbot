"""Scheduler for periodic worker tasks."""


class Scheduler:
    """Schedules and manages periodic background tasks."""

    async def start(self) -> None:
        raise NotImplementedError("Scheduler is not implemented yet.")

    async def stop(self) -> None:
        raise NotImplementedError("Scheduler stop is not implemented yet.")
