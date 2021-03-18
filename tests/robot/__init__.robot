*** Settings ***
Suite Setup    Setup before all tests

*** Keywords ***
Setup before all tests
    evaluate    sys.path.append(os.path.join("path", "to", "library"))    modules=os, sys