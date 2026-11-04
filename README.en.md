# pokeldn-zh-hans

An official **Simplified Chinese (zh-Hans) language pack** plugin for [POKELDN](https://github.com/Decryptu/pokeldn).

POKELDN lets an ESP32 use local wireless (LDN) to talk to Pokémon games on the Switch for trading and mystery gifts. Its UI ships in English only; this plugin localizes everything — all UI strings (1896), hardcoded in-app English (mystery-gift modes/presets etc., 453) and the built-in documentation (48 pages).

> ⚠️ **AI-generated translation.** All translations in this pack were produced and proofread by an AI assistant, with official Simplified Chinese names AI-verified against [神奇宝贝百科 / 52poke](https://wiki.52poke.com). Minor inaccuracies or inconsistent wordings may exist. Corrections via [Issue](https://github.com/ZsyzLahz/pokeldn-zh-hans/issues) or [Pull Request](https://github.com/ZsyzLahz/pokeldn-zh-hans/issues) are welcome.

## Features

- **Full UI localization**: `strings.toml` (1896 entries) covering menus, settings, devices, bank, GTS, sessions and more.
- **Hardcoded text localized**: `messages.toml` (453 entries) covering the mystery-gift MODES/PRESETS, event-gift items, and other in-game strings (e.g. "Mystery Cards", "Nature Mints", "10 ANIV").
- **Docs fully translated**: `docs/` (48 markdown pages) mirroring the official Pokédex docs page-for-page with identical heading hierarchy, links and table structure.
- **Official names**: Pokémon, moves, abilities, items, berries, natures and marks follow the official Simplified Chinese translations from [52poke](https://wiki.52poke.com).

## Installation

pokeldn loads language packs through its "community plugin" mechanism — no modification to the app itself, applied after a restart.

1. Quit pokeldn (tray icon → Quit).
2. Copy this repository's `plugin/` directory into the language-pack folder:
   - Windows: `%APPDATA%\pokeldn\plugins\community-zh-hans\`
   - Other platforms: `~/.config/pokeldn/plugins/community-zh-hans/` (if your DATA dir differs, locate it per the official docs)
3. Open pokeldn → **Settings → App language** and select **简体中文** (Simplified Chinese).
4. Restart pokeldn as prompted.

The UI, mystery gifts and docs will then all be in Chinese.

> Alternatively, download `community-zh-hans.zip` from the [Releases](https://github.com/ZsyzLahz/pokeldn-zh-hans/releases) page, unzip it and drop it into the same plugin folder.

## Directory layout

```
pokeldn-zh-hans/
├── plugin/
│   ├── plugin.toml      # language-pack metadata (id/name/api/locale)
│   ├── strings.toml     # UI strings, 1896 entries
│   ├── messages.toml    # hardcoded in-app English, 453 entries
│   └── docs/            # built-in docs, 48 pages (all in Chinese)
├── scripts/
│   ├── build.py            # merges English strings.en.toml + shards → strings.toml
│   ├── build_messages.py   # merges msg_*.json → messages.toml
│   └── verify_docs.py      # validates docs heading levels/links/fences/EN residue
├── community-zh-hans.zip  # ready-made archive, unzip-and-install
└── README.md
```

## Language-pack metadata

`plugin.toml` follows the official pokeldn [language-pack spec](https://github.com/Decryptu/pokeldn/blob/main/docs/plugins.md) (API 1.9):

```toml
id = "community-zh-hans"
name = "简体中文"
version = "1.0.0"
api = "1.9"
locale = "zh-Hans"
strings = "strings.toml"
messages = "messages.toml"
documents = "docs"
description = "POKELDN 界面简体中文语言包（社区翻译）。"
author = "community"
```

## Simplified vs. Traditional

This pack targets **Simplified Chinese (zh-Hans)**. For Traditional Chinese, fork this repository, change `locale` to `zh-Hant`, and adjust wording per the official spec.

## Updating

- Bump the version in `plugin.toml`, following pokeldn's semantic-versioning conventions.
- After a pokeldn upgrade, new English strings may appear — that is expected. Add the new keys to `strings.toml`/`messages.toml` and release a new version.

## Rebuilding from source

This repo ships rebuild scripts (need Python 3.10+ with `tomllib`):

```bash
# 1. strings.toml — needs the official strings.en.toml as the source
#    Place the English strings at the same level as the script as the shard
#    source for part_*.toml, then:
python scripts/build.py

# 2. messages.toml — needs the msg_*.json of in-app English strings
python scripts/build_messages.py

# 3. Validate docs
python scripts/verify_docs.py
```

> Rebuilding is mainly for maintainers to review and regression-test; end users can just use the release archive.

## Credits & License

- Language-pack mechanism and plugin spec come from [pokeldn (Decryptu)](https://github.com/Decryptu/pokeldn).
- Official name verification references [52poke / 神奇宝贝百科](https://wiki.52poke.com).
- This is a community language pack, not affiliated with pokeldn officially.
- Distributed under the permissive terms of the pokeldn ecosystem (see upstream repo for details).