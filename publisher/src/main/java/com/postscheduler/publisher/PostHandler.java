package com.postscheduler.publisher;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Handles one due-post message: publish it, then report "published" or "failed". */
public class PostHandler {

    private static final Logger log = LoggerFactory.getLogger(PostHandler.class);

    /** Reports a post's final status; implemented by PostStatusClient in production. */
    @FunctionalInterface
    public interface StatusReporter {
        void updateStatus(long postId, String status) throws Exception;
    }

    private final SocialPlatformClient platform;
    private final StatusReporter statusReporter;
    private final RetryPolicy retry;

    public PostHandler(SocialPlatformClient platform, PostStatusClient statusClient, RetryPolicy retry) {
        this(platform, statusClient::updateStatus, retry);
    }

    public PostHandler(SocialPlatformClient platform, StatusReporter statusReporter, RetryPolicy retry) {
        this.platform = platform;
        this.statusReporter = statusReporter;
        this.retry = retry;
    }

    /** Returns the status that was reported for the post, or null if the message was invalid. */
    public String handle(String message) {
        PostEvent event;
        try {
            event = PostEvent.fromJson(message);
        } catch (IllegalArgumentException e) {
            // A malformed message can never succeed, so skip it instead of blocking the partition.
            log.error("Skipping invalid message: {}", e.getMessage());
            return null;
        }

        String status;
        try {
            retry.execute(() -> platform.publish(event));
            status = "published";
        } catch (Exception e) {
            log.error("Publishing post {} failed after retries", event.postId(), e);
            status = "failed";
        }

        final String finalStatus = status;
        try {
            retry.execute(() -> statusReporter.updateStatus(event.postId(), finalStatus));
        } catch (Exception e) {
            log.error("Could not report status '{}' for post {}", finalStatus, event.postId(), e);
        }
        return status;
    }
}
