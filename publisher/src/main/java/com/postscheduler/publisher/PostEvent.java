package com.postscheduler.publisher;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.databind.ObjectMapper;

/** A post whose scheduled time has arrived, as sent to Kafka by the API service. */
@JsonIgnoreProperties(ignoreUnknown = true)
public record PostEvent(long postId, String platform, String content, String scheduledAt) {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    public static PostEvent fromJson(String json) {
        try {
            PostEvent event = MAPPER.readValue(json, PostEvent.class);
            if (event.postId() <= 0 || event.platform() == null) {
                throw new IllegalArgumentException("Event is missing postId or platform: " + json);
            }
            return event;
        } catch (IllegalArgumentException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalArgumentException("Invalid post event: " + json, e);
        }
    }
}
