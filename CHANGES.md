# Add base functionality and idea

**Version**: v0.1.0

**Date:** 27/05/2025

## Additions

**`/app/deps.py`**:

* Added `CheckGroupValidDep` for entries to check if the provided group is valid.

**`/app/routers/groups.py | /app/models/groups.py`**:

* Added bare functionality for password groups, will add parent/children groups later.

**`/app/routers/entries.py | /app/models/entries.py`**:

* Added bare functionality for password entries, will add file entries and encryption later.

**`/app/routers/utils.py`**:

* Added simple healthcheck for the app.

**`/app/internal/database.py`**:

* Added `PasswordGroupMethods` and `PasswordEntryMethods` for their respective group and entry functionality.

**`/app/internal/dbtables.py`**:

* Added `PasswordGroups` and `PasswordEntry` tables.

**`/README.md`**:

* Added simple information to project README.md file.

## Changes

* None.

## Misc

* This is a very early concept, so lots of features and ideas are yet to be implemented.
* Mostly done with copying from syncServer, so next is to implement features.
