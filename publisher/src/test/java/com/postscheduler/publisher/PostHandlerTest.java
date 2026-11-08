package com.postscheduler.publisher;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.util.ArrayList;
import java.util.List;

import org.junit.jupiter.api.Test;

class PostHandlerTest {

    private final List<String> reported = new ArrayList<>();
    private final PostHandler handler = new PostHandler(
            new SocialPlatformClient(),
            (postId, status) -> reported.add(postId + ":" + status),
            new RetryPolicy(3, 1));

    @Test
    void publishesValidPostAndReportsPublished() {
        String status = handler.handle(
                "{\"postId\":7,\"platform\":\"x\",\"content\":\"Hello\",\"scheduledAt\":\"2026-11-08T10:00:00Z\"}");
        assertEquals("published", status);
        assertEquals(List.of("7:published"), reported);
    }

    @Test
    void reportsFailedWhenPostCannotBePublished() {
        String status = handler.handle("{\"postId\":8,\"platform\":\"x\",\"content\":\"\"}");
        assertEquals("failed", status);
        assertEquals(List.of("8:failed"), reported);
    }

    @Test
    void skipsMalformedMessage() {
        assertNull(handler.handle("not json"));
        assertNull(handler.handle("{\"platform\":\"x\"}"));
        assertEquals(List.of(), reported);
    }

    @Test
    void retriesStatusReportUntilItSucceeds() {
        int[] calls = {0};
        PostHandler flaky = new PostHandler(new SocialPlatformClient(), (postId, status) -> {
            if (++calls[0] < 3) {
                throw new RuntimeException("API temporarily unavailable");
            }
        }, new RetryPolicy(3, 1));

        flaky.handle("{\"postId\":9,\"platform\":\"linkedin\",\"content\":\"Hi\"}");
        assertEquals(3, calls[0]);
    }

    @Test
    void retryPolicyGivesUpAfterMaxAttempts() {
        RetryPolicy retry = new RetryPolicy(2, 1);
        int[] calls = {0};
        assertThrows(RuntimeException.class, () -> retry.execute(() -> {
            calls[0]++;
            throw new RuntimeException("boom");
        }));
        assertEquals(2, calls[0]);
    }
}
