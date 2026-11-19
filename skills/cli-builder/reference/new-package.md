# Mode: new package

No CLI exists yet. Order: template, optional parts, own commands, gate. The rules are in the Standard
(`standard.md`); this file is only the order of actions.

## 1. Decide the answers

Three names, deliberately separate (Standard, Technology):

- `package_name` — the Python import package; for a new tool `rb_<slug>` (`rb_serp`).
- `cli_name` — the command users type; default `<slug>` (`serp`). Runtime code reads it from the installed
  console script (`core.version.cli_name()`), never from `__name__`.
- `dist_name` — the distribution (`[project] name`); `rb-<slug>` (`rb-serp`). Runtime code gets it from
  `_distribution.DIST_NAME`.

Also `project_name`, a one-line `description`, `author_name`, and `repository_url`: decide it now, before
generating. Default `https://homeserver.tailee01ab.ts.net:3000/bolandeu/<repo>`, `<repo>` = `package_name` with
`_` → `-`, unless the user names another. The install answers `install_homeserver_users` and `install_mac`
(Standard, Install): default homeserver user `rbtools` and Mac; a library publishes only
(`--data install_homeserver_users= --data install_mac=false`).

Ask the user what the package must do. That is the one piece of real logic the template does not provide.

## 2. Copy the template with the minimal defaults

The template source is the Gitea URL below (keep the `.git` suffix: without it copier takes the URL for a path).
It becomes `_src_path` in `.copier-answers.yml`, so every later `copier update` pulls tags from Gitea. Never use
a local path.

```bash
uvx copier copy https://homeserver.tailee01ab.ts.net:3000/bolandeu/cli-generator.git <dest-dir> --trust --defaults \
  --data package_name=<name> --data project_name="<Name>" \
  --data description="<one line>" --data author_name="<name>" \
  --data cli_name=<command> --data dist_name=rb-<slug> \
  --data repository_url=https://homeserver.tailee01ab.ts.net:3000/bolandeu/<repo>
```

Copier picks the latest release tag; `--vcs-ref vX.Y.Z` pins one. A local checkout as the source is only for
testing a template change.

## 3. Turn on only the parts the package needs

Each optional part is one copier question, off by default. Add `--data <question>=true` for the parts below that
the task needs, and nothing else. The Standard, Optional parts, holds each part's rules.

| Question | Turn on when | Standard section |
|---|---|---|
| `include_project` | the tool works on a project directory with its own settings | Project |
| `include_auth` | the tool needs a key; it brings `include_providers` | Credentials and providers |
| `include_providers` | the tool calls an external service | Credentials and providers |
| `include_http_provider` | a provider speaks HTTP; otherwise subclass `providers.Provider` | HTTP |
| `include_db` | the tool keeps data (journal, history, a cache of paid responses) | Database |
| `include_skill` | agents call the tool from other projects | Package skill |
| `include_describe` | `describe --json` is wanted (the catalog and `clidocs` read it) | Describe |
| `include_contracts` | another tool consumes this one under a contract | Consumer contracts |

## 4. Write the package's own commands

- Business logic goes in `src/<package_name>/core/services.py` (or modules under `core/`), never inside
  `commands/*.py`. A command parses arguments, calls a service, then calls `output.emit_success` /
  `output.guard`.
- A new command group is created with `output.group("...")`, never `typer.Typer(...)`.
- With providers: one module per service under `providers/`; a provider implements `health_check()`.
- With a database: tables in `core/tables.py` and a hand-written Alembic migration.
- A program `uv` cannot install (`ffmpeg`, `git`, another CLI): declare it in `[[tool.rb.external]]` and reach it
  through `core.deps.require_cli`.
- Depending on another of our tools: a version range in `dependencies` and `{ index = "gitea" }` in
  `[tool.uv.sources]`; never a git `tag =`, a `branch =` or a committed `path =`.
- A key several CLIs share: the provider reads the shared name through `legacy_env`; a new key goes to sysadmin as
  a request (`docs/contracts/sysadmin.md`, "Ключи").
- Do not edit `CHANGELOG.md`.

## 5. Gate before every commit

```bash
cd <dest-dir> && uv sync && uvx --from "git+https://homeserver.tailee01ab.ts.net:3000/bolandeu/cli-generator.git@<template tag>#subdirectory=gate" gate check && uv run <package_name> doctor
```

`<template tag>` is `_commit` in `.copier-answers.yml`. In the package the command is `[publish] gate_command` of
`.agents/antagor/antagor.toml`; that setting alone writes it, and no workflow runs it. The gate names the first failing
step with its output.
`uv sync` writes `uv.lock`; commit it. Run the gate before every commit, not only at the end.

Then publish: see "Publish" in `SKILL.md`.
