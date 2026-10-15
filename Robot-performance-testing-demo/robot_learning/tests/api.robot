*** Settings ***
Documentation    Real HTTP requests against a fake local service. No internet needed.
Resource    ../resources/service.resource
Library    Collections
Suite Setup    Start Practice Service
Suite Teardown    Stop Practice Service
Test Setup    Reset Mock Data
Test Tags    api

*** Test Cases ***
Health Endpoint Returns JSON
    ${response}=    GET On Session    api    /health    expected_status=200
    Should Contain    ${response.headers}[Content-Type]    application/json
    ${body}=    Set Variable    ${response.json()}
    Should Be Equal    ${body}[status]    ok

Create Read And Delete A User
    [Documentation]    Arrange a payload, act via HTTP, then assert status AND data.
    ${payload}=    Create Dictionary    name=Grace
    ${created}=    POST On Session    api    /api/users    json=${payload}    expected_status=201
    ${user}=    Set Variable    ${created.json()}
    # This readable keyword runs user_should_have_name() in MockService.py.
    User Should Have Name    ${user}    Grace
    Should Be Equal As Integers    ${user}[id]    2
    ${read}=    GET On Session    api    /api/users/${user}[id]    expected_status=200
    Dictionaries Should Be Equal    ${read.json()}    ${user}
    DELETE On Session    api    /api/users/${user}[id]    expected_status=204
    ${missing}=    GET On Session    api    /api/users/${user}[id]    expected_status=404
    Should Be Equal    ${missing.json()}[error]    User not found

Invalid Names Are Rejected
    [Documentation]    One template runs the same assertion with several inputs.
    [Template]    Name Should Be Rejected
    ${EMPTY}
    ${SPACE}
    ${None}
    ${123}

Malformed JSON Is Rejected
    ${response}=    POST On Session    api    /api/users    data=not-json    expected_status=400
    Should Be Equal    ${response.json()}[error]    Invalid JSON

Missing User Returns Not Found
    ${response}=    GET On Session    api    /api/users/999    expected_status=404
    Should Be Equal    ${response.json()}[error]    User not found

Private Endpoint Requires A Token
    ${denied}=    GET On Session    api    /api/private    expected_status=401
    Should Be Equal    ${denied.json()}[error]    Unauthorized
    ${headers}=    Create Dictionary    Authorization=Bearer learning-token
    ${allowed}=    GET On Session    api    /api/private    headers=${headers}    expected_status=200
    Should Be Equal    ${allowed.json()}[message]    Access granted

Every Test Starts With Only Ada
    ${response}=    GET On Session    api    /api/users    expected_status=200
    ${users}=    Set Variable    ${response.json()}
    Length Should Be    ${users}    1
    FOR    ${user}    IN    @{users}
        User Should Have Name    ${user}    Ada
    END

*** Keywords ***
Name Should Be Rejected
    [Arguments]    ${name}
    ${payload}=    Create Dictionary    name=${name}
    # expected_status=400 makes this a passing negative test, not an ignored error.
    ${response}=    POST On Session    api    /api/users    json=${payload}    expected_status=400
    Should Be Equal    ${response.json()}[error]    Name is required
    ${users}=    GET On Session    api    /api/users    expected_status=200
    Length Should Be    ${users.json()}    1
