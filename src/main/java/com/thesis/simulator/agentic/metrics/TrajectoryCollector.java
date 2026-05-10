package com.thesis.simulator.agentic.metrics;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

/**
 * Simple in-memory trajectory log. Writes to CSV on close.
 * Dynamic columns: discovers all payload keys across all rows,
 * so schema can evolve without breaking compatibility.
 */
public class TrajectoryCollector {

    private final List<Row> rows = new ArrayList<>();

    public void log(String workflowId, String entityId, String eventType,
                    double timeMs, Map<String, Object> payload) {
        rows.add(new Row(workflowId, entityId, eventType, timeMs, new TreeMap<>(payload)));
    }

    public void writeCsv(Path output) throws IOException {
        // Collect every payload key seen, so all rows share the same column set
        Set<String> keys = new TreeSet<>();
        for (Row r : rows) keys.addAll(r.payload.keySet());

        try (var w = Files.newBufferedWriter(output)) {
            w.write("time_ms,workflow_id,entity_id,event_type");
            for (String k : keys) w.write("," + k);
            w.newLine();
            for (Row r : rows) {
                w.write(String.format(java.util.Locale.US, "%.3f,%s,%s,%s",
                        r.timeMs, r.workflowId, r.entityId, r.eventType));
                for (String k : keys) {
                    Object v = r.payload.get(k);
                    w.write("," + (v == null ? "" : v.toString()));
                }
                w.newLine();
            }
        }
    }

    public List<Row> rows() {
        return Collections.unmodifiableList(rows);
    }

    public record Row(String workflowId, String entityId, String eventType,
                      double timeMs, Map<String, Object> payload) {}
}
