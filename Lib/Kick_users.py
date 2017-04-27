from arcpy import ListUsers, DisconnectUser
from Exceptions import DBLock


def kick(gdb, users="all"):
    """Users: Python list of user names."""
    try:
        if users == "all":
            DisconnectUser(gdb, users="ALL")
        else:
            for u in ListUsers(gdb):
                if u.Name in users:
                    DisconnectUser(gdb, u.ID)
        return 0
    except Exception as e:
        raise DBLock(("All users may not have been kicked.", e.message))


