"""Small, closed-loop localhost load generator, exposed as Robot keywords.

Workers use separate Sessions and never call Robot APIs from worker threads.
This teaches measurement, not distributed load generation or capacity planning.

THEORY: Performance testing measures speed, throughput, reliability and resource
use under a defined workload. Correct output alone is insufficient if users wait
too long or requests fail during busy periods. See PERFORMANCE_TESTING.md for the
process, metrics and interpretation of all six runnable lessons below.

Load = expected traffic; stress = beyond capacity; soak = sustained traffic;
spike = an abrupt traffic change; volume = more data; scalability = how behavior
changes when workload and/or resources grow. These are different test questions.

PROCESS: agree on response-time/error budgets; describe the environment and user
journeys; choose traffic, data and duration; prepare data and monitoring; warm up
and establish a baseline; run the workload; analyze latency, successful throughput,
errors and resources; fix bottlenecks and repeat under comparable conditions.
"""
import json
import math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import mean
from threading import Barrier, BoundedSemaphore
from time import perf_counter, sleep
from urllib.parse import urlparse

import requests
from robot.api import logger
from robot.api.deco import keyword, library


@library(auto_keywords=False)
class PerformanceLibrary:
    @staticmethod
    def _demo_stage(users, capacity, requests_per_user=10):
        """Measure a toy service with a finite number of processing slots.

        Each client sends requests sequentially (closed-loop traffic). A full
        service rejects immediately; successful work takes about 5 ms. Real
        services might queue, time out or autoscale instead. Threads overlap
        waiting work here; this is not a CPU parallelism benchmark.
        """
        slots = BoundedSemaphore(capacity)
        barrier = Barrier(users + 1)

        def client():
            samples = []
            barrier.wait(timeout=15)
            for _ in range(requests_per_user):
                started = perf_counter()
                accepted = slots.acquire(timeout=0.2)
                if accepted:
                    try:
                        sleep(0.005)  # Simulated I/O, not a measured real API.
                    finally:
                        slots.release()
                samples.append({"latency_ms": (perf_counter() - started) * 1000,
                                "error": None if accepted else "capacity_exceeded"})
                if not accepted:
                    sleep(0.005)  # Client backoff is outside response latency.
            return samples

        with ThreadPoolExecutor(max_workers=users) as pool:
            futures = [pool.submit(client) for _ in range(users)]
            started = perf_counter()
            barrier.wait(timeout=15)
            samples = [sample for future in futures for sample in future.result()]
            duration = perf_counter() - started
        latencies = sorted(sample["latency_ms"] for sample in samples)
        failures = sum(sample["error"] is not None for sample in samples)
        return {"metrics": {
            "users": users, "capacity": capacity, "requests": len(samples),
            "failures": failures, "error_rate": failures / len(samples),
            "duration_seconds": duration, "throughput_rps": len(samples) / duration,
            "successful_rps": (len(samples) - failures) / duration,
            "mean_ms": mean(latencies),
            "p95_ms": latencies[math.ceil(0.95 * len(latencies)) - 1],
        }, "samples": samples}

    @keyword
    def demonstrate_load_testing(self):
        """Expected load: two concurrent clients fit in two service slots.

        What it does: measures behavior at ordinary and expected peak traffic.
        Why it matters: a function can be correct for one user but too slow for
        everyday traffic. Load testing checks whether user-facing performance
        goals remain achievable under the workload the business expects.

        Inspect p95, successful throughput and errors together. A real load test
        also needs a representative request mix, think time and business budget.
        """
        return self._demo_stage(users=20, capacity=3)

    @keyword
    def demonstrate_stress_testing(self):
        """Increase demand beyond two slots, then return to normal load.

        What it does: pushes demand beyond the normal operating range to observe
        saturation, failure behavior and recovery when demand decreases.
        Why it matters: reveals capacity limits and whether overload is handled
        predictably. It helps plan headroom and exposes failures that ordinary
        load testing may never trigger.

        Keep overloaded stages even when their budget fails: those failures are
        evidence of the limit. The final stage checks recovery after overload.
        Stages drain fully; this does not model a persistent queue or crash.
        """
        return [{"phase": phase, **self._demo_stage(users, capacity=3)}
                for phase, users in [("normal", 20), ("above_capacity", 40),
                                     ("higher_stress", 80), ("recovery", 20)]]

    @keyword
    def demonstrate_soak_testing(self, duration_seconds: float = 2):
        """Repeat stable load and retain time windows to inspect for drift.

        What it does: holds a representative workload for an extended period,
        comparing behavior and resource consumption as time passes.
        Why it matters: memory leaks, unclosed connections, growing queues and
        other accumulating problems may remain invisible in short tests. A fast
        start does not guarantee stable service throughout a working day.

        Two seconds only demonstrates the method. Real soak tests run for hours
        or days and track memory, handles, connections and latency over time.
        This stateless toy has no leak; stable results do not prove leak freedom.
        """
        if not math.isfinite(duration_seconds) or not 0 < duration_seconds <= 30:
            raise ValueError("Use a demo duration greater than 0 and at most 30 seconds")
        started = perf_counter()
        windows = []
        while perf_counter() - started < duration_seconds:
            offset = perf_counter() - started
            result = self._demo_stage(users=20, capacity=3)
            windows.append({"offset_seconds": offset, **result})
        # Finish the last window, so actual elapsed time may exceed the target.
        return windows

    @keyword
    def demonstrate_spike_testing(self):
        """Jump directly from one client to eight, then back to one.

        What it does: applies an abrupt increase or decrease in traffic and
        observes responses during the transition and afterward.
        Why it matters: launches, flash sales or synchronized clients can create
        bursts that gradual load ramps miss. It checks whether buffering,
        rejection policies and, in a real system, scaling react quickly enough.

        Compare the spike's errors with the recovery stage. Unlike stress, this
        lesson skips intermediate load levels. Each stage starts fresh workers;
        it illustrates workload shape, not a continuous live traffic transition.
        """
        return [{"phase": phase, **self._demo_stage(users, capacity=3)}
                for phase, users in [("before", 20), ("spike", 200), ("recovery", 20)]]

    @keyword
    def demonstrate_volume_testing(self):
        """Keep one reader and the same operation; increase stored row count.

        What it does: grows stored or processed data while keeping other workload
        factors comparable, checking both processing time and correct results.
        Why it matters: a query that works well on a tiny test dataset may become
        slow or run out of memory as customer history grows. Volume tests expose
        data-size effects even when the number of concurrent users stays small.

        Count even IDs by scanning all rows. Data creation and one warm-up scan
        are outside the measured region. Real examples include growing a table,
        file or payload while checking correctness as well as elapsed time.
        """
        results = []
        for row_count in (1000, 10_000, 100_000):
            rows = list(range(row_count))

            def count_even_rows():
                return sum(row % 2 == 0 for row in rows)

            count_even_rows()  # Warm the operation before collecting samples.
            latencies = []
            for _ in range(10):
                started = perf_counter()
                matched = count_even_rows()
                latencies.append((perf_counter() - started) * 1000)
                if matched != row_count // 2:
                    raise AssertionError("The scan returned an incorrect count")
            results.append({"rows": row_count, "matched": matched,
                            "readers": 1, "samples_ms": latencies,
                            "mean_ms": mean(latencies)})
        # No timing-order assertion: OS scheduling can make a small scan noisy.
        return results

    @keyword
    def demonstrate_scalability_testing(self):
        """Hold four clients fixed and compare one, two and four service slots.

        What it does: compares performance as workload and/or resources change,
        explicitly recording which variable changed and by how much.
        Why it matters: adding hardware or replicas does not guarantee matching
        capacity gains. Shared locks and other bottlenecks can limit improvement;
        this testing helps evaluate growth plans and resource cost effectiveness.

        Successful throughput matters: rejected requests can otherwise make a
        small service appear fast. More slots model more processing resources;
        this is not deployment of real replicas or proof of linear scaling.
        """
        results = [self._demo_stage(users=40, capacity=capacity)
                   for capacity in (3, 6, 8, 20)]
        baseline = results[0]["metrics"]["successful_rps"]
        baseline_capacity = results[0]["metrics"]["capacity"]
        for result in results:
            metrics = result["metrics"]
            metrics["throughput_speedup"] = metrics["successful_rps"] / baseline
            metrics["scaling_efficiency"] = (
                metrics["throughput_speedup"] / (metrics["capacity"] / baseline_capacity))
        return results

    @keyword
    def measure_order_reads(self, base_url: str, users: int = 1,
                            requests_per_user: int = 20,
                            token: str = "alice-token"):
        """Measure full GET + body download time. Warm-up is not measured.

        A successful request must return 200 and a valid empty orders response.
        Use immediately after Reset Interview Data; this workload never writes.
        """
        parsed = urlparse(base_url)
        if parsed.scheme != "http" or parsed.hostname != "127.0.0.1":
            raise ValueError("This learning workload targets the local mock only")
        if not 1 <= users <= 8 or not 1 <= requests_per_user <= 200:
            raise ValueError("Use 1..8 users and 1..200 requests per user")
        url = base_url.rstrip("/") + "/orders"
        timing = {}

        def mark_start():
            timing["started"] = perf_counter()

        barrier = Barrier(users + 1, action=mark_start)

        def worker():
            samples = []
            with requests.Session() as session:
                session.trust_env = False  # Local traffic does not need proxies.
                session.headers["Authorization"] = f"Bearer {token}"
                try:
                    # Prime client/server paths without counting warm-up latency.
                    with session.get(url, timeout=(2, 2)):
                        pass
                    barrier.wait(timeout=15)
                except Exception:
                    barrier.abort()
                    raise
                for _ in range(requests_per_user):
                    started = perf_counter()
                    status = None
                    error = None
                    try:
                        with session.get(url, timeout=(2, 2)) as response:
                            elapsed_ms = (perf_counter() - started) * 1000
                            status = response.status_code
                            if status != 200:
                                error = f"HTTP {status}"
                            else:
                                try:
                                    body = response.json()
                                    if (not isinstance(body, dict)
                                            or body.get("items") != []
                                            or body.get("total") != 0):
                                        error = "Unexpected response body"
                                except ValueError:
                                    error = "Invalid JSON response"
                    except requests.RequestException as exc:
                        elapsed_ms = (perf_counter() - started) * 1000
                        error = type(exc).__name__
                    samples.append({"latency_ms": elapsed_ms, "status": status, "error": error})
            return samples

        with ThreadPoolExecutor(max_workers=users) as pool:
            futures = [pool.submit(worker) for _ in range(users)]
            barrier.wait(timeout=15)
            samples = [sample for future in futures for sample in future.result()]
            duration = perf_counter() - timing["started"]

        latencies = sorted(sample["latency_ms"] for sample in samples)
        failures = sum(sample["error"] is not None for sample in samples)

        def percentile(percent):
            # Nearest-rank percentile, explicitly defined for reproducibility.
            return latencies[max(0, math.ceil(percent * len(latencies)) - 1)]

        metrics = {
            "users": users, "requests": len(samples), "failures": failures,
            "error_rate": failures / len(samples), "duration_seconds": duration,
            "throughput_rps": len(samples) / duration,
            "successful_rps": (len(samples) - failures) / duration,
            "mean_ms": mean(latencies), "p50_ms": percentile(0.50),
            "p95_ms": percentile(0.95), "max_ms": max(latencies),
        }
        logger.info(json.dumps(metrics, indent=2))
        return {"metrics": metrics, "samples": samples}

    @keyword
    def save_performance_result(self, result, path: str):
        """Save a single measurement or a list of lesson stages as JSON."""
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, indent=2), encoding="utf-8")

    @keyword
    def performance_should_meet_budget(self, result: dict,
                                       max_p95_ms: float = 1500,
                                       max_error_rate: float = 0.1):
        """Example thresholds, not a production SLA. Error rate is a fraction."""
        metrics = result["metrics"]
        if metrics["error_rate"] > max_error_rate:
            raise AssertionError(f"Error rate {metrics['error_rate']:.1%} exceeds {max_error_rate:.1%}")
        if metrics["p95_ms"] > max_p95_ms:
            raise AssertionError(f"p95 {metrics['p95_ms']:.1f} ms exceeds {max_p95_ms} ms")
