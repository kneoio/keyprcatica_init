import json

from database import get_connection
from util.logging import logger


class OnceTrigger:
    def __init__(self, start_time=None, duration=None, weekdays=None):
        self.start_time = start_time
        self.duration = duration
        self.weekdays = weekdays or []

    def to_dict(self):
        return {
            "startTime": self.start_time,
            "duration": self.duration,
            "weekdays": self.weekdays
        }


class TimeWindowTrigger:
    def __init__(self, start_time=None, end_time=None, weekdays=None):
        self.start_time = start_time
        self.end_time = end_time
        self.weekdays = weekdays or []

    def to_dict(self):
        return {
            "startTime": self.start_time,
            "endTime": self.end_time,
            "weekdays": self.weekdays
        }


class PeriodicTrigger:
    def __init__(self, start_time=None, end_time=None, interval=None, weekdays=None):
        self.start_time = start_time
        self.end_time = end_time
        self.interval = interval
        self.weekdays = weekdays or []

    def to_dict(self):
        return {
            "startTime": self.start_time,
            "endTime": self.end_time,
            "interval": self.interval,
            "weekdays": self.weekdays
        }


class Task:
    def __init__(self, type=None, target=None, trigger_type=None, once_trigger=None,
                 time_window_trigger=None, periodic_trigger=None):
        self.type = type
        self.target = target
        self.trigger_type = trigger_type
        self.once_trigger = once_trigger
        self.time_window_trigger = time_window_trigger
        self.periodic_trigger = periodic_trigger

    def to_dict(self):
        return {
            "type": self.type,
            "target": self.target,
            "triggerType": self.trigger_type,
            "onceTrigger": self.once_trigger.to_dict() if self.once_trigger else None,
            "timeWindowTrigger": self.time_window_trigger.to_dict() if self.time_window_trigger else None,
            "periodicTrigger": self.periodic_trigger.to_dict() if self.periodic_trigger else None
        }


class Schedule:
    def __init__(self, timezone=None, tasks=None):
        self.timezone = timezone
        self.tasks = tasks or []
        self.enabled = False

    def to_dict(self):
        return {
            "enabled": self.enabled,
            "tasks": [task.to_dict() for task in self.tasks]
        }


class ScheduleWrapper:
    def __init__(self, schedule=None):
        self.schedule = schedule

    def to_dict(self):
        return {
            "schedule": self.schedule.to_dict() if self.schedule else None
        }


def create_default_schedule():
    weekdays = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]

    morning_trigger = TimeWindowTrigger(
        start_time="09:00",
        end_time="10:00",
        weekdays=weekdays
    )

    evening_trigger = TimeWindowTrigger(
        start_time="23:00",
        end_time="00:00",
        weekdays=weekdays
    )

    morning_task = Task(
        type="PROCESS_DJ_CONTROL",
        target="default",
        trigger_type="TIME_WINDOW",
        time_window_trigger=morning_trigger
    )

    evening_task = Task(
        type="PROCESS_DJ_CONTROL",
        target="default",
        trigger_type="TIME_WINDOW",
        time_window_trigger=evening_trigger
    )

    schedule = Schedule(
        timezone="Europe/Lisbon",
        tasks=[morning_task, evening_task]
    )

    return ScheduleWrapper(schedule=schedule)


def update_brands_schedule():
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id FROM kneobroadcaster__brands")
        brands = cursor.fetchall()

        default_schedule = create_default_schedule()
        schedule_json = json.dumps(default_schedule.to_dict())
        print(schedule_json)
        for brand in brands:
            brand_id = brand[0]

            cursor.execute("""
                UPDATE kneobroadcaster__brands
                SET schedule = %s
                WHERE id = %s
            """, (schedule_json, brand_id))

            logger.info(f"Updated schedule for brand {brand_id}")

        conn.commit()
        logger.info(f"Updated {len(brands)} brands with default schedule")

    except Exception as e:
        logger.error(f"Error updating brands schedule: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    update_brands_schedule()