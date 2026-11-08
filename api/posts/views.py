from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Post
from .serializers import PostSerializer, PostStatusSerializer


class PostViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    POST   /api/posts/              schedule a post
    GET    /api/posts/?status=...   list posts, optionally filtered by status
    GET    /api/posts/{id}/         get one post
    POST   /api/posts/{id}/cancel/  cancel a scheduled post
    PATCH  /api/posts/{id}/status/  report publish result (used by the publisher service)
    """

    serializer_class = PostSerializer

    def get_queryset(self):
        queryset = Post.objects.all()
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        post = self.get_object()
        if post.status != Post.Status.SCHEDULED:
            return Response(
                {"detail": f"Only scheduled posts can be cancelled (current: {post.status})."},
                status=status.HTTP_409_CONFLICT,
            )
        post.status = Post.Status.CANCELLED
        post.save(update_fields=["status", "updated_at"])
        return Response(PostSerializer(post).data)

    @action(detail=True, methods=["patch"], url_path="status")
    def update_status(self, request, pk=None):
        post = self.get_object()
        if post.status != Post.Status.QUEUED:
            return Response(
                {"detail": f"Post is not queued for publishing (current: {post.status})."},
                status=status.HTTP_409_CONFLICT,
            )
        serializer = PostStatusSerializer(post, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(PostSerializer(post).data)
