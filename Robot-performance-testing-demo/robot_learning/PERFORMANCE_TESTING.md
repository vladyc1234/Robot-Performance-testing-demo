# Performance testing with Robot Framework and Python

Run from the project root:

```powershell
.\.venv\Scripts\python.exe robot_learning/run_examples.py performance
```

No new dependencies are required. The HTTP suite starts and stops its own local mock.
The command also runs `tests/performance_theory.robot`, the six lessons below.
It is an explicit option; `all` continues to select functional suites only.

## Theory: what performance testing is and why it matters

Performance testing evaluates how quickly and reliably a system completes work
under a defined workload, and how its resource use changes. A functional test asks
whether an order can be read correctly. A performance test asks whether orders
remain correct and fast enough when many people read them, when data grows, or
when the service has been running for a long time.

It helps detect slow user journeys, capacity limits, expensive resource use and
regressions before they affect users. A fast error is not a successful response:
always check correctness, latency and error rate together. Measure throughput
(completed work per second) and, in a real system, CPU, memory, disk I/O, network,
connections and queues. Measurements need a stated environment and workload to
be meaningful; a laptop result is not a production capacity estimate.

## Performance-testing process

1. **Define the question and success criteria.** For example: can the expected
   checkout traffic meet p95 <= 500 ms with error rate below 1%? These are example
   targets, not universal requirements. Agree on budgets before running tests.
2. **Understand the system and environment.** Record versions, hardware, resource
   limits, dependencies, network and monitoring. Identify important user journeys.
3. **Design the workload.** Specify concurrent users or arrival rate, request mix,
   think time, data size, warm-up, duration, load transitions and recovery period.
   Ten concurrent users does not mean ten requests per second.
4. **Prepare data and instrumentation.** Use representative data, reproducible
   setup, correctness checks and server/client metrics. Separate setup from timing.
5. **Establish a baseline, then execute the experiment.** Start small, check the
   generator is behaving correctly, and change one main variable at a time.
   Define stopping criteria for overload experiments and retain failed samples.
6. **Analyze the time series and bottlenecks.** Compare percentiles, successful
   throughput, errors and resource use. Correlation suggests what to investigate;
   rising latency alone does not prove a database problem.
7. **Improve, repeat and report.** Re-run comparable workloads after a change,
   repeat noisy measurements and document limits, regressions and recovery.

## Six runnable theory lessons

Run just these lessons from the project root:

```powershell
.\.venv\Scripts\python.exe -m robot --outputdir robot_learning/results/theory robot_learning/tests/performance_theory.robot
```

Read each `Demonstrate ... Testing` keyword in `libraries/PerformanceLibrary.py`
alongside its Robot test. Comments explain the setup, measured work and assertions.
Each lesson writes a `lesson-*.json` file into the selected output directory.

| Type | Question | Implemented experiment | What to inspect |
| --- | --- | --- | --- |
| Load | Does expected traffic meet its budget? | Two clients use two processing slots | p95, errors and successful requests/second |
| Stress | What happens beyond capacity, and does normal service recover? | 2, 4, 8, then 2 clients against two slots | Overload failures and final recovery |
| Soak (endurance) | Does sustained load degrade service over time? | Two clients repeatedly run measured windows for two seconds | Per-window latency, throughput and errors |
| Spike | What happens when demand jumps suddenly? | 1, 8, then 1 client against two slots | Burst failures and recovery after the drop |
| Volume | How does more data affect the same operation? | One reader scans 1,000, 10,000 and 100,000 rows | Correct count and scan duration |
| Scalability | How does adding resources affect a fixed workload? | Four clients use 1, 2 and 4 slots | Successful throughput, speedup and efficiency |

**Load:** choose traffic representative of ordinary and expected peak use. Passing
our two-client example only means this tiny workload met a teaching budget; it
does not establish how many real customers an application supports.

**Stress:** deliberately exceed the expected operating range. A useful result can
include errors, provided they are recorded and recovery is evaluated. This toy
rejects work when all slots are busy, so overload is visible without exhausting
your computer. Real systems may queue, time out, fail dependencies or crash.

**Soak:** duration is the distinguishing variable. Real soak tests run for hours
or days to expose memory leaks, resource exhaustion and gradual degradation. The
two-second example teaches collecting consecutive windows, with short gaps for
worker setup between them. It has no persistent leaking state or resource monitor
and cannot establish endurance. The final window completes even if the requested
duration has elapsed. The demo duration is bounded to 30 seconds.

**Spike:** the distinguishing feature is a sudden change rather than a gradual
increase. This lesson jumps directly to eight clients and then returns to one.
Stages fully drain and use fresh workers, so this is a workload-shape example,
not a test of a persistent backlog or a live autoscaler's recovery time.

**Volume:** increase data, keeping concurrency and the operation fixed. The lesson
creates an actual list, warms up the scan, then measures ten scans and checks each
answer. Setup time is excluded. A full scan generally does more work as data grows,
but small timings are noisy; the test does not assert a strict timing ordering.
For a real database, also examine indexes, query plans, storage and data distribution.

**Scalability:** compare workload and resources explicitly. Here workload stays at
four clients while processing slots increase. Speedup is successful throughput
divided by the one-slot baseline; efficiency is speedup divided by the slot count.
An ideal proportional improvement would give efficiency near 1. Scheduling and
small samples can distort these values. Other experiments increase workload at
fixed resources, or increase both to check whether response times remain stable.
More slots here only simulate capacity; they are not real CPUs or deployed replicas.

The concurrency lessons use threads and a semaphore (a limited set of processing
slots). Accepted requests simulate I/O with a short sleep; rejected requests are
counted as failures, followed by client backoff. Latency includes each attempt,
while total wall time also includes backoff. Percentiles include fast rejections,
so read them together with error rate and successful throughput. These bounded
examples illustrate mechanics; use the HTTP experiments below to measure real
local request/response traffic. Neither set replaces a production load test.

Expected overload makes the stress and spike lessons **pass** when they detect
failures and verify normal stages meet the budget. Their green Robot status does
not mean that overloaded requests succeeded. Timing budgets are intentionally
generous teaching defaults, and even these can fail on a heavily loaded machine.

Start with `tests/api_performance.robot`, then read `libraries/PerformanceLibrary.py`.
Robot controls setup, workload selection, assertions and reports. A Python keyword
generates concurrent HTTP traffic. A plain Robot FOR loop of GET keywords would
issue requests sequentially, not simulate simultaneous clients.

## Four HTTP experiments

| Example | Workload | What to learn |
| --- | --- | --- |
| Single User Baseline | 1 worker x 40 requests | Establish a latency baseline |
| Four Concurrent Users | 4 workers x 40 requests | Observe latency and throughput under competing requests |
| Compare Increasing Concurrency | Separate 1, 2, 4 worker stages; 30 requests per worker | Compare behavior as concurrency increases |
| Fast Errors Must Not Count As Success | Invalid token; 2 workers x 10 requests | Verify a fast HTTP 401 still fails a success budget |

The last Robot test passes only if it observes all 20 failures and verifies that
the budget keyword rejects the result. It is a check of the measuring tool, not
a claim that the API served those requests successfully.

Each worker owns a separate requests.Session. It performs one warm-up request,
waits at a barrier, then sends requests sequentially without think time. All
workers start the measured phase at the barrier release. Requests have connect
and read timeouts, with no application retry hiding errors. Timeouts count as
failed samples. Requests timeouts are not a total wall-clock deadline.

## Read the metrics

Open `results/performance/report.html` and `log.html`. JSON files in the same
directory contain both summary metrics and raw request samples:

- `baseline.json` and `concurrent.json`
- `stage-1.json`, `stage-2.json`, `stage-4.json`
- `expected-errors.json`

| Metric | Meaning |
| --- | --- |
| mean_ms | Average observed request duration |
| p50_ms | Median using the nearest-rank method |
| p95_ms | At least 95% of samples have a duration at or below this value |
| max_ms | Slowest observed attempt |
| throughput_rps | Completed attempts, including failures, divided by measured wall time |
| successful_rps | Successful attempts divided by measured wall time |
| error_rate | Failed attempts / all attempts; 0.01 means 1% |

Latency includes the client HTTP call and complete body download. JSON validation
happens afterward and is excluded from individual latency, but included in total
workload duration. Percentiles include failed attempts as well as successful ones;
inspect their error labels rather than treating a fast failure as good performance.
Only status 200 with an empty orders list and total zero counts as success here.
Every test resets the mock, and the performance workload is read-only.

For 100 sorted samples, nearest-rank p95 is sample number 95. An average alone can
hide a small group of very slow requests. These small datasets teach the method;
they are too small for a stable estimate of rare tail behavior such as p99.9.

## Budgets and interpretation

The teaching budget is p95 <= 1500 ms and zero failures. This is deliberately not
a business SLA. Define real thresholds from user needs, endpoint criticality,
expected traffic and an agreed environment, before examining the results.

Override the latency budget through Robot:

```powershell
.\.venv\Scripts\python.exe -m robot --variable MAX_P95_MS:100 --outputdir robot_learning/results/performance-strict robot_learning/tests/api_performance.robot
```

A stricter budget may fail on your machine. Read the latency and error samples to
understand why rather than raising the threshold just to obtain a green report.

If concurrency rises but throughput plateaus while latency grows, investigate
contention or resource saturation. Our orders mock locks its shared state and
writes responses while holding that lock; this can serialize work. But do not
diagnose a bottleneck from those metrics alone: capture CPU, memory, connection
counts, server traces, and load-generator utilization to test the hypothesis.

## Interview topics and limits

- **Load:** expected traffic with a defined user mix and duration.
- **Stress:** increase beyond expected capacity to find saturation and recovery.
- **Spike:** sudden traffic increase, followed by recovery checks.
- **Soak:** sustained traffic long enough to expose leaks or gradual degradation.

The HTTP tests are short baseline/concurrency experiments; the separate theory
suite demonstrates the other workload shapes with a toy service. Both use a
closed-loop model: each worker waits for its
response before sending its next request. Four workers means at most four requests
in flight, not four requests per second. When responses slow down, the generator
also sends less traffic. It cannot model a fixed external arrival rate and may
under-represent overload that an open-loop arrival model would reveal.

The mock and generator share one Python process and one computer. There is no
database, TLS or realistic network path, and the mock's default HTTP/1.0 response
handling closes connections. A client Session therefore does not make this a
benchmark of persistent connections. Results describe this local experiment only.

For an interview, explain workload shape, data volume, warm-up, sample size,
percentiles, error criteria, monitoring and repeatability before discussing a
single requests-per-second number. More threads do not automatically mean a
better or more representative test.

## Exercises

1. Compare JSON metrics for stages 1, 2 and 4. Explain whether throughput scales.
2. Add a controlled server delay and predict how latency and throughput change.
3. Seed a large number of orders, adapt the response validator and compare list
   endpoint behavior. Explain why a tiny empty dataset is not representative.
4. Add a mixed read/create workload using unique idempotency keys, and report
   endpoint-specific percentiles instead of combining unrelated operations.
5. Design an arrival-rate experiment and a longer soak experiment, specifying
   monitoring, stopping criteria and expected recovery before implementation.

## Implementation references

- [Python ThreadPoolExecutor](https://docs.python.org/3/library/concurrent.futures.html)
- [Requests timeouts](https://requests.readthedocs.io/en/latest/user/quickstart/#timeouts)
