*** Settings ***
Documentation    Orders API: ownership, idempotency, contracts, pagination and polling.
Library    ../libraries/InterviewService.py
Library    RequestsLibrary
Library    Collections
Suite Setup    Start Interview API
Suite Teardown    Stop Interview API
Test Setup    Reset Interview Data
Test Tags    api    interview

*** Test Cases ***
Created Order Has A Location And Valid Contract
    ${response}=    Create Order    alice    first-order
    Should Contain    ${response.headers}[Content-Type]    application/json
    ${order}=    Set Variable    ${response.json()}
    Order Should Match Contract    ${order}
    Should Be Equal    ${order}[owner]    alice
    Should Be Equal    ${order}[sku]    BOOK
    Should Be Equal As Integers    ${order}[quantity]    1
    Should Be Equal    ${order}[status]    pending
    Should Be Equal    ${response.headers}[Location]    /orders/${order}[id]
    ${read}=    GET On Session    alice    ${response.headers}[Location]    expected_status=200
    Should Be Equal    ${read.json()}[id]    ${order}[id]

Authentication Is Different From Ownership
    ${created}=    Create Order    alice    private-order
    ${path}=    Set Variable    ${created.headers}[Location]
    ${anonymous}=    GET On Session    anonymous    ${path}    expected_status=401
    Should Be Equal    ${anonymous.json()}[error]    invalid_token
    Should Be Equal    ${anonymous.headers}[WWW-Authenticate]    Bearer
    ${other_user}=    GET On Session    bob    ${path}    expected_status=403
    Should Be Equal    ${other_user.json()}[error]    forbidden
    Dictionary Should Not Contain Key    ${other_user.json()}    sku
    ${owner}=    GET On Session    alice    ${path}    expected_status=200
    Should Be Equal    ${owner.json()}[owner]    alice

Retrying A POST With The Same Key Does Not Duplicate Orders
    ${first}=    Create Order    alice    checkout-42
    ${retry}=    Create Order    alice    checkout-42    expected=200
    Dictionaries Should Be Equal    ${first.json()}    ${retry.json()}
    Should Be Equal    ${retry.headers}[Idempotency-Replayed]    true
    Order Count Should Be    alice    1

Reusing A Key With Different Data Is A Conflict
    ${first}=    Create Order    alice    checkout-42
    ${conflict}=    Create Order    alice    checkout-42    quantity=${2}    expected=409
    Should Be Equal    ${conflict.json()}[error]    idempotency_conflict
    ${stored}=    GET On Session    alice    ${first.headers}[Location]    expected_status=200
    Should Be Equal As Integers    ${stored.json()}[quantity]    1
    Order Count Should Be    alice    1

Idempotency Keys Are Scoped To Each User
    ${alice}=    Create Order    alice    shared-key
    ${bob}=    Create Order    bob    shared-key
    Should Not Be Equal    ${alice.json()}[id]    ${bob.json()}[id]
    Order Count Should Be    alice    1
    Order Count Should Be    bob    1

Pagination Has No Gaps Duplicates Or Other Users Data
    ${expected_ids}=    Create List
    FOR    ${index}    IN RANGE    5
        ${response}=    Create Order    alice    order-${index}
        Append To List    ${expected_ids}    ${response.json()}[id]
    END
    Create Order    bob    hidden-order
    ${actual_ids}=    Create List
    FOR    ${page}    IN RANGE    1    4
        ${params}=    Create Dictionary    page=${page}    size=${2}
        ${response}=    GET On Session    alice    /orders    params=${params}    expected_status=200
        ${body}=    Set Variable    ${response.json()}
        Should Be Equal As Integers    ${body}[total]    5
        Should Be Equal As Integers    ${body}[page]    ${page}
        FOR    ${order}    IN    @{body}[items]
            Order Should Match Contract    ${order}
            Should Be Equal    ${order}[owner]    alice
            Append To List    ${actual_ids}    ${order}[id]
        END
    END
    Lists Should Be Equal    ${actual_ids}    ${expected_ids}
    ${params}=    Create Dictionary    page=${4}    size=${2}
    ${last}=    GET On Session    alice    /orders    params=${params}    expected_status=200
    Should Be Empty    ${last.json()}[items]

Quantity Validation Rejects Wrong Types And Boundaries
    [Template]    Quantity Should Be Rejected
    ${0}
    ${6}
    ${-1}
    ${1.5}
    ${True}
    ${None}
    2

Pagination Rejects Invalid Parameters
    [Template]    Pagination Should Be Rejected
    0    2
    1    0
    1    4
    abc    2

Accepted Quantity Boundaries
    [Template]    Quantity Should Be Accepted
    ${1}
    ${5}

Missing Idempotency Key Does Not Create An Order
    ${payload}=    Create Dictionary    sku=BOOK    quantity=${1}
    ${response}=    POST On Session    alice    /orders    json=${payload}    expected_status=400
    Should Be Equal    ${response.json()}[error]    idempotency_key_required
    Order Count Should Be    alice    0

Unsupported Media Type Is Rejected
    ${headers}=    Create Dictionary    Content-Type=text/plain    Idempotency-Key=text-order
    ${response}=    POST On Session    alice    /orders    data=hello    headers=${headers}    expected_status=415
    Should Be Equal    ${response.json()}[error]    json_required
    Order Count Should Be    alice    0

Poll Until An Order Is Confirmed
    ${created}=    Create Order    alice    async-order
    Should Be Equal    ${created.json()}[status]    pending
    # Repeat only the read/assertion. Never retry the whole create workflow blindly.
    Wait Until Keyword Succeeds    3 seconds    100 milliseconds
    ...    Order Should Be Confirmed    ${created.headers}[Location]
    Order Count Should Be    alice    1

*** Keywords ***
Start Interview API
    ${url}=    Start Interview Service
    ${alice_headers}=    Create Dictionary    Authorization=Bearer alice-token
    ${bob_headers}=    Create Dictionary    Authorization=Bearer bob-token
    Create Session    alice    ${url}    headers=${alice_headers}    timeout=2
    Create Session    bob    ${url}    headers=${bob_headers}    timeout=2
    Create Session    anonymous    ${url}    timeout=2

Stop Interview API
    TRY
        Delete All Sessions
    FINALLY
        Stop Interview Service
    END

Create Order
    [Arguments]    ${session}    ${key}    ${quantity}=${1}    ${expected}=201
    ${payload}=    Create Dictionary    sku=BOOK    quantity=${quantity}
    ${headers}=    Create Dictionary    Idempotency-Key=${key}
    ${response}=    POST On Session    ${session}    /orders
    ...    json=${payload}    headers=${headers}    expected_status=${expected}
    RETURN    ${response}

Order Count Should Be
    [Arguments]    ${session}    ${expected}
    ${response}=    GET On Session    ${session}    /orders    expected_status=200
    Should Be Equal As Integers    ${response.json()}[total]    ${expected}

Quantity Should Be Rejected
    [Arguments]    ${quantity}
    ${response}=    Create Order    alice    invalid-order    quantity=${quantity}    expected=422
    Should Be Equal    ${response.json()}[error]    invalid_order
    Order Count Should Be    alice    0

Quantity Should Be Accepted
    [Arguments]    ${quantity}
    ${response}=    Create Order    alice    boundary-${quantity}    quantity=${quantity}
    Should Be Equal As Integers    ${response.json()}[quantity]    ${quantity}

Pagination Should Be Rejected
    [Arguments]    ${page}    ${size}
    ${params}=    Create Dictionary    page=${page}    size=${size}
    ${response}=    GET On Session    alice    /orders    params=${params}    expected_status=400
    Should Be Equal    ${response.json()}[error]    invalid_pagination

Order Should Be Confirmed
    [Arguments]    ${path}
    ${response}=    GET On Session    alice    ${path}    expected_status=200
    Order Should Match Contract    ${response.json()}
    Should Be Equal    ${response.json()}[status]    confirmed
