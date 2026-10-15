*** Settings ***
Documentation    Small local performance experiments; thresholds are teaching defaults.
Library    ../libraries/InterviewService.py
Library    ../libraries/PerformanceLibrary.py
Suite Setup    Start Performance API
Suite Teardown    Stop Interview Service
Test Setup    Reset Interview Data
Test Tags    performance

*** Variables ***
${MAX_P95_MS}    1500

*** Test Cases ***
Single User Baseline
    [Documentation]    Establish latency without competing clients.
    ${result}=    Measure Order Reads    ${BASE_URL}    users=1    requests_per_user=40
    Save Performance Result    ${result}    ${OUTPUT DIR}/baseline.json
    Performance Should Meet Budget    ${result}    max_p95_ms=${MAX_P95_MS}

Four Concurrent Users
    [Documentation]    Four workers, each issuing one request at a time: 160 measured GETs.
    ${result}=    Measure Order Reads    ${BASE_URL}    users=4    requests_per_user=40
    Save Performance Result    ${result}    ${OUTPUT DIR}/concurrent.json
    Performance Should Meet Budget    ${result}    max_p95_ms=${MAX_P95_MS}

Compare Increasing Concurrency
    [Documentation]    Separate bounded stages, not a continuous ramp or capacity test.
    FOR    ${users}    IN    1    2    4
        ${result}=    Measure Order Reads    ${BASE_URL}    users=${users}    requests_per_user=30
        Save Performance Result    ${result}    ${OUTPUT DIR}/stage-${users}.json
        Performance Should Meet Budget    ${result}    max_p95_ms=${MAX_P95_MS}
    END

Fast Errors Must Not Count As Success
    [Documentation]    A fast 401 is still a failure; prove that the budget catches it.
    ${result}=    Measure Order Reads    ${BASE_URL}    users=2    requests_per_user=10    token=invalid
    Save Performance Result    ${result}    ${OUTPUT DIR}/expected-errors.json
    Should Be Equal As Integers    ${result}[metrics][failures]    20
    Run Keyword And Expect Error    Error rate 100.0% exceeds 0.0%
    ...    Performance Should Meet Budget    ${result}

*** Keywords ***
Start Performance API
    ${url}=    Start Interview Service
    Set Suite Variable    ${BASE_URL}    ${url}
