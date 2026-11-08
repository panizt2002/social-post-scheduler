package com.postscheduler.publisher;

/** Retries an action with exponential backoff (e.g. 500 ms, 1 s, 2 s). */
public class RetryPolicy {

    @FunctionalInterface
    public interface Action {
        void run() throws Exception;
    }

    private final int maxAttempts;
    private final long initialDelayMs;

    public RetryPolicy(int maxAttempts, long initialDelayMs) {
        if (maxAttempts < 1) {
            throw new IllegalArgumentException("maxAttempts must be at least 1");
        }
        this.maxAttempts = maxAttempts;
        this.initialDelayMs = initialDelayMs;
    }

    public void execute(Action action) throws Exception {
        long delay = initialDelayMs;
        for (int attempt = 1; ; attempt++) {
            try {
                action.run();
                return;
            } catch (Exception e) {
                if (attempt >= maxAttempts) {
                    throw e;
                }
                Thread.sleep(delay);
                delay *= 2;
            }
        }
    }
}
