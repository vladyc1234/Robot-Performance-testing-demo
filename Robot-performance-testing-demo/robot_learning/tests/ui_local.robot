*** Settings ***
Documentation    Browser -> local HTML -> fetch -> mock API, with explicit waits.
Resource    ../resources/service.resource
Library    SeleniumLibrary    timeout=10 seconds
Suite Setup    Start Practice Service
Suite Teardown    Stop Practice Service
Test Setup    Open Fresh Registration Page
Test Teardown    Close All Browsers
Test Tags    ui    local

*** Variables ***
${BROWSER}    headlesschrome

*** Test Cases ***
Register A User Through The Browser
    Input Text    id=name    Grace
    Click Button    id=save
    # Wait for asynchronous fetch to finish; fixed Sleep calls are unnecessary.
    Wait Until Element Contains    id=status    Created user: Grace
    ${response}=    GET On Session    api    /api/users/2    expected_status=200
    User Should Have Name    ${response.json()}    Grace

Empty Name Displays A Helpful Error
    Click Button    id=save
    Wait Until Element Contains    id=status    Name is required
    ${response}=    GET On Session    api    /api/users    expected_status=200
    Length Should Be    ${response.json()}    1

*** Keywords ***
Open Fresh Registration Page
    Reset Mock Data
    Open Browser    ${BASE_URL}    ${BROWSER}
    Wait Until Element Is Visible    id=name
    Title Should Be    User registration practice
