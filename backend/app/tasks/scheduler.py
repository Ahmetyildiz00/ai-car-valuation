from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource

from app.core.broker import broker, schedule_source

# Import tasks so they register with the broker
from app.tasks.scraper_tasks import scrape_all_brands_task  # noqa: F401

scheduler = TaskiqScheduler(broker=broker, sources=[LabelScheduleSource(broker)])
