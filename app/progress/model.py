"""Local profile, XP, levels and daily streak ("flames") for Bulle.

Everything lives in one small JSON file on this computer; there is no server.
Qt-free and date-injectable, so it is fully unit-tested.

    XP     10 per translated page
    Level  n starts at 50 * (n - 1) ** 2 XP   (1: 0, 2: 50, 3: 200, 4: 450, ...)
    Flame  a day is lit as soon as one page is translated; the streak counts the
           consecutive lit days and stays alive until the end of the next day.
"""

import json
import math
import os
from datetime import date, timedelta
from typing import Optional

XP_PER_PAGE = 10
LEVEL_NAMES = [
    "Apprentice", "Translator", "Typesetter", "Cleaner", "Scanlator",
    "Editor", "Bubble Master", "Scan Legend",
]
DAILY_GOALS = (1, 3, 5, 10, 20)


def xp_for_level(level: int) -> int:
    """Total XP needed to reach ``level`` (level 1 = 0)."""
    return 50 * max(level - 1, 0) ** 2


def level_from_xp(xp: int) -> int:
    return int(math.isqrt(max(int(xp), 0) // 50)) + 1


def level_name(level: int) -> str:
    return LEVEL_NAMES[min(max(level, 1), len(LEVEL_NAMES)) - 1]


def _iso(d: date) -> str:
    return d.isoformat()


class Progress:
    def __init__(self, path: str):
        self.path = path
        self.data = self._load()

    # ------------------------------------------------------------ storage
    @staticmethod
    def _blank() -> dict:
        return {"name": "", "daily_goal": 3, "xp": 0, "history": {}, "created": ""}

    def _load(self) -> dict:
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                blank = self._blank()
                blank.update({k: v for k, v in data.items() if k in blank})
                if isinstance(blank["history"], dict):
                    return blank
        except (OSError, ValueError):
            pass
        return self._blank()

    def save(self) -> None:
        folder = os.path.dirname(self.path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    # ------------------------------------------------------------ profile
    def has_profile(self) -> bool:
        return bool(self.data.get("name"))

    def create_profile(self, name: str, daily_goal: int, today: Optional[date] = None) -> None:
        self.data["name"] = (name or "").strip()[:30]
        self.data["daily_goal"] = daily_goal if daily_goal in DAILY_GOALS else 3
        self.data["created"] = _iso(today or date.today())
        self.save()

    def set_goal(self, daily_goal: int) -> None:
        self.data["daily_goal"] = daily_goal if daily_goal in DAILY_GOALS else self.data["daily_goal"]
        self.save()

    # ------------------------------------------------------------ queries
    @property
    def name(self) -> str:
        return self.data["name"]

    @property
    def xp(self) -> int:
        return int(self.data["xp"])

    @property
    def level(self) -> int:
        return level_from_xp(self.xp)

    def level_progress(self) -> float:
        """0..1 progress inside the current level."""
        lo, hi = xp_for_level(self.level), xp_for_level(self.level + 1)
        return (self.xp - lo) / (hi - lo)

    def pages_on(self, day: date) -> int:
        return int(self.data["history"].get(_iso(day), 0))

    def streak(self, today: Optional[date] = None) -> int:
        today = today or date.today()
        day = today if self.pages_on(today) > 0 else today - timedelta(days=1)
        count = 0
        while self.pages_on(day) > 0:
            count += 1
            day -= timedelta(days=1)
        return count

    def week(self, today: Optional[date] = None) -> list[dict]:
        """Monday..Sunday of the current week: {'day', 'lit', 'today', 'future'}."""
        today = today or date.today()
        monday = today - timedelta(days=today.weekday())
        cells = []
        for i in range(7):
            d = monday + timedelta(days=i)
            cells.append({"day": d, "lit": self.pages_on(d) > 0, "today": d == today, "future": d > today})
        return cells

    # ------------------------------------------------------------ updates
    def record_pages(self, pages: int, today: Optional[date] = None) -> dict:
        """Register translated pages and report what the celebration should show."""
        today = today or date.today()
        pages = max(int(pages), 0)
        before_level = self.level
        before_streak = self.streak(today)
        was_lit = self.pages_on(today) > 0
        goal = int(self.data["daily_goal"])
        before_today = self.pages_on(today)

        if pages:
            self.data["history"][_iso(today)] = before_today + pages
            self.data["xp"] = self.xp + pages * XP_PER_PAGE
            self.save()

        after_streak = self.streak(today)
        return {
            "xp_gained": pages * XP_PER_PAGE,
            "level": self.level,
            "level_up": self.level > before_level,
            "streak": after_streak,
            "streak_extended": pages > 0 and not was_lit and after_streak > before_streak,
            "streak_started": pages > 0 and not was_lit and before_streak == 0,
            "goal_reached": pages > 0 and before_today < goal <= before_today + pages,
        }
