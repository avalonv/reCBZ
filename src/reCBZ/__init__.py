from uuid import uuid4

__version__ = "0.7.0"
CMDNAME = 'recbz'

# whether to print the 'recbz.py' title at the beginning
SHOWTITLE = True

# global UUID for files stored in temp, so we can ensure multiple instances
# created under the same process don't delete cache currently used by another
TEMPUUID = str(uuid4().hex)
