# Change identifer for groups to a uuid

**Version**: v0.1.0

**Date:** 29/05/2025

## Additions

**`/app/routers/entries.py`**:

* Added `PATCH /entries/{entry_id}` to replace the entry data.

**`/app/routers/groups.py`**:

* Added `GET /{group_id}/children` to get all the children of a certain group. Getting the children of
  the root group acts similar to simply `GET /groups`.
* Added `POST /{group_id}/move` to move the specified group to another parent.

**`/app/internal/database.py`**:

* Added `PasswordGroupMethods.move_to_new_parent()` to move a group to a new parent group.
* Added `check_group_is_root()` to simply check if the group is the top-level group.
* Added `PasswordEntryMethods.replace_entry_data()` to replace entry data.

## Changes

**`/app/deps.py`**:

* `CheckGroupValidDep` now returns a UUID from the path.

**`/app/internal/config.py`**:

* Changed `PasswordGroups` to be a self-referential model so everything can base off the first top-level group.
* Added `is_root` field to identify if it's the root field or not.

**`/app/models/entries.py`**:

* `EntryPublicGet` now returns the `group_id` with the entry.

**`/app/models/groups.py`**:

* Removed `CannotBeRoot` after validator.
* Groups are now uniquely identified by their `group_id`.

**`/app/routers/entries.py`**:

* Changed path operation identifier from `group_name` to `group_id`.

**`/app/routers/groups.py`**:

* Changed all `group_name` path identifiers to `group_id`.
* Modify operations now return a `GroupPublicModify` which leaves out the child groups.

**`/app/internal/database.py`**:

* Most `PasswordGroupMethods` now uses `group_id` instead of `group_name`, changes:
  * `create_group()` now requires a `parent_id` unless it is the top-level group
    and returns a `GroupPublicModify` instead of a `GroupPublicGet`.
  * `get_children_of_root()` now returns a `GroupPublicGet` with a list of `GroupPublicChildren`.
  * `get_children_of_group()` also returns similar to `get_children_of_root()`, and if the provided group ID is
    the top-level group, calls `get_children_of_root()` instead.
  * `delete_group()` now prevents deleting the top-level group.
  * `rename_group()` now allows renaming the top-level group and returns a `GroupPublicModify`.
* Changed `PasswordEntryMethods.create_entry()` to use a `group_id` instead of `group_name`.

## Misc

* This is a very early concept, so lots of features and ideas are yet to be implemented.
* Mostly done with copying from syncServer, so next is to implement features.
