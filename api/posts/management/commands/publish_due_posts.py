import logging
import time

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from posts.kafka_producer import DuePostProducer
from posts.models import Post

logger = logging.getLogger(__name__)


def queue_due_posts(producer, batch_size=100):
    """Send every scheduled post whose time has come to Kafka and mark it as queued.

    Returns the number of posts queued.
    """
    with transaction.atomic():
        due_posts = list(
            Post.objects.select_for_update(skip_locked=True)
            .filter(status=Post.Status.SCHEDULED, scheduled_at__lte=timezone.now())
            .order_by("scheduled_at")[:batch_size]
        )
        if not due_posts:
            return 0

        for post in due_posts:
            producer.send(post)
        # Only mark posts as queued once Kafka has confirmed delivery.
        producer.flush()

        Post.objects.filter(id__in=[p.id for p in due_posts]).update(
            status=Post.Status.QUEUED, updated_at=timezone.now()
        )
    return len(due_posts)


class Command(BaseCommand):
    help = "Poll for posts whose scheduled time has passed and publish them to Kafka."

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=int, default=10, help="Seconds between polls.")
        parser.add_argument("--once", action="store_true", help="Run a single poll and exit.")

    def handle(self, *args, **options):
        producer = DuePostProducer()
        while True:
            try:
                count = queue_due_posts(producer)
                if count:
                    logger.info("Queued %d due post(s) to Kafka", count)
            except Exception:
                logger.exception("Failed to queue due posts; will retry on next poll")
            if options["once"]:
                break
            time.sleep(options["interval"])
