from taskiq_redis import ListQueueBroker, RedisScheduleSource

from app.core.config import settings

broker = ListQueueBroker(url=settings.REDIS_URL)

schedule_source = RedisScheduleSource(url=settings.REDIS_URL)
