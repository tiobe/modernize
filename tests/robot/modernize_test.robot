*** Settings ***
Documentation     Modernize version

Library  Process
Library  OperatingSystem

*** Test Cases ***
Modernize version
    [Documentation]  Modernize version
    ${result}=  Run Process  python  ${CURDIR}${/}..${/}..${/}modernize.py  --version
    Should Contain    ${result.stdout}    TIOBE

Modernize fix_expect FP
    [Documentation]  Modernize fix_expect FP enforce #27753
    ${result}=  Run Process  python  ${CURDIR}${/}..${/}..${/}modernize.py  -f  fissix.fixes.fix_except  --enforce  ${CURDIR}/test_files/fix_except_test_py3.py
    Should Be Equal As Integers  ${result.rc}  0

Modernize fix_expect python 2 file TP
    [Documentation]  Modernize fix_expect TP enforce #27753
    ${result}=  Run Process  python  ${CURDIR}${/}..${/}..${/}modernize.py  -f  fissix.fixes.fix_except  --enforce  ${CURDIR}/test_files/fix_except_test_py2.py
    Should Be Equal As Integers  ${result.rc}  2

Modernize python 2
    [Documentation]  Modernize with enforce option - python 2 #26566
    ${result}=  Run Process  python  -B  ${CURDIR}${/}..${/}..${/}modernize.py  --enforce  ${CURDIR}/test_files/py2.py
    Should Be Equal As Integers  ${result.rc}  2


Modernize python 3
    [Documentation]  Modernize with enforce option - python 3 #26566
    ${result}=  Run Process  python  -B  ${CURDIR}${/}..${/}..${/}modernize.py  --enforce  ${CURDIR}/test_files/py3.py
    Should Be Equal As Integers  ${result.rc}  0