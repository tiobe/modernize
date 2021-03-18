def testl():    
    try:
        raise NameError('HiThere')
    except (RuntimeError, ImportError) ,    e:
        print('An exception flew by!')