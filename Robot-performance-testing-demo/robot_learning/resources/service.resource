*** Settings ***
Library    ../libraries/MockService.py
Library    RequestsLibrary

*** Keywords ***
Start Practice Service
    ${url}=    Start Mock Service
    Set Suite Variable    ${BASE_URL}    ${url}
    Create Session    api    ${BASE_URL}    timeout=5

Stop Practice Service
    TRY
        Delete All Sessions
    FINALLY
        Stop Mock Service
    END
