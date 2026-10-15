*** Settings ***
Documentation    Six short runnable lessons. Read PERFORMANCE_TESTING.md first.
Library    ../libraries/PerformanceLibrary.py
Test Tags    performance    theory

*** Test Cases ***
Load Testing - Expected Traffic
    # Two clients fit the toy service's two processing slots.
    ${result}=    Demonstrate Load Testing
    Save Performance Result    ${result}    ${OUTPUT DIR}/lesson-load.json
    Performance Should Meet Budget    ${result}

Stress Testing - Increase Beyond Capacity And Recover
    ${stages}=    Demonstrate Stress Testing
    Save Performance Result    ${stages}    ${OUTPUT DIR}/lesson-stress.json
    # Overload is expected; the lesson passes when errors are detected.
    Should Be True    ${stages}[2][metrics][failures] > 0
    Performance Should Meet Budget    ${stages}[0]
    Performance Should Meet Budget    ${stages}[3]

Soak Testing - Watch Stable Load Over Time
    ${windows}=    Demonstrate Soak Testing    duration_seconds=2
    Save Performance Result    ${windows}    ${OUTPUT DIR}/lesson-soak.json
    FOR    ${window}    IN    @{windows}
        Performance Should Meet Budget    ${window}
    END

Spike Testing - Sudden Burst And Recovery
    ${stages}=    Demonstrate Spike Testing
    Save Performance Result    ${stages}    ${OUTPUT DIR}/lesson-spike.json
    Performance Should Meet Budget    ${stages}[0]
    Should Be True    ${stages}[1][metrics][failures] > 0
    Performance Should Meet Budget    ${stages}[2]

Volume Testing - Grow Data With One Reader
    ${results}=    Demonstrate Volume Testing
    Save Performance Result    ${results}    ${OUTPUT DIR}/lesson-volume.json
    # More data must still produce the correct answer.
    Should Be Equal As Integers    ${results}[2][matched]    50000

Scalability Testing - Add Processing Resources
    ${stages}=    Demonstrate Scalability Testing
    Save Performance Result    ${stages}    ${OUTPUT DIR}/lesson-scalability.json
    Should Be True    ${stages}[0][metrics][failures] > 0
    Performance Should Meet Budget    ${stages}[2]
    # Inspect speedup and efficiency; do not assume exact linear scaling.
