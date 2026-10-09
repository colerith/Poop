from datetime import datetime


class PoopSessionState:
    """管理进行中的如厕会话与提醒计数。"""

    def __init__(self):
        self._starters: dict[int, tuple[datetime, int]] = {}
        self._reminder_count: dict[int, int] = {}

    def has_session(self, user_id: int) -> bool:
        return user_id in self._starters

    def start_session(self, user_id: int, start_time: datetime, guild_id: int) -> None:
        self._starters[user_id] = (start_time, guild_id)
        self._reminder_count[user_id] = 0

    def get_session(self, user_id: int):
        return self._starters.get(user_id)

    def pop_session(self, user_id: int):
        self._reminder_count.pop(user_id, None)
        return self._starters.pop(user_id, None)

    def iter_sessions(self):
        return list(self._starters.items())

    def get_reminder_count(self, user_id: int) -> int:
        return self._reminder_count.get(user_id, 0)

    def set_reminder_count(self, user_id: int, value: int) -> None:
        self._reminder_count[user_id] = value

    def restore_session(self, user_id: int, session: tuple[datetime, int]) -> None:
        self._starters[user_id] = session
