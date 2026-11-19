# cli-generator

Claude Code plugin: a `cli-builder` skill that scaffolds new CLI tools or
refactors existing ones onto one shared architecture (Python + uv + Typer,
dual human/JSON output, AI-readable errors, optional parts — project config,
OS-keychain credentials, an `HttpProvider` base for external APIs, a database —
each behind a copier question, versions from git tags and the changelog written by
`antagor publish` from ticket titles (semver; no towncrier, no hand-made hooks), one local gate — `uvx --from "git+…/cli-generator.git@<template tag>#subdirectory=gate" gate check` —
that also proves the built wheel installs and reports the right version,
`auth status --check --json` in a cross-tool shape, and an enforced
`--help` contract).

## Layout

```
.claude-plugin/plugin.json    # plugin manifest
skills/cli-builder/           # the skill: SKILL.md + reference docs
                              #   (reference/standard.md: the Standard)
copier.yml                    # copier config; _subdirectory points at template/
template/                     # the actual copier template
```

## Using the skill

From the target package's directory, load this plugin for the session:

```bash
claude --plugin-dir /path/to/cli-generator
```

(or symlink it into `~/.claude/skills/cli-generator` to auto-load every
session without the flag), then ask for either:

- "create a CLI for X" → scaffold mode
- "refactor this script/package into our CLI architecture" → refactor mode
  (works on a feature branch, never directly on main — see SKILL.md step 0)

Both modes end by offering to publish: the skill prepares the local repo
and pushes it to Gitea (`https://homeserver.tailee01ab.ts.net:3000/bolandeu/<name>`,
the primary store; GitHub `bolandeu/<name>` is a private push mirror, nobody
pushes there). The first push creates the repo; the skill sends no message
to sysadmin. The skill then verifies that `uv tool install --index gitea=https://homeserver.tailee01ab.ts.net:3000/api/packages/bolandeu/pypi/simple <dist_name>`
works from the Gitea registry — the one-command install every generated README/SKILL.md
points other machines (and agents) at.

If it doesn't trigger automatically, invoke it explicitly:
`/cli-generator:cli-builder`.

See `skills/cli-builder/SKILL.md` for the exact workflow, and
`skills/cli-builder/reference/standard.md` (the Standard) for what every
package must and should be.

## Using the template directly

```bash
# `https://homeserver.tailee01ab.ts.net:3000/bolandeu/cli-generator.git` in place of `.` works from anywhere (add
# `--vcs-ref v1.0.0` to pin a template release)
uvx copier copy . <dest-dir> \
  --data package_name=mycli \
  --data project_name="My CLI" \
  --data description="Project-aware automation CLI" \
  --data author_name="Your Name"
cd <dest-dir>
uv sync
uv run mycli --help
uv run pytest
```

With default answers the package is minimal: what the Standard makes mandatory
(the bare command lists the commands, `--version`, global `--json` and the error
envelope, `doctor`, `auth status` with empty credentials, one example command, its
tests, `README.md`, `AGENTS.md`, `[tool.rb.install]`).
Each optional part is a copier question, off in a new package; a package made
before a question existed keeps that part on `copier update`:

| Question | Part | A package needs it when |
|---|---|---|
| `include_project` | project config, `init`, `config`, `status`, `--project` | the tool works on a project directory that keeps its own settings |
| `include_auth` | credentials, `auth login`/`logout`, providers in `auth status` | the tool calls an external service, or needs a key |
| `include_providers` | providers without credentials (asked when `include_auth` is off) | the tool calls an external service that needs no key |
| `include_http_provider` | `HttpProvider` and `httpx` (asked when providers are on) | a provider speaks HTTP |
| `include_db` | PostgreSQL/SQLite, Alembic migrations, `db` | the tool keeps data: journals, results, history, a cache of paid responses |
| `include_skill` | the package's agent skill, `skill install`, `--ai` | agents call the tool from other projects |
| `include_describe` | `describe --json` | the tool is in the tools catalog, or `clidocs` shows it |
| `include_contracts` | consumer contracts, the detach runner (asked when `include_describe` is on) | another tool, a Windmill flow or the platform relies on the CLI |

Each part's rules are in the Standard, Optional parts.

Once a project has been generated this way, pulling in later architecture
changes is `cd <dest-dir> && copier update` (requires the destination to be
a git repo — copier uses git to diff and merge template changes without
clobbering your business logic). Template releases are git tags on this
repo (`v1.0.0`, ...): `copier update` moves a project from the tag it was
generated with to the newest one, and re-runs the same verify loop
afterwards is how you know the merge was clean.
