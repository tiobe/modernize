def testl():    
    try:
        raise NameError('HiThere')
    except (RuntimeError, ImportError) as    e:
        print('An exception flew by!')