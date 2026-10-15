# Robot Framework with Python: practical lessons

For response-time and concurrent-request exercises, see [Performance testing](PERFORMANCE_TESTING.md).
Run `.\.venv\Scripts\python.exe robot_learning/run_examples.py performance`.

For advanced API exercises, see [Interview preparation](INTERVIEW_PREP.md).
Run them with `.\.venv\Scripts\python.exe robot_learning/run_examples.py interview`.
The `all` option includes these advanced tests as well as the beginner API and local UI tests.

Robot Framework runs readable test steps from `.robot` files. Python libraries
implement those steps. Here you get both: executable tests, a Python keyword
library, a mock HTTP server, and a Python test runner. Your existing `main.py`
generator exercise is separate; it is not used to launch these examples.

## Run from the project root (PowerShell)

Use the interpreter configured in PyCharm. In this project it is `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r robot_learning/requirements.txt
.\.venv\Scripts\python.exe robot_learning/run_examples.py api
.\.venv\Scripts\python.exe robot_learning/run_examples.py ui
.\.venv\Scripts\python.exe robot_learning/run_examples.py ui --browser chrome
.\.venv\Scripts\python.exe robot_learning/run_examples.py google --browser chrome
.\.venv\Scripts\python.exe robot_learning/run_examples.py all
```

`api` requires no browser and makes no external API calls. `ui` uses installed
Chrome, headless by default. Selenium Manager may need internet access on the
first run to obtain a matching driver. `--browser edge` can use installed Edge.
`all` runs the API and local UI suites; Google is explicitly opt-in.

In PyCharm, open `run_examples.py` and run it: the default is the API suite.
Set script parameters to `ui --browser chrome` for a visible browser example.
Each run returns a nonzero exit code when tests fail.

Open `results/api/report.html` for a summary and `results/api/log.html` for
individual steps, inputs, responses, and assertion failures. UI results go in
`results/ui/`; SeleniumLibrary captures screenshots on failures where possible.

You can also invoke Robot directly to select tests or tags:

```powershell
.\.venv\Scripts\python.exe -m robot --outputdir robot_learning/results/selected --include api robot_learning/tests
.\.venv\Scripts\python.exe -m robot --outputdir robot_learning/results/one --test "Create Read And Delete A User" robot_learning/tests/api.robot
.\.venv\Scripts\python.exe -m robot --dryrun --outputdir robot_learning/results/dryrun robot_learning/tests
```

A dry run checks keyword names and argument structure; it does not test HTTP,
launch a browser, or prove application behavior.

## Suggested reading order

1. `tests/api.robot`: start with the health check, then the create/read/delete flow.
2. `resources/service.resource`: reusable suite setup and teardown keywords.
3. `libraries/MockService.py`: see how Robot calls Python and how HTTP is handled.
4. `tests/ui_local.robot` and `web/index.html`: follow a click through JavaScript
   `fetch`, the HTTP server, and the UI assertion.
5. `tests/ui_google.robot`: try locators and typing on an external website.

## Read the Robot syntax

Separate cells with **at least two spaces** (the examples use four). Single
spaces are allowed inside a keyword name such as `Should Be Equal`.

```robotframework
${payload}=    Create Dictionary    name=Grace
${response}=    POST On Session    api    /api/users    json=${payload}    expected_status=201
${user}=    Set Variable    ${response.json()}
User Should Have Name    ${user}    Grace
```

The first step creates a Python dictionary. The second sends it as JSON over
HTTP using the session alias `api`. The third decodes the response into a Python
object. The last calls our Python assertion method `user_should_have_name`.
Robot maps underscores to spaces and ignores keyword-name case.

| Syntax | Meaning |
| --- | --- |
| `*** Settings ***` | Imports, documentation, setup, teardown, tags |
| `*** Variables ***` | Default configuration, overridable with `--variable` |
| `*** Test Cases ***` | Named scenarios and their steps |
| `*** Keywords ***` | Reusable groups of steps |
| `${value}` | One object, including a list or dictionary |
| `@{users}` | Expand a list, for example in a `FOR` loop |
| `${user}[name]` | Read a dictionary field |
| `${123}`, `${None}` | An integer and Python `None`, not strings |
| `[Template]` | Run one keyword with several rows of input data |

`Suite Setup` starts the server once. `Test Setup` resets its in-memory data
before every test, so tests do not depend on their execution order. Teardown
closes HTTP sessions, browser windows, and the server even after failures.
The mock binds only to `127.0.0.1` on a free port and is stopped automatically.
These examples are intended for sequential test execution.

## API lessons

The mock is a real local server with fake data, not a patched HTTP client. That
lets you inspect actual requests, JSON serialization, status codes and headers.
It begins with `{"id": 1, "name": "Ada"}` and resets between tests.

| Method and route | Behavior |
| --- | --- |
| `GET /health` | 200, `{"status": "ok"}` |
| `GET /api/users` | 200, a list of users |
| `POST /api/users` | 201 with a generated ID; body: `{"name": "Grace"}` |
| `GET /api/users/<id>` | 200 when present; otherwise 404 |
| `DELETE /api/users/<id>` | 204 with no body; otherwise 404 |
| `GET /api/private` | 200 with `Authorization: Bearer learning-token`; otherwise 401 |

Invalid JSON or an invalid name returns 400. The token is a fixed demonstration
string, not real authentication. State is in memory and disappears on shutdown.

Assert both the status and response data: a 200 response with the wrong user is
still a bug. `expected_status=400` explicitly verifies an expected rejection;
it does not suppress a failure. Avoid decoding JSON from a 204 empty response.
The template checks empty, whitespace, null and numeric names. A final GET checks
that invalid input did not create a user.

## UI lessons

The local form provides stable `id=name`, `id=save` and `id=status` locators.
The successful scenario types a name, clicks Save, waits for the asynchronous
confirmation and verifies the stored user through the API. The failure scenario
checks the validation message and verifies that no user was created.

Prefer `Wait Until Element Contains` or `Wait Until Element Is Visible` over
fixed sleeps: they continue as soon as the condition becomes true and fail at
the timeout if it never does. Each test opens a fresh browser and closes it in
teardown, avoiding leaked cookies and windows.

The optional Google example tests opening the page and typing into `name=q`.
It deliberately makes no claim about search-result correctness. Consent
screens, regional markup and CAPTCHA can cause genuine external test failures.
An English “Reject all” locator is supplied, but may need updating. Do not
bypass CAPTCHA; practice with the local suite if Google blocks automation.

## Exercises

1. Change the expected name to `Wrong` and inspect the failed step in `log.html`.
2. Add a test proving `"  Grace  "` is trimmed to `"Grace"`.
3. Add an incorrect bearer-token test expecting 401.
4. Add a missing-name payload test using an empty dictionary.
5. Extend the mock with a PUT route, then test updating and reading a user.
6. Add an email field to the page, server validation and both API/UI tests.

## Official references

- [Robot Framework User Guide](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html)
- [RequestsLibrary keywords](https://marketsquare.github.io/robotframework-requests/doc/RequestsLibrary.html)
- [SeleniumLibrary keywords](https://robotframework.org/SeleniumLibrary/SeleniumLibrary.html)
