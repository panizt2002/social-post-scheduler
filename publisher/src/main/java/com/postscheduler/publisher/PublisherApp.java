package com.postscheduler.publisher;

import java.time.Duration;
import java.util.List;
import java.util.Properties;

import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.common.errors.WakeupException;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Consumes due posts from Kafka, publishes them, and reports the result to the API.
 * Offsets are committed only after a batch is fully handled (at-least-once delivery).
 */
public class PublisherApp {

    private static final Logger log = LoggerFactory.getLogger(PublisherApp.class);

    public static void main(String[] args) {
        String bootstrap = env("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092");
        String topic = env("KAFKA_DUE_POSTS_TOPIC", "posts.due");
        String apiBaseUrl = env("API_BASE_URL", "http://localhost:8000/api/");

        Properties props = new Properties();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrap);
        props.put(ConsumerConfig.GROUP_ID_CONFIG, "post-publisher");
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, "false");
        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");

        PostHandler handler = new PostHandler(
                new SocialPlatformClient(), new PostStatusClient(apiBaseUrl), new RetryPolicy(3, 500));

        KafkaConsumer<String, String> consumer = new KafkaConsumer<>(props);
        Thread mainThread = Thread.currentThread();
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            consumer.wakeup();
            try {
                mainThread.join();
            } catch (InterruptedException ignored) {
                Thread.currentThread().interrupt();
            }
        }));

        try (consumer) {
            consumer.subscribe(List.of(topic));
            log.info("Listening for due posts on topic '{}'", topic);
            while (true) {
                ConsumerRecords<String, String> records = consumer.poll(Duration.ofSeconds(1));
                for (ConsumerRecord<String, String> record : records) {
                    handler.handle(record.value());
                }
                if (!records.isEmpty()) {
                    consumer.commitSync();
                }
            }
        } catch (WakeupException e) {
            log.info("Shutting down publisher");
        }
    }

    private static String env(String name, String defaultValue) {
        String value = System.getenv(name);
        return value == null || value.isBlank() ? defaultValue : value;
    }
}
