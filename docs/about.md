# gotchi

`gotchi` is a lightweight terminal virtual pet for pubnix-style communities such as Runv.Club. The project keeps the original MVP spirit: no resident daemon, no service process, no web layer. The pet evolves only when a command runs, based on elapsed real time since the last saved update.

The current build is ready for multi-user Unix environments:

- canonical ownership by real process UID
- one private state directory per user
- one SQLite database per user
- migration from the older username-keyed save model
- lock-protected updates for concurrent shells/SSH sessions
- the original gameplay commands preserved
- the hidden `gotchi -runv` mode preserved

## Installation

Requires Python 3.9+.

```bash
python3 -m pip install .
```

This installs:

```bash
gotchi
```

For local development:

```bash
python3 -m pip install -e .
python3 -m unittest discover -s tests -v
```

## Core Commands

```bash
gotchi
gotchi init --name Nyx --species crow
gotchi status
gotchi feed
gotchi play
gotchi sleep
gotchi clean
gotchi rename Corvus
gotchi doctor
gotchi doctor --storage
gotchi path
gotchi migrate
gotchi export backup.json
gotchi import backup.json
gotchi line
gotchi help
```

Hidden command kept intentionally undocumented in help:

```bash
gotchi -runv
```

## Identity Model

Ownership is now derived from the real account running the process.

On Unix-like systems the app resolves identity from:

- `os.getuid()`
- `pwd.getpwuid(os.getuid())`

This means:

- UID is the canonical owner key
- username is display metadata and compatibility data
- `USER`, `LOGNAME`, `HOME` and similar variables are not trusted as the source of truth for who owns the pet

Environment variables may still influence XDG locations when appropriate, but they do not change who owns a pet.

## Storage Layout

Each user gets a private state layout.

Preferred user state root:

- `XDG_STATE_HOME/gotchi/uid-<UID>/`

Safe fallback roots when the preferred location is unavailable:

- `<real-home>/.local/state/gotchi/uid-<UID>/`
- `./.gotchi-state/uid-<UID>/` as a last-resort workspace fallback

Equivalent per-user directories also exist for config and data:

- config: `XDG_CONFIG_HOME/gotchi/uid-<UID>/`
- data: `XDG_DATA_HOME/gotchi/uid-<UID>/`

Important files:

- `pet.db`: per-user SQLite save
- `pet.lock`: per-user write lock
- `migration.json`: migration status marker
- `legacy-backups/`: backups created during legacy migration
- `exports/`: optional place for export artifacts

Permissions are created as restrictively as the platform allows:

- directories target `0700`
- files target `0600`

## Migration From Legacy Saves

Older builds stored pets in a username-keyed database, typically in locations such as:

- `XDG_DATA_HOME/runv-pet/gotchi.db`
- `XDG_DATA_HOME/runv-pet-data/gotchi.db`
- `~/.gotchi-data/gotchi.db`
- `./.gotchi-data/gotchi.db`

The new build can migrate those saves automatically.

Migration rules:

- it looks up the old row by the current display username
- it writes the migrated pet into the new per-UID database
- it keeps the old save intact
- it writes a JSON backup of the migrated pet
- it records migration information in `migration.json`
- it is idempotent: rerunning migration does not duplicate the pet

Manual migration command:

```bash
gotchi migrate
```

## Concurrency And Multiple Shells

The project is designed for users with multiple SSH sessions and terminals.

Protection in place:

- per-user lock file around writes
- SQLite transactions with `BEGIN IMMEDIATE`
- SQLite busy timeout configured
- WAL mode attempted where supported
- predictable single-user serialization of updates

In practice, two near-simultaneous commands from the same user should not corrupt the save.

## New Maintenance Commands

### `gotchi path`

Shows:

- resolved UID
- resolved username
- real home
- effective state/config/data paths
- active save path
- active lock path
- chosen config path

### `gotchi doctor --storage`

Checks:

- path resolution
- permissions summary
- SQLite integrity check
- save presence
- visible legacy migration candidates

### `gotchi migrate`

Forces a migration attempt from the legacy username-based save model.

### `gotchi export [FILE]`

Exports the current pet as readable JSON.

If no path is given, it prints JSON to stdout.

### `gotchi import FILE`

Imports a JSON backup of the current user's pet with strong validation.

Safety rules:

- rejects payloads whose `owner_uid` does not match the real current UID
- rewrites display username metadata to the current resolved account
- only imports into the current user's private save

### `gotchi line`

Prints one short line meant for login/profile integration.

Example:

- `Nyx esta por perto. Fome: ok. Humor: otimo.`
- `Corvus dormiu bem. Humor: bom.`

## Optional Login / Shell Integration

Opt-in snippet for bash/zsh-style interactive shells:

```bash
case "$-" in
  *i*)
    command -v gotchi >/dev/null 2>&1 && gotchi line 2>/dev/null
    ;;
esac
```

Characteristics:

- only runs in interactive shells
- easy to remove
- does not affect non-interactive scripts
- short output only

## Global Defaults For Admins

The app supports optional global base config files for shared defaults.

Read order:

1. `/etc/xdg/gotchi/gotchi.json`
2. `/etc/gotchi/gotchi.json`
3. per-user config file

Precedence:

- user config overrides global defaults
- global defaults are only a base layer

This lets Runv admins tune community-wide defaults without overriding user-specific choices.

## Testing

The automated suite covers:

- identity isolation by UID
- environment spoof resistance
- separate saves for separate simulated users
- migration from username-keyed legacy data
- save/load roundtrip
- private directory creation
- concurrent writes for the same user
- lock sequencing
- export/import validation
- `gotchi path`
- `gotchi doctor --storage`
- compatibility of existing commands
- hidden `-runv` rendering

Run:

```bash
python3 -m unittest discover -s tests -v
```

## Backup / Restore

Backup:

```bash
gotchi export my-pet-backup.json
```

Restore:

```bash
gotchi import my-pet-backup.json
```

Because ownership is validated by UID, a backup from one account is not silently accepted by another.

## Debugging Permissions

Useful commands:

```bash
gotchi path
gotchi doctor --storage
gotchi migrate
```

What to inspect:

- whether the resolved UID is correct
- whether the save path is inside the expected per-user state directory
- whether permissions are restrictive enough
- whether SQLite integrity reports `ok`
- whether a legacy database still exists and needs migration

## Known Limitations

- legacy migration still maps old data by username because that is all the old format had
- Windows local development uses a fallback identity path because `pwd` is Unix-specific
- the system does not yet expose any public wall, ranking, or read-only gallery
- no cross-pet interactions are implemented yet by design

## Future-Safe Direction

The new layout is ready for future social/read-only features without mixing private pet storage today.

Examples of future additions that are now easier to add safely:

- public memorial/cemetery
- public read-only showcase
- ranking or streak board
- admin-generated snapshots

Those features are intentionally not implemented in the private storage path now.
