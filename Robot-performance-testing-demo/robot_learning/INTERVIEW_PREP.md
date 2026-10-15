# API interview practice: orders service

Run from the project root:

```powershell
.\.venv\Scripts\python.exe robot_learning/run_examples.py interview
```

Read `tests/api_interview.robot` alongside `libraries/InterviewService.py`.
Results appear in `results/interview/report.html` and `log.html`. No new packages
or browser are needed beyond the existing requirements. The beginner service
remains separate so you can compare simple and advanced examples.

## The API contract in this exercise

These are deliberate mock API design choices, not universal rules for all APIs.

| Request | Contract |
| --- | --- |
| POST /orders | JSON with exactly `sku: "BOOK"` and integer `quantity: 1..5`; requires Idempotency-Key |
| GET /orders/{id} | Only the owner can read it; pending becomes confirmed after a simulated delay |
| GET /orders?page=1&size=2 | Owner's orders in creation order; page >= 1, size 1..3; returns items and total |

Send `Authorization: Bearer alice-token` or `Bearer bob-token`. These are fake
identities for exercising access-control behavior, not secure authentication.
Missing or unrecognized tokens return 401. Reading another owner's order returns
403. Some real APIs use 404 instead to conceal existence; test the agreed contract.

Malformed JSON gives 400, unsupported media type gives 415, and invalid order data
gives 422. New orders return 201 and Location. Same user + same idempotency key +
same payload returns 200 with the same order and Idempotency-Replayed: true.
Changing the payload while reusing the key returns 409 without changing the order.
The key is scoped per user, so Alice and Bob can use the same key independently.

## What to explain in an interview

| Scenario | What your assertions establish | Discussion question |
| --- | --- | --- |
| Response contract | Required fields, types, allowed status, content type and Location | Why is checking only 200 insufficient? |
| Authentication and ownership | Anonymous gets 401, another user gets 403, owner gets 200 | How do authentication and authorization differ? |
| Idempotent retry | Replaying a POST produces the same order and count stays one | How do you retry after a client timeout without duplicating checkout? |
| Conflicting retry | Same key with changed quantity returns 409; stored quantity stays unchanged | Why should we verify persisted state after a rejected request? |
| User-scoped keys | Matching keys do not expose or reuse another user's order | What belongs in an idempotency key's server-side scope? |
| Pagination | Exact ID sequence matches; no omissions, duplicates or other users' data | What happens if new data arrives between offset-based page reads? |
| Boundary/type validation | Reject 0, 6, -1, fractions, true, null and string "2"; accept 1 and 5 | Why test both invalid and valid boundaries? |
| Polling | Create once, then read until confirmed within a bounded retry window | How do you test eventual consistency without fixed sleeps? |

Use this answer structure: describe the risk, arrange controlled data, perform
the request, assert the response and resulting state, and explain cleanup.

For example: “If a checkout client times out, the order might already exist. I
would replay the request with the same idempotency key, verify that it returns the
same order ID, and check that the order count remains one. I would also test a
changed payload, a different user, concurrent retries, and key expiry.”

## Trace a reusable keyword

```robotframework
${retry}=    Create Order    alice    checkout-42    expected=200
```

`Create Order` is defined under `*** Keywords ***`. `alice` selects the HTTP
session; `checkout-42` is the idempotency header value. The keyword constructs a
JSON dictionary, sends POST, checks the expected status and returns the response
with `RETURN`. Named arguments let negative tests reuse the request construction
without weakening assertions.

```robotframework
Wait Until Keyword Succeeds    3 seconds    100 milliseconds
...    Order Should Be Confirmed    ${created.headers}[Location]
```

This retries the read-and-assert keyword until it succeeds or the retry window
expires. It does not retry creation. Each HTTP request also has its own timeout;
the retry window is not a hard cancellation deadline for an in-flight request.
This teaching keyword retries any ordinary failure, including wrong HTTP status.
For production, decide which failures are transient and fail immediately on
permanent problems such as authorization errors.

## Isolation and limits

Suite setup starts a local server and creates sessions for two users and an
anonymous client. Test setup resets all orders, keys and simulated completion
times. Template rows share one test setup; rejected quantities must not create
state, and accepted boundary rows use different keys. Teardown always stops the
server and closes sessions. Tests can run in a different order.

The Python contract keyword checks selected required fields and allows extra
fields. It is not JSON Schema or a consumer-driven contract test. A real project
could validate against an independently maintained OpenAPI/JSON Schema contract.
Writing the mock and tests together can reproduce the same mistaken assumption
on both sides; passing here proves the learning examples, not a production API.

Confirmation is simulated using elapsed monotonic time and a GET that updates
state. There is no real queue or worker. In-memory data has no durability. The
lock protects idempotency lookup and insertion, but these sequential tests do
not prove concurrent correctness. HTTP requests here are local and plaintext;
TLS, token issuance/expiry and rate limiting are outside this mock.

## Next interview exercises

1. Add a missing-order test expecting 404 and an invalid bearer-token test.
2. Add PATCH with an ETag and If-Match; reject stale updates with 412, and prove
   the second writer did not overwrite the first writer's changes.
3. Send concurrent POSTs with the same key; verify all responses reference one ID.
4. Simulate 429 plus Retry-After; implement bounded retries that respect the header.
5. Simulate a timeout after the server stores an order; retry with the same key.
6. Add a job-failure state and prove polling fails usefully instead of retrying forever.
7. Insert records between page reads and discuss when cursor pagination helps.

## Official references

- [RequestsLibrary guide](https://docs.robotframework.org/docs/different_libraries/requests)
- [Robot BuiltIn keywords, including Wait Until Keyword Succeeds](https://robotframework.org/robotframework/latest/libraries/BuiltIn.html)
