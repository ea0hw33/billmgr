from billmgr.db import *

# db_query_dict("UPDATE user SET password = '$5$Zt1jOXVIcV779NvJ$hJfM.64A2nN2s4kKuBhVbfgRLyhf2iHk6H89NwDidkD' WHERE id = '1'")
print(db_query("SELECT number FROM payment"))

