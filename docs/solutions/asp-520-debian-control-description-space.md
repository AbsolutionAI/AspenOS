# Learning: Debian control file Description field must not have leading space

**Ticket:** ASP-520 / ASP-522 (cherry-picked via hermes worktrees)

## Problem

The `Description:` field in `debian/DEBIAN/control` had a leading space (` Description:`), which is a Debian control format violation. The space caused `dpkg-deb` to interpret the field name as a continuation line rather than the field itself, emitting a warning:

```
dpkg-deb: warning: Description' field, missing description, resorting to default
```

This did not break the build (dpkg-deb auto-corrected) but emitted a distracting warning during every package build. Two separate hermes worktree branches independently fixed it with identical patches.

## Fix

Removed the leading space before `Description:` in `debian/DEBIAN/control` (line 11):

```diff
- Description: Starship OS
+Description: Starship OS
```

## Patterns to reuse

- **Debian control fields must start at column 0.** Only continuation lines (extended description text) should have leading whitespace.
- **Nightly check Section 9** (`debian control file` pass) was already catching the file's existence but not its content format. A grep for `^ Description:` in the control file would catch this class of issue proactively.
- **Coordinate between worktrees.** Duplicate commits across hermes worktrees signal a coordination gap — consider a shared branch or notification mechanism for simultaneous hygiene fixes.