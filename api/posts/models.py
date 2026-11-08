from django.db import models


class Post(models.Model):
    class Platform(models.TextChoices):
        X = "x", "X"
        LINKEDIN = "linkedin", "LinkedIn"
        INSTAGRAM = "instagram", "Instagram"
        FACEBOOK = "facebook", "Facebook"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        QUEUED = "queued", "Queued"
        PUBLISHED = "published", "Published"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    content = models.TextField(max_length=2000)
    platform = models.CharField(max_length=20, choices=Platform.choices)
    scheduled_at = models.DateTimeField(db_index=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SCHEDULED, db_index=True
    )
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["scheduled_at"]

    def __str__(self):
        return f"{self.platform} post #{self.pk} ({self.status})"
