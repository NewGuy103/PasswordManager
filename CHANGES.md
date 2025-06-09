# Add metadata for entries

**Version**: v0.1.0

**Date:** 9/06/2025

## Additions

**`/app/routers/auth.py`**:

* Added `responses` to the `/token` endpoint to show that 400 and 401 are expected status codes.

**`/app/routers/entries.py | /app/models/entries.py`**:

* Added fields `entry_username`, `entry_password` and `entry_url` as a replacement to `entry_data`.

**`/app/internal/database.py`**:

* Added new parameters from fields to `PasswordEntryMethods.create_entry()`.

**`/app/models/dbtables.py`**:

* Added `entry_username`, `entry_password` and `entry_url` as a replacement to `entry_data`.

## Changes

**`/app/models/entries.py`**:

* Replaced `EntryReplaceData` with `EntryUpdate` since the PATCH operation is now a PUT operation.
* Removed `group_name` from `EntryPublicGet` and instead kept the `group_id`.
* Removed `EntryData` and `GroupName` aliases as they are no longer used.

**`/app/routers/entries.py`**:

* Changed `PATCH /{entry_id}` to `PUT /{entry_id}` because it changes most of the entry data now.

**`/app/routers/groups.py`**:

* `GET /groups` and `GET /groups/{group_id}/children` now returns one single `GroupPublicGet` instead of a list
  of `GroupPublicGet` with only one item. The children returned is in the `child_groups` key.

**`/app/internal/database.py`**:

* `logger` object now gets the `password_manager` logger instead of the syncServer logger.
* Changed `PasswordGroupMethods.get_children_of_root()` and `get_children_of_group()` to return one
  `GroupPublicGet` model instead of a list with only one `GroupPublicGet` model.
* Changed `PasswordEntryMethods.create_entry()` and `get_entries_by_group()` to expect one
  group model from SQLModel and to not return a boolean value anymore.
* Replaced `replace_entry_data()` with `update_entry_data()` as the method changed from PATCH to PUT.

## Misc

* Work is currently being done on the client application to make it not require the server, which means
  this server component will only be an integrated sync instead of a requirement for the app to function.
