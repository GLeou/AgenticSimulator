package com.thesis.simulator.agentic.scheduler;

import com.thesis.simulator.agentic.events.AgenticEvent;

import java.util.PriorityQueue;
import java.util.function.Consumer;

/**
 * Minimal priority-queue event loop.
 * The only contract is:
 *   - schedule(event) inserts by event.timeMs()
 *   - run(handler) drains the queue, calling handler for each event in time order.
 */
public class EventScheduler {

    private final PriorityQueue<AgenticEvent> queue = new PriorityQueue<>();
    private double now = 0.0;

    public void schedule(AgenticEvent ev) {
        if (ev.timeMs() < now) {
            throw new IllegalStateException(
                    "Cannot schedule event in the past: t=" + ev.timeMs() + " now=" + now);
        }
        queue.offer(ev);
    }

    public void run(Consumer<AgenticEvent> handler) {
        while (!queue.isEmpty()) {
            AgenticEvent ev = queue.poll();
            now = ev.timeMs();
            handler.accept(ev);
        }
    }

    public double now() {
        return now;
    }
}
