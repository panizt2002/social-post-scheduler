import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class DuePostProducer:
    """Thin wrapper around the Kafka producer so it can be swapped out in tests."""

    def __init__(self, bootstrap_servers=None, topic=None):
        from confluent_kafka import Producer

        self.topic = topic or settings.KAFKA_DUE_POSTS_TOPIC
        self._producer = Producer(
            {
                "bootstrap.servers": bootstrap_servers or settings.KAFKA_BOOTSTRAP_SERVERS,
                "enable.idempotence": True,
            }
        )

    def send(self, post):
        event = {
            "postId": post.id,
            "platform": post.platform,
            "content": post.content,
            "scheduledAt": post.scheduled_at.isoformat(),
        }
        # Keying by post id keeps all events for one post on the same partition.
        self._producer.produce(self.topic, key=str(post.id), value=json.dumps(event))

    def flush(self, timeout=10):
        remaining = self._producer.flush(timeout)
        if remaining:
            raise RuntimeError(f"{remaining} Kafka messages were not delivered")
