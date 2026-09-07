from copy import deepcopy
from threading import Lock


class PatternStore:
    def __init__(self) -> None:
        self._items: dict[str, dict] = {}
        self._lock = Lock()

    def put(self, pattern_id: str, value: dict) -> None:
        with self._lock:
            self._items[pattern_id] = value

    def get(self, pattern_id: str) -> dict | None:
        with self._lock:
            value = self._items.get(pattern_id)
            return deepcopy(value) if value else None

    def update_plans(self, pattern_id: str, plans: dict) -> dict | None:
        with self._lock:
            if pattern_id not in self._items:
                return None
            self._items[pattern_id]["plans"].update(plans)
            return deepcopy(self._items[pattern_id])


store = PatternStore()

