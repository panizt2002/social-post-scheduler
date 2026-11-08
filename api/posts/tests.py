from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from posts.management.commands.publish_due_posts import queue_due_posts
from posts.models import Post


class FakeProducer:
    def __init__(self, fail_on_flush=False):
        self.sent = []
        self.fail_on_flush = fail_on_flush

    def send(self, post):
        self.sent.append(post.id)

    def flush(self, timeout=10):
        if self.fail_on_flush:
            raise RuntimeError("Kafka unavailable")


def make_post(minutes_from_now, status=Post.Status.SCHEDULED):
    return Post.objects.create(
        content="Hello world",
        platform=Post.Platform.LINKEDIN,
        scheduled_at=timezone.now() + timedelta(minutes=minutes_from_now),
        status=status,
    )


class PostApiTests(APITestCase):
    def test_create_post(self):
        response = self.client.post(
            "/api/posts/",
            {
                "content": "Launching our new feature!",
                "platform": "x",
                "scheduled_at": (timezone.now() + timedelta(hours=1)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "scheduled")

    def test_rejects_post_scheduled_in_the_past(self):
        response = self.client.post(
            "/api/posts/",
            {
                "content": "Too late",
                "platform": "x",
                "scheduled_at": (timezone.now() - timedelta(minutes=5)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("scheduled_at", response.data)

    def test_rejects_unknown_platform(self):
        response = self.client.post(
            "/api/posts/",
            {
                "content": "Hi",
                "platform": "myspace",
                "scheduled_at": (timezone.now() + timedelta(hours=1)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_list_filters_by_status(self):
        make_post(10)
        make_post(10, status=Post.Status.PUBLISHED)
        response = self.client.get("/api/posts/?status=published")
        self.assertEqual(response.data["count"], 1)

    def test_cancel_scheduled_post(self):
        post = make_post(10)
        response = self.client.post(f"/api/posts/{post.id}/cancel/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "cancelled")

    def test_cannot_cancel_published_post(self):
        post = make_post(10, status=Post.Status.PUBLISHED)
        response = self.client.post(f"/api/posts/{post.id}/cancel/")
        self.assertEqual(response.status_code, 409)

    def test_publisher_marks_queued_post_published(self):
        post = make_post(-1, status=Post.Status.QUEUED)
        response = self.client.patch(
            f"/api/posts/{post.id}/status/", {"status": "published"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        post.refresh_from_db()
        self.assertEqual(post.status, Post.Status.PUBLISHED)
        self.assertIsNotNone(post.published_at)

    def test_status_update_rejected_when_not_queued(self):
        post = make_post(10)
        response = self.client.patch(
            f"/api/posts/{post.id}/status/", {"status": "published"}, format="json"
        )
        self.assertEqual(response.status_code, 409)


class QueueDuePostsTests(APITestCase):
    def test_only_due_posts_are_queued(self):
        due = make_post(-1)
        future = make_post(60)
        cancelled = make_post(-1, status=Post.Status.CANCELLED)

        producer = FakeProducer()
        count = queue_due_posts(producer)

        self.assertEqual(count, 1)
        self.assertEqual(producer.sent, [due.id])
        due.refresh_from_db()
        future.refresh_from_db()
        cancelled.refresh_from_db()
        self.assertEqual(due.status, Post.Status.QUEUED)
        self.assertEqual(future.status, Post.Status.SCHEDULED)
        self.assertEqual(cancelled.status, Post.Status.CANCELLED)

    def test_posts_stay_scheduled_when_kafka_fails(self):
        post = make_post(-1)
        with self.assertRaises(RuntimeError):
            queue_due_posts(FakeProducer(fail_on_flush=True))
        post.refresh_from_db()
        self.assertEqual(post.status, Post.Status.SCHEDULED)
