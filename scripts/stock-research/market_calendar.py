"""Explicit exchange sessions; no weekday approximations or provider access."""
from bisect import bisect_left, bisect_right
from datetime import date, timedelta
from importlib.metadata import version


class MarketCalendar:
    def __init__(self, start='1990-01-01', end='2040-12-31', name='XNYS'):
        import exchange_calendars
        self.name = name
        self.calendar = exchange_calendars.get_calendar(name, start=start, end=end)
        self.version = version('exchange_calendars')
        self._sessions=tuple(item.date().isoformat() for item in self.calendar.sessions)
        self._closes={day:int(value.value//1_000_000) for day,value in zip(self._sessions,self.calendar.closes)}
        self._opens={day:int(value.value//1_000_000) for day,value in zip(self._sessions,self.calendar.opens)}

    def sessions(self, start, end):
        if start> end or start<self._sessions[0] or end>self._sessions[-1]:
            raise ValueError('calendar-range-unavailable')
        return list(self._sessions[bisect_left(self._sessions,start):bisect_right(self._sessions,end)])

    def trailing_sessions(self, origin, count):
        end=bisect_right(self._sessions,origin)
        return list(self._sessions[max(0,end-count):end])

    def close_ms(self, day):
        try: return self._closes[day]
        except KeyError: raise ValueError('not-exchange-session') from None

    def open_ms(self, day):
        try: return self._opens[day]
        except KeyError: raise ValueError('not-exchange-session') from None

    def windows(self, origin):
        day = date.fromisoformat(origin)
        if origin not in self.sessions(origin, origin):
            raise ValueError('origin-not-session')
        future = self.sessions((day + timedelta(days=1)).isoformat(), (day + timedelta(days=21)).isoformat())
        monday = day + timedelta(days=7-day.weekday())
        week = self.sessions(monday.isoformat(), (monday+timedelta(days=4)).isoformat())
        if len(future) < 5 or not week:
            raise ValueError('calendar-window-unavailable')
        return {'1d': future[:1], '3d': future[:3], '5d': future[:5], 'next_week': week}
