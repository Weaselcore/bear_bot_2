
from datetime import datetime
from zoneinfo import ZoneInfo

from manager.timezone_service import TimezoneManager

class TestTimezoneService:

    def test_positive_difference(self):
        dt1 = datetime.now(tz=ZoneInfo('NZ'))
        dt2 = datetime.now(tz=ZoneInfo('Japan'))
        _, time_delta, descriptor = TimezoneManager.get_datetime_difference(dt1, dt2)
        assert time_delta.total_seconds() > 0 and descriptor == "behind"

    def test_negative_difference(self):
        dt1 = datetime.now(tz=ZoneInfo('America/Toronto'))
        dt2 = datetime.now(tz=ZoneInfo('NZ'))
        _, time_delta, descriptor = TimezoneManager.get_datetime_difference(dt1, dt2)
        print(time_delta)
        assert time_delta.total_seconds() < 0 and descriptor == "ahead"