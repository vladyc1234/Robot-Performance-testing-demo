*** Settings ***
Documentation    Optional external smoke test. Google may show consent or CAPTCHA.
Library    SeleniumLibrary    timeout=15 seconds
Test Teardown    Close All Browsers
Test Tags    ui    external

*** Variables ***
${BROWSER}    headlesschrome
${GOOGLE_URL}    https://www.google.com/?hl=en
# English consent button; override for a different locale or changed markup.
${CONSENT_LOCATOR}    xpath=//button[.//div[normalize-space()='Reject all']]

*** Test Cases ***
Type A Search Query On Google
    [Documentation]    Exercise navigation, locators, typing and an input assertion.
    Open Browser    ${GOOGLE_URL}    ${BROWSER}
    ${consent_shown}=    Run Keyword And Return Status
    ...    Wait Until Element Is Visible    ${CONSENT_LOCATOR}    5 seconds
    IF    ${consent_shown}
        Click Element    ${CONSENT_LOCATOR}
    END
    Wait Until Element Is Visible    name=q
    Input Text    name=q    Robot Framework Python
    # Google's search box can be a textarea, so read its value generically.
    ${query}=    Get Value    name=q
    Should Be Equal    ${query}    Robot Framework Python
    # This tests typing, not search results. CAPTCHA/markup failures stay visible.
