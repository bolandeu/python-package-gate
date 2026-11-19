# CLI Standard

What every CLI package of the Human must be (**Mandatory**) and should be (**Recommended**). A package agent reads it
once; the `cli-builder` skill says how to get there.

A **Mandatory** rule names the gate step that checks it; a package that fails it cannot be released. No gate step
checks a **Recommended** rule: a package may differ, and says how and why in its own `AGENTS.md`.

The gate is one command, run in the package root, with nothing added to the package:

```bash
uvx --from "git+https://homeserver.tailee01ab.ts.net:3000/bolandeu/cli-generator.git@<tag>#subdirectory=gate" gate check
```

`<tag>` is the template tag of the package (`_commit` in `.copier-answers.yml`), else the latest tag of
`cli-generator`. The gate prints each step by name; the first failure stops it with the step's output and the last line
`release: code failed` (exit 1), or `release: audit failed` (exit 3) when only the vulnerability audit failed. A green run
ends with `release: gate passed`.

A command below is written `<cli>`: the command a user types. `<CLI>` is that name in capitals, every non-alphanumeric
character as `_` (`sitemap-xml` → `SITEMAP_XML`).

## Technology

- **Mandatory** (gate: `build + install wheel`). The package is a Python distribution that `uv build` turns into a
  wheel; a tool has its command as the first entry of `[project.scripts]`, a library has no command and its top-level
  packages import.
- **Recommended.** The package requires Python 3.14 or newer (`requires-python = ">=3.14"`); the gate and the local
  tests run on 3.14. Why: one Python everywhere; a lower minimum nobody tests is a false promise.
- **Mandatory** (gate: `uv lock --check`). `uv.lock` is committed and matches `pyproject.toml`. Why: every machine and
  the gate install the same set.
- **Mandatory** (gate: `ruff check`). `uv run ruff check .` passes.
- **Mandatory** (gate: `ruff format --check`). `uv run ruff format --check .` passes.
- **Mandatory** (gate: `ty check`). `uv run ty check` passes.
- **Mandatory** (gate: `pytest`). `uv run pytest` passes.
- **Mandatory** (gate: `external dependencies`). Every program the code runs by a literal name (another CLI, `ffmpeg`,
  `git`, `npx`) is declared in `pyproject.toml` `[[tool.rb.external]]` with `name` and `why` (optional `required`,
  `min_version`, `check`), and every declared program is run. A program run in a way the scan cannot see (an injected
  runner, an absolute path) sets `detect = false`.
- **Recommended.** Commands use Typer. Why: the template's output and error layer is built on it.
- **Recommended.** A dependency the package's code calls into is capped below the next minor version the package is
  not verified against (`typer>=0.27,<0.29`), and the cap is raised only together with a green `fresh install` gate
  step. Why: an uncapped dependency's next minor lands on a user's machine before anyone runs the package.
- **Recommended.** Three names: the distribution `rb-<slug>`, the command `<slug>`, the import package `rb_<slug>`.
  Why: a generic distribution name collides with someone else's PyPI package.
- **Recommended.** The three names are separate, and nothing derives one from another: a package belongs to the family
  (the packages built to this Standard) by its distribution name `rb-*`, never by its command, and a package whose
  command differs from its slug is legal (`rb-llmkit` runs `llm`). A document names the tool by `x-rb-tool.tool`, a
  shell by that command; `dist` and `package` sit next to it in `x-rb-tool`. Why: a consumer that reads the command
  prefix for membership loses such a package.
- **Recommended.** The package runs on any machine without an agent, this plugin or our servers; the gate is a
  development tool, never a runtime dependency.
- **Recommended.** Use Python APIs (`pathlib`, `shutil`, `platformdirs`), never `os.system`, `shell=True` or a fixed
  POSIX path. Why: the same package runs on macOS, Linux and Windows.
- **Recommended.** A command reads as parse → call one core function → render; the logic lives below the commands.
- **Recommended.** Before the first call to another CLI, check that it is installed at its minimum version; a missing
  or older one fails with `DEPENDENCY_TOO_OLD` and an `action` that is a runnable install command.
- **Recommended.** A coverage floor (`fail_under`) that only goes up, and ruff's `S` (security) rules.

## Commands

- **Mandatory** (gate: `standard: commands`). `<cli>` with no arguments lists every command with the first line of its
  help and exits 0. Why: an agent explores a CLI by running it, and Click's default is a usage error with exit 2.
- **Mandatory** (gate: `standard: commands`). Every command and every group answers `--help` with exit 0.
- **Mandatory** (gate: `build + install wheel`). `<cli> --version` prints the version of the installed wheel.
- **Recommended.** The bare `<cli>` starts with `<name> <version> — <description>`; `<cli> <group>` alone prints the
  group's help and exits 0.
- **Recommended.** The help is the command reference: no other file (README, package skill) lists the commands.
- **Recommended.** The help of a command comes from its docstring, in this shape:

  ```
  Paint the targets in one color.

  A coat dries before the next one; each target gets every coat.
  coats: how many coats each target gets.

  Example: tool paint wall --coats 2
  -> wall: red, 2 coats
  ```

  1. Summary: the first sentence, on the first line, ending with «.».
  2. Description: the paragraphs after it, plain and short.
  3. Option line: «name: text» explains the option or argument `name` («first, last: text» for several).
  4. Example: «Example: <cli> <command path> …», one to three per command, each a real short command; an optional next
     line «-> <result>» says what it gives.
- **Recommended.** Every option and argument has a non-empty help text.
- **Recommended.** A change of a command's behaviour changes its help in the same commit.
- **Recommended.** Every command takes the global options before or after its name (`<cli> --json status` and
  `<cli> status --json`): `--json`, `--quiet`, `--verbose`, `--non-interactive`, `--version`, `--help`; a command that
  changes external state also takes `--dry-run` and `--confirm`.
- **Recommended.** A command that can prompt takes `--non-interactive` and then fails with an error instead of a
  prompt.
- **Recommended.** A command that changes external state irreversibly (deletes, overwrites a remote resource, restarts
  a service) previews with `--dry-run` before any side effect, asks before it acts, and under `--non-interactive`
  refuses without `--confirm`. Why: an agent that always passes `--non-interactive` must not destroy anything by
  accident.
- **Recommended.** Help and human messages are in English; a package may translate them, for the whole CLI at once.
  Machine-read values are never translated: JSON keys, enum values, error codes, command and option names.

## Output

- **Mandatory** (gate: `standard: json`). Every command that is not a group takes `--json`: its own `--help` or the
  root's lists it (a global option before the command is enough).
- **Recommended.** Under `--json`, stdout is one JSON object: `{"ok": true, ...}` with the command's fields on success,
  the error envelope (see Errors) on failure.
- **Recommended.** stdout carries data only; stderr carries everything else: human `Error:` lines, `--verbose`
  progress, logging (WARNING and above, DEBUG under `--verbose`), tracebacks. Why: `<cli> status > out.json` never
  captures an error as data.
- **Recommended.** A report (a health or audit result) prints its data whether or not it found a problem. A problem
  gives `ok: false` and the `error` object next to the full payload, and the exit code of that error.

  ```json
  {"ok": false, "error": {"code": "CREDENTIALS_UNHEALTHY", "message": "...", "action": "..."}, "tool": "mycli", "credentials": [...]}
  ```
- **Recommended.** Output is the same on a terminal and in a pipe: no pager, no prompt except the confirmation of a
  destructive command, nothing shown only to a human watching.
- **Recommended.** A command that returns many records prints JSON Lines (one object per line) under `--json`. Why: a
  reader can start before the command ends, and a cut output stays readable.

## Errors

- **Mandatory** (gate: `standard: errors`). Under `--json` a failure prints the error envelope on stdout:

  ```json
  {"ok": false, "error": {"code": "AUTH_REQUIRED", "message": "Authentication is required for provider 'openai'.", "action": "Run 'mycli auth login'."}}
  ```

  `code` and `message` are always there; `action` is there when a concrete next command can unblock the caller.
- **Mandatory** (gate: `standard: errors`). A usage error (an unknown option or command, a missing argument, a bad
  value) exits 2. Under `--json` anywhere before `--` it is the error envelope `INVALID_ARGUMENTS`; without `--json`
  it stays the usage message on stderr.
- **Mandatory** (gate: `standard: errors`). Every exit code is one of this table:

  | Exit | Meaning |
  |---|---|
  | 0 | success |
  | 1 | general error (also an unexpected one, and an answer «no» to a confirmation) |
  | 2 | invalid arguments |
  | 3 | authentication error |
  | 4 | project not initialized |
  | 5 | provider error: an external service (network, timeout, 5xx, 429, a bad body) |
  | 6 | the CLI is too old for this project or database |
- **Recommended.** Use these error codes where one fits; a new code is for a cause none of them names.

  | `error.code` | Exit | When |
  |---|---|---|
  | `INVALID_ARGUMENTS` | 2 | bad arguments; also `--non-interactive` without `--confirm` |
  | `AUTH_REQUIRED` | 3 | a service answers 401/403, or no credential is there |
  | `CREDENTIALS_UNHEALTHY` | 3 | `auth status`: a required credential is not ok, or any is invalid or expired |
  | `PROJECT_NOT_INITIALIZED` | 4 | a project command outside a project |
  | `PROVIDER_ERROR` | 5 | an external service failed after retries; carries `provider` and `status` |
  | `DATABASE_UNAVAILABLE` | 5 | the configured database is unreachable, rejects the CLI or is not PostgreSQL |
  | `CLI_TOO_OLD` | 6 | the project's `min_version` or the database's revision is newer than the CLI |
  | `DATABASE_NOT_MIGRATED` | 1 | the database is behind the CLI's migrations |
  | `DEPENDENCY_TOO_OLD` | 1 | another CLI this one runs is missing or too old |
  | `CREDENTIAL_STORE_UNAVAILABLE` | 1 | the OS keychain is unusable for a write or a delete |
  | `ABORTED` | 1 | the user answered «no» to a confirmation |
  | `UNEXPECTED` | 1 | any exception nothing mapped |
- **Recommended.** An exception nothing mapped still gives the envelope under `--json`: `UNEXPECTED`, exit 1, the
  `action` says to re-run with `--verbose`, the traceback goes to stderr under `--verbose` only. The same `UNEXPECTED`
  cause seen twice deserves its own code.

## Health

- **Mandatory** (gate: `standard: health`). `<cli> doctor --json` prints the readiness report and exits 0 (the report is
  the result):

  ```json
  {"ok": true, "healthy": false, "checks": [{"name": "config", "ok": false, "detail": "..."}]}
  ```

  `healthy` is true when every check is `ok`; `detail` is optional.
- **Mandatory** (gate: `standard: health`). Every CLI has `<cli> auth status --json`. It prints the credentials report
  (`ok`, `tool`, `version`, `checked_at`, `credentials`) with an exit code from the table; a CLI that needs no keys reports
  `"credentials": []` and exits 0. The entries are in Credentials and providers.
- **Recommended.** `doctor` checks what the CLI needs to run: its version, the project and its config, the credential
  store, every external program (`external:<name>`), the database. Why: it is the first command an agent runs when
  something fails.
- **Recommended.** The two report shapes are a contract with sysadmin (`docs/contracts/sysadmin.md` of
  `cli-generator`); a change of shape is a breaking change.

## Credentials

- **Mandatory** (gate: `secret scan`). No key, token or password is in the repo or its git history. The scan is
  `gitleaks` over the whole history (install it: `brew install gitleaks`; without it the step is skipped with a
  notice). A fake test value is allowed in the root `.gitleaks.toml` as one exact string, never a path or a disabled
  rule. Any other finding is a leaked key: tell the Human its name and file; revoking it is the Human's. When the
  Human has revoked a key that stays in history, `.gitleaksignore` may hold exactly one fingerprint line per finding
  (`<commit>:<file>:<rule>:<line>`, no value); never a path, a disabled rule or the key's value.
- **Recommended.** `.env` and `.env.*` are in `.gitignore`.
- **Recommended.** A key never goes on the command line or into a project file: it comes from an environment variable
  (or, on a dev machine, the OS keychain). Why: arguments show in the process list and in shell history.
- **Recommended.** A new key is a request to sysadmin: the env name, where to get the value, who needs it. The value
  never goes into the repo, a file or the request.

## Install

- **Mandatory** (gate: `install section`). `pyproject.toml` has `[tool.rb.install]`, and it has no other key:

  ```toml
  [tool.rb.install]
  homeserver = ["rbtools"] # homeserver users to install for; [] = build and publish only
  mac = true               # install on the Mac
  extras = ["tui"]         # optional: extras to install
  ```

  A library has `homeserver = []` and `mac = false`. Why: sysadmin's tool-updater installs from this section.

  Choose the values by who runs the command:
  1. An agent or an automation on homeserver runs it: `homeserver = ["rbtools"]`.
  2. The Human or an agent on the Mac runs it: `mac = true`.
  3. Nobody runs it (a library): `[]` and `false`.
  4. Unsure: both on.
- **Mandatory** (gate: `build + install wheel`). The wheel installs into an empty venv with exactly the `uv.lock` set
  (nothing resolved from an index), `uv pip check` passes, and `<cli> --help` works. A package that `[tool.uv.sources]`
  takes from an explicit index installs from that index only, at its locked version. Why: a same-named PyPI package
  cannot replace one of ours.
- **Recommended.** A package depends on another of ours by a compatible range from the Gitea registry, never by a git
  tag, a branch or a committed `path =`:

  ```toml
  [project]
  dependencies = ["rb-yandex-oauth>=0.2,<0.3"]

  [[tool.uv.index]]
  name = "gitea"
  url = "https://homeserver.tailee01ab.ts.net:3000/api/packages/bolandeu/pypi/simple"
  explicit = true

  [tool.uv.sources]
  rb-yandex-oauth = { index = "gitea" }
  ```
- **Recommended.** The package lives in Gitea, `https://homeserver.tailee01ab.ts.net:3000/bolandeu/<repo>`; nobody
  pushes to GitHub (a private mirror follows by itself).
- **Recommended.** The installation on machines is sysadmin's (tool-updater, the Mac agent, `tools.toml` overrides): the
  package only declares the section. The README's install line is
  `uv tool install --index gitea=https://homeserver.tailee01ab.ts.net:3000/api/packages/bolandeu/pypi/simple <dist>`.

## Docs

- **Mandatory** (gate: `standard: docs`). The package has a `README.md` and an `AGENTS.md`.
- **Recommended.** `README.md` says what the tool is for, how to install it and one first command; it does not list the
  commands (the bare `<cli>` does).
- **Recommended.** `AGENTS.md` links this Standard by its Gitea URL
  (`https://homeserver.tailee01ab.ts.net:3000/bolandeu/cli-generator/src/branch/main/skills/cli-builder/reference/standard.md`)
  and cites its sections by name; it holds only what is particular to the package (and every Recommended rule it does
  not follow, with the reason).

## CI

The gate is `gate check`, run on the machine that builds the package: the command at the top of this Standard.
There is no second gate and no CI file — no workflow under `.gitea/workflows/`, none under `.github/`. Gitea stores
releases and nothing else; it runs no test. A release exists only after a green gate, a red one stops the tag. Why: a
remote run of the same gate tells nothing the local one did not, and every copied workflow drifts from the template
that would have to keep it.

## Release

- **Mandatory** (gate: `build + install wheel`). The version is the latest git tag `vX.Y.Z` (a PEP 440 version), read
  at build time: with a tag in reach the wheel is never `0.0.0`. A new repo is tagged `v0.1.0` on its first commit.
- **Mandatory** (gate: `fresh install`). The package installs into an empty environment whose dependencies come from
  the package index, as on a new machine — not from `uv.lock`. A tool prints the version being released for
  `<cli> --version`, `<cli> --help` works and `<cli> describe --json` answers its document; a package without the
  Describe part answers the command as absent, and the step stays green. A library imports every top-level package
  and `importlib.metadata` reports that version. Why: the wheel step installs the locked set, so it stays green while
  a dependency's new minor release breaks every fresh install.
- **Mandatory** (gate: `vulnerability audit`). `osv-scanner` finds no known vulnerability in `uv.lock` (install it:
  `brew install osv-scanner`; without it the step is skipped with a notice). This failure alone ends with
  `release: audit failed`, exit 3: bump the dependency, the code is fine.
- **Recommended.** No `version =` in `pyproject.toml` and no version literal in the code: the code reads
  `importlib.metadata.version()`.
- **Recommended.** A version moves only through Antagor's release. Nobody pushes or tags by hand, edits
  `CHANGELOG.md` or adds changelog fragments. The Antagor config holds the docstring check in `checks`, the gate in
  `heavy`, and no gate command; `[publish]` has `gate = "local"` with the gate command: the gate runs on this machine
  before the tag, and a red gate means no tag. No package file holds a gate command (Standard, CI).
- **Recommended.** A user-visible change is a task whose title says what changed for the user.
- **Recommended.** Versions follow SemVer over the public surface: commands, options, the `--json` shapes, exit codes,
  error codes, the `auth status` and `describe` documents, the Python API.

  | Change | From 1.0.0 | At 0.x |
  |---|---|---|
  | a fix, no surface change | patch | patch |
  | a new command, option or field; the old behaviour intact | minor | patch |
  | anything removed, renamed or changed | major | minor |
- **Recommended.** Deprecate before removing: the old form keeps working with a warning on stderr, a task titled
  `deprecate …` says so, and the next breaking release removes it.

## Optional parts

A package turns on only the parts it needs. In the template each part is a copier question, off in a new package; a
package made before a question existed keeps that part on `copier update`.

### Project

**When.** The tool works on a project directory that keeps its own settings.

**Turn on.** `include_project`; a package not from the template adds the project folder and the commands below.

- **Recommended.** The CLI is installed once and serves any number of projects; a project holds only config and data,
  never the CLI's code or venv.
- **Recommended.** Project config is `<project>/.<package>/config.toml` (committed; never a secret); generated state is
  `<project>/.<package>/state.json` (not committed); user config is in the OS user config dir (`platformdirs`).
- **Recommended.** A project command finds the project by walking up from the current directory, or takes
  `--project PATH`; outside a project it fails with `PROJECT_NOT_INITIALIZED` (exit 4).
- **Recommended.** Commands `init` (with `--non-interactive`), `status`, `config get|set|list`.
- **Recommended.** The config has `[cli] min_version`: an older CLI fails with `CLI_TOO_OLD` (exit 6, the `action` is
  `uv tool upgrade <cli>`), and `doctor` reports a `cli_compat` check instead of failing. A dev build (`0.0.0…`) skips
  the check.

### Credentials and providers

**When.** The tool calls an external service, or needs a key.

**Turn on.** `include_auth` (the providers come with it; `include_providers` alone gives providers without credentials),
or by hand: a provider per service and `auth login|logout`.

- **Recommended.** One env name per key: `<CLI>_<PROVIDER>_<FIELD>` (`SERP_XMLRIVER_API_KEY`). It is also the key's name
  in Doppler `tools/prd`, the source of every production key (`docs/contracts/sysadmin.md` of `cli-generator`,
  «Ключи»). Why: the wrappers run the CLI under `doppler run` with no renaming.
- **Recommended.** The CLI looks for a key in this order: argument, env, OS keychain, then a fallback env name the
  provider declares. Never in project or user config.
- **Recommended.** The OS keychain (`auth login`) is a local dev override; a key only in the keychain is a violation.
- **Recommended.** The namespace of keys is the command name, not the import package: keychain service
  `<cli>:<provider>`, env prefix `<CLI>_`. Why: it is the name a user knows, and it survives a package rename.
- **Recommended.** A key several CLIs share (Google service account, S3, Telegram, GitHub) has one env name without a
  CLI prefix; each provider declares it as its fallback name. A provider may read another CLI's stored key, read-only.
- **Recommended.** A credential is a named set of fields per provider (`{"api_key": ...}`, a session's cookies and
  token, a user and password per deploy target), all in one store. A per-target provider stores one credential per
  target as `<kind>:<target>` (`auth login --provider deploy:example.com`; env `<CLI>_DEPLOY_EXAMPLE_COM_PASSWORD`).
- **Recommended.** Each integration (an HTTP API, a vendor SDK, a local binary) is a provider: it maps the vendor's
  failures onto `AUTH_REQUIRED` and `PROVIDER_ERROR`, so nothing above it sees a vendor exception.
- **Recommended.** Each provider has a health check: one cheap, read-only, unbilled call within 10 s (its own client
  timeout), no retries, that proves the credential works.
- **Recommended.** Each `auth status` entry has this shape; `--check` runs the health checks, `--provider NAME` limits
  the report:

  ```json
  {"provider": "xmlriver", "required": true, "fields": ["user", "token"], "source": "env",
   "source_ref": "SERP_XMLRIVER_USER, SERP_XMLRIVER_TOKEN", "status": "ok", "expires_at": null,
   "quota": {"remaining": 1840, "limit": null, "unit": "requests"}, "message": null}
  ```

  1. `source`: `env`, `keychain`, `file` or `missing`; `source_ref` names the env vars, keychain service or file, never
     a value (messages are scrubbed of values too).
  2. `status`: `missing` or `unchecked` without `--check`; with it `ok`, `invalid` (auth refused), `unreachable`,
     `expired` (a past `expires_at`) or `quota_exhausted`.
  3. Exit 0 when every required provider is `ok` or `unchecked`; exit 3 with `CREDENTIALS_UNHEALTHY` (and the full
     report) when a required one is anything else or any is `invalid` or `expired`.
  4. A per-target provider gives one entry per stored target (`provider: "deploy:example.com"`); with none stored, one
     `missing` entry.

### HTTP

**When.** A provider speaks HTTP.

**Turn on.** `include_http_provider` (asked when providers are on; it brings `httpx`), or one shared HTTP base class of
your own.

- **Recommended.** One base for every HTTP provider: 401/403 → `AUTH_REQUIRED` (the `action` names the login command);
  429, 502, 503, 504, timeouts and connection errors are retried with exponential backoff (honouring `Retry-After`),
  then `PROVIDER_ERROR`; any other 4xx/5xx → `PROVIDER_ERROR` with the HTTP `status`; a body that is not JSON where JSON
  is expected → `PROVIDER_ERROR`.
- **Recommended.** A `User-Agent` of `<cli>/<version>` and a 30 s timeout. Why: a stuck service cannot hang an agent.
- **Recommended.** Request and retry lines go to the log, shown under `--verbose`.

### Database

**When.** The tool keeps data: journals, results, history, a cache of paid responses.

**Turn on.** `include_db`, or by hand: SQLAlchemy Core, Alembic and psycopg 3 (no ORM, no hand-rolled migrations), and
the `db` commands below.

- **Recommended.** All the tool's data goes through this layer, caches included; data kept elsewhere is the tool's
  decision, with its reason in its `AGENTS.md`. Why: Mac and homeserver do not pay twice for one response.
- **Recommended.** `<TOOL>_DATABASE_URL` set → PostgreSQL (the shared base, the URL from Doppler); set but unreachable,
  rejected or not PostgreSQL → `DATABASE_UNAVAILABLE` (exit 5), never a fallback to SQLite. Not set → SQLite in the user
  data dir, or at `<TOOL>_DB_PATH`.
- **Recommended.** Every table, view, index and constraint starts with `<tool>_`; the tool changes only its own objects,
  through its own migrations, tracked in `alembic_version_<tool>`.
- **Recommended.** Every table has a single-column primary key (a surrogate `id`; the natural key as a unique
  constraint) and says what its rows are: `data` (lost when deleted) or `cache` (fetched again). Cache tables live in
  the PostgreSQL schema `cache`, data in `public`.
- **Recommended.** Another tool, Directus or a report reads only the views `<tool>_v1_*`, never the tables. A view's
  columns never change: a new shape is a new `<tool>_v2_*` view next to the old one, and `v1` goes only after every
  reader moved.
- **Recommended.** Tools link records by normalized natural keys (a phrase: NFKC, lower case, ё→е, collapsed spaces; a
  URL or domain: no scheme, `www.`, port or trailing slash, IDN as Unicode), stored in their own indexed column next to
  the original text.
- **Recommended.** SQLite migrates on open; PostgreSQL never migrates implicitly: `<cli> db upgrade`. Opening a base
  that is behind gives `DATABASE_NOT_MIGRATED` (exit 1); one at a revision the CLI does not know gives `CLI_TOO_OLD`
  (exit 6).
- **Recommended.** Every migration works with the previous release's code (expand, then contract): add first, switch
  the code, drop or rename the old thing only in a later release.
- **Recommended.** Commands `db status`, `db upgrade [--dry-run]`, `db import-sqlite [PATH] [--dry-run]`, and
  `db push [--dry-run]` for append-only tables from a dev SQLite to production (`<TOOL>_PROD_DATABASE_URL`). `doctor`
  reports `database` and `database_schema`.
- **Recommended.** An agent never runs anything against production (`db push`, its dry run included, a read through
  the production URL, ssh to the server): it gives the Human the exact command.
- **Recommended.** Tests against PostgreSQL run only in a throwaway container with its own name, on a port Docker
  assigns, removed afterwards.

### Package skill

**When.** Agents call the tool from other projects.

**Turn on.** `include_skill`; a package not from the template adds a `SKILL.md` to its package data and the commands
below.

- **Recommended.** The skill ships in the wheel, so the installed tool serves it anywhere: `<cli> --ai` prints it,
  `<cli> skill install --tool claude-code|agents [--project]` installs it into an AI tool's skill directory.
- **Recommended.** It says when to take the tool, how to install it and what is particular to it, and names the
  destructive commands with the rule to get the user's yes before running one with `--confirm`. It never lists the
  commands; the rules common to every package stay here, not in each skill.
- **Recommended.** Extra skills for kinds of work (Agent Skills format) also ship in the package data; each has the
  frontmatter `name` `<cli>-<name>` and a `description`, and `skill install` installs them all.

### Describe

**When.** The tool is in the tools catalog, or `clidocs` shows it.

**Turn on.** `include_describe`; otherwise a `describe` command built on the CLI framework's own command tree.

- **Recommended.** `<cli> describe --json` prints an [OpenCLI](https://opencli.org) 0.1 document on one line, bare: the
  one `--json` output without the `{"ok": ...}` envelope.
- **Recommended.** The document is introspected from the commands, never written by hand: commands, options,
  arguments, `arity`, `acceptedValues`, and `exitCodes` from the table in Errors. What OpenCLI has no field for goes
  into `metadata` as `x-rb-*`: the per-parameter fields below, and on the root command the tool names, env vars, data
  tables and views, external programs and skills.
- **Mandatory** (gate: `standard: params`). Every option and every argument carries `x-rb-type`: a Typer type name
  from this closed list — `boolean`, `str`, `int`, `float`, `choice`, `path`, `file`, `datetime`, `int range`,
  `float range`. A new name in the list is an additive change.
- **Mandatory** (gate: `standard: params`). Every option and every argument carries `x-rb-default`: the value, or
  `null` when the parameter has no default, or its default is computed at run time.
- **Mandatory** (gate: `standard: params`). `x-rb-multiple` is present and `true` iff the parameter is repeatable or
  variadic; absent means single.
- **Recommended.** A hidden command, option or argument carries `hidden: true`; absent means visible. It is an
  OpenCLI field; the template has emitted it since v1.5.0.
- **Recommended.** Each `x-rb-skills` entry names the skill, describes it and points at its directory in the
  installed distribution, so a consumer reads the skill text with no extra call.
- **Recommended.** It is public API: it changes only by adding fields.

### Consumer contracts

**When.** Another tool, a Windmill flow, the Astro build or the platform relies on the CLI.

**Turn on.** `include_contracts` (asked when `include_describe` is on: a contract reads `describe --json`), then put the
consumer's contract file in the package; the gate runs every one it finds.

- **Mandatory** (gate: `contracts`). Every contract `tests/contracts/<consumer>/<provider>.yaml` (format
  `contract: 1`) passes; the gate names each failing case `<consumer>:<section>:<name>`.
- **Recommended.** The consumer writes its contract (the source is the consumer's repo, the tool keeps a copy, both
  through the Human); the tool's agent never edits it to make it pass.
- **Recommended.** A contract has `static` (commands, options, exit codes, env names against `describe --json`), `run`
  (the CLI in-process, offline and keyless: a case that tries the network fails) and `view` (view columns), and applies
  inside its `provider_range`. Placeholders and offline data come from the tool's `tests/contracts/fixtures.yaml`.

### Detach

**When.** Agents start a command that runs longer than a couple of minutes (the gate, PostgreSQL tests, a big import).

**Turn on.** `include_contracts` (the detach runner comes with the contracts), or any runner that starts the command in a
new session and records its result.

- **Recommended.** Start it detached (`scripts/run_detached.sh <label> <command...>`) and follow it with
  `scripts/runs_status.sh`: pid, stdout and stderr logs and the exit code per label, in the user state dir. Why: a
  command in the agent's own shell dies when the turn is interrupted.
