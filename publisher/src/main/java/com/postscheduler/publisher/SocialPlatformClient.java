package com.postscheduler.publisher;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Simulates publishing to a social network. A real implementation would call
 * the platform's API (X, LinkedIn, ...) here.
 */
public class SocialPlatformClient {

    private static final Logger log = LoggerFactory.getLogger(SocialPlatformClient.class);

    public void publish(PostEvent event) {
        if (event.content() == null || event.content().isBlank()) {
            throw new IllegalStateException("Cannot publish an empty post " + event.postId());
        }
        log.info("Published post {} to {}: \"{}\"", event.postId(), event.platform(), event.content());
    }
}
