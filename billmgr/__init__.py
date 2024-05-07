import sys
import os
if not '/usr/local/mgr5/lib/python' in sys.path:
    sys.path.insert(0, '/usr/local/mgr5/lib/python')
if not '/usr/local/mgr5/lib/python/billmgr/thirdparty' in sys.path:
    sys.path.insert(0, '/usr/local/mgr5/lib/python/billmgr/thirdparty')

BINARY_NAME = os.path.splitext(os.path.basename(sys.argv[0]))[0]