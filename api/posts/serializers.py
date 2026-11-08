from django.utils import timezone
from rest_framework import serializers

from .models import Post


class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = [
            "id",
            "content",
            "platform",
            "scheduled_at",
            "status",
            "published_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["status", "published_at", "created_at", "updated_at"]

    def validate_scheduled_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("scheduled_at must be in the future.")
        return value


class PostStatusSerializer(serializers.ModelSerializer):
    """Used by the publisher service to report the result of a publish attempt."""

    class Meta:
        model = Post
        fields = ["status"]

    def validate_status(self, value):
        if value not in (Post.Status.PUBLISHED, Post.Status.FAILED):
            raise serializers.ValidationError("status must be 'published' or 'failed'.")
        return value

    def update(self, instance, validated_data):
        instance.status = validated_data["status"]
        if instance.status == Post.Status.PUBLISHED:
            instance.published_at = timezone.now()
        instance.save(update_fields=["status", "published_at", "updated_at"])
        return instance
