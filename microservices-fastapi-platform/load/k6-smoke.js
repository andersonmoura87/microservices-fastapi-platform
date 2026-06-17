import http from "k6/http";
import { check, sleep } from "k6";
import { Counter } from "k6/metrics";

// Drive load through the gateway. Override with: k6 run -e BASE_URL=... load/k6-smoke.js
const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

const ingestErrors = new Counter("ingest_errors");

export const options = {
  scenarios: {
    ramping: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "30s", target: 20 },
        { duration: "1m", target: 20 },
        { duration: "30s", target: 0 },
      ],
    },
  },
  // Thresholds encode the SLOs — k6 exits non-zero if they are breached,
  // which is what makes this usable as a gate in CI.
  thresholds: {
    http_req_failed: ["rate<0.01"], // < 1% errors
    http_req_duration: ["p(95)<300"], // p95 < 300ms
    ingest_errors: ["count<10"],
  },
};

export default function () {
  // Write path: ingest a record through the gateway.
  const payload = JSON.stringify({
    key: `k6-${__VU}-${__ITER}`,
    payload: { source: "k6", ts: Date.now() },
  });
  const ingest = http.post(`${BASE_URL}/data/ingest`, payload, {
    headers: { "Content-Type": "application/json" },
  });
  if (!check(ingest, { "ingest 201": (r) => r.status === 201 })) {
    ingestErrors.add(1);
  }

  // Read path: list records (served from Redis cache after the first miss).
  const list = http.get(`${BASE_URL}/data/records`);
  check(list, { "list 200": (r) => r.status === 200 });

  sleep(1);
}
