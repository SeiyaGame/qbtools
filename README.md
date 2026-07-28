# qbtools

Bulk-edit qBittorrent torrents over the Web API (trackers, tags, category, save
path, name) on selections filtered by category, tag, state, name or tracker.
Every write is a dry-run by default: you see the plan, then add `--run` to apply.

Commands read noun-verb: `qbt.py <field> <verb>`, e.g. `qbt.py tags remove obsolete`.
Fields are `trackers | tags | category | savepath | name`; verbs are
`replace | add | remove | set`. Each field only exposes the verbs it supports
(multi-valued: add/remove, single-valued: set, all: replace). `qbt.py fields` lists them.

## Setup

Enable the Web UI in qBittorrent (Tools > Options > Web UI), then:

```bash
pip install -r requirements.txt
cp config.example.toml config.toml   # edit host/port/username/password
python qbt.py ping                   # test the connection
```

## Inspect (read-only)

```bash
python qbt.py list --category linux --state seeding
python qbt.py list --category linux --trackers
python qbt.py list --category linux --all
python qbt.py hosts --tag iso
python qbt.py urls --category Torr9
```

- `list` shows the matching torrents; `--trackers` adds each tracker URL, `--all` also shows the DHT/PeX/LSD pseudo-trackers.
- `hosts` lists the distinct tracker hosts across the selection.
- `urls` lists tracker URLs deduped with per-URL torrent counts.

## Edit (dry-run, add `--run` to apply)

```bash
python qbt.py trackers replace old.tracker.org new.tracker.org --category linux
python qbt.py trackers replace "https://tracker\.torr9\.net/announce/.*" "https://tk.tr4ker.net/announce/NEWKEY" --regex --tag Torr9
python qbt.py trackers add "https://backup.tracker.net/announce" --state seeding
python qbt.py trackers remove dead.tracker.org

python qbt.py category set Torr9 --tag torr9
python qbt.py category replace linux archived-linux
python qbt.py tags add favorite --category linux
python qbt.py tags remove obsolete
python qbt.py savepath set /data/moved --category linux
```

- `--regex` treats the match as a Python regex (replacement can reference groups: `\1`).
- `category list` / `tags list` show what qBittorrent already knows.

## Selection flags (shared by every command)

`--category/-c`, `--tag/-t`, `--state/-s`, `--name/-n`, `--tracker`, `--hash/-H` (repeatable).

For `--category`/`--tag`, pass `''` to match uncategorised / untagged; omit to match any.

## Layout

```
qbt.py                 # launcher (also: python -m qbtools)
qbtools/
  cli.py               # Typer commands (thin: shared filters + write pipeline)
  config.py            # config.toml -> Settings/QbitConfig
  models.py            # TorrentInfo/Tracker/Change, enums, TorrentFilter
  client.py            # qbittorrent-api wrapper -> domain models
  engine.py            # Plan + apply (dry-run is the same computation)
  ui.py                # rich rendering
  registry.py          # self-registering plugin base
  operations/          # replace / add / remove / set   (auto-discovered)
  fields/              # trackers / tags / category / savepath / name (auto-discovered)
```

- Add an operation: drop a `FieldOperation` subclass in `operations/`; it becomes a verb under every field whose actions include it.
- Add a field: drop a `TorrentField` subclass in `fields/` (its `values()`, `apply()` and supported `actions`); it becomes the `qbt.py <field>` command group.
