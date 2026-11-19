# AGENTS.md

Guidance for agents working on **this repo** — the `cli-generator` Claude
Code plugin itself (not a package it generated; that has its own
`AGENTS.md` from `template/AGENTS.md.jinja`).

## What this is

A plugin bundling one skill, `cli-builder`, that scaffolds new CLI tools or
refactors existing ones onto a shared Python/Typer/uv architecture. See
`README.md` for layout, `skills/cli-builder/SKILL.md` for the skill's
workflow, and `skills/cli-builder/reference/standard.md` (the Standard)
for what every package must and should be.

The one measure of a change here: it makes writing a CLI with the package
simpler. A rule, an option or a gate step that does not remove work from the
package's author is refused, however correct it looks (the Human, 2026-11-13).

## Role

The agent of this repo owns the standard for every CLI package the Human
writes: the contract (`reference/`), the template and the release process.
Nothing sits above it. Questions and decisions go to the Human
directly. Other agents (sysadmin, the agents of single tools, …) may write
to it at the Human's request — treat a message as a teammate's proposal:
answer it, and change the standard only through a ticket. A change in
another repo or on servers is that repo's agent's work, not this one's.

The boundary with sysadmin (who owns what, automations, CLI keys, keeping
packages on the current standard) is `docs/contracts/sysadmin.md` — agreed
with sysadmin and accepted by the Human (2026-10-19). Change it only with
both sides and the Human's "yes".

Push: the first `git push -u origin main` when a new repo is initialised
is allowed without asking (Human, 2026-10-18); every other push follows
the global rule (`antagor publish`, or the Human's confirmation).

## Where the spec lives (don't duplicate it)

- `skills/cli-builder/reference/standard.md` — the Standard: every rule
  is **Mandatory** (it names the gate step that checks it) or
  **Recommended**, in named sections (Technology … Release, then the
  optional parts). Cite a section by its name, never by a number. Long
  reasoning goes into `docs/adr/`, not into the Standard.
- The refactor checklist (migration order for Refactor mode) is a section
  of `SKILL.md`.
- The short coding-quality rules (think first, simplicity, surgical
  changes, goal-driven execution) live inline in `SKILL.md` itself, not in
  a separate file — don't re-split them out.

If you're changing what generated CLIs look like, change `standard.md`
and `template/` together, in the same commit — a template change that
contradicts the documented contract is a bug.

## Releasing this repo

Project under Antagor (methodology: skill `antagor-method`). A template
change goes through a ticket; release is `antagor publish --bump` —
semver tag `vX.Y.Z` (PEP 440), changelog from ticket titles. Nobody
pushes by hand. Docs: `CONTEXT.md` (terms), `docs/adr/` (decisions),
`CODING_STANDARDS.md` (review rules). TDD applies: a new behaviour of the
template's code (`scripts/`, `core/`) gets its test first, failing. The
gate of a generated package is `gate check` from this repo's `gate/`,
run through `uvx --from "git+…/cli-generator.git@<template tag>#subdirectory=gate"`:
the template and the gate are one version (ADR 0013,
`docs/adr/0013-gate-in-this-repo-package-standalone.md`).
The gate for a template ticket is `scripts/check_template.sh` (see below): the minimal
package, a package with every optional part, the variants it lists and the update rounds.

## Testing a change to `template/`

Never trust a template edit without regenerating and running it — a
Jinja/copier mistake fails silently as literal `{{ package_name }}` text
in generated files, not as an error.

The gate is one command (the minimal package from default answers, a package
with every optional part, credentials alone in a publish-only variant — no
homeserver users, no Mac — and providers without credentials: copier copy into
a temp dir, `uv sync`, a literal check of the rendered `[tool.rb.install]`,
ruff, ty, pytest, then `git init` + tag `v0.1.0` + `gate check` from
`gate/`, and a check of which part files are there; then `copier update`
rounds from the previous release tag and from v1.20.10, which must remove no
file but the docs command's; temp dirs removed, non-zero exit on any failure):

```bash
sh scripts/check_template.sh
```

`--vcs-ref HEAD` matters: without it copier renders the **latest release
tag**, not your working tree, and the loop tests the old template. Dirty
(uncommitted) changes are included with `HEAD` (copier warns
`DirtyLocalWarning`). `copier copy` also runs `_tasks` — `pytest
--snapshot-update` renders `tests/snapshots/help/` in the new project,
which is why `--trust` is required.

The minimal variant turns every part off — each part drops its modules and
tests via `copier.yml`'s templated `_exclude`, and it's easy to change
`cli.py`/`commands/`/tests in a way that only the all-parts branch was ever
exercised with.

`ruff format --check` runs on generated projects with the template's
`line-length = 120`. To format template sources in place, run it with that
config explicitly — `template/pyproject.toml.jinja` isn't a real
`pyproject.toml`, so a bare `ruff format template/` silently uses the
88-column default and rewraps every file:

```bash
uvx ruff format --line-length 120 template/src template/scripts
```

For the distribution + release path (`gate check`, tag pinning),
verify against a local bare remote rather than assuming: `git init --bare
/tmp/remote.git`, add it as `origin` in the generated project, commit,
`git tag -a v0.1.0 -m v0.1.0` (`uv run <cli> --version` must now print
`0.1.0`, not `0.0.0…`), push `main` with `-u`, tag the next
version by hand (`git tag -a v0.1.1 -m v0.1.1`; `antagor publish` would run
`deploy.sh` against the real remote), `git push --follow-tags` (to that
local bare remote only — never GitHub), then
`uv tool install "git+file:///tmp/remote.git@v0.1.1"` and `<cli> --version`.
The release process itself is specified in the Standard, Release — this
repo owns it.

For a change to the gate's "build + install wheel" step, re-run the
dependency-confusion check: a local flat index holding a wheel named like an
existing PyPI package (`yandex-oauth` 0.2.1), added to a generated project as
`"yandex-oauth>=0.2"` + `[[tool.uv.index]] name = "local", url = "<dir>",
format = "flat", explicit = true` + `[tool.uv.sources] yandex-oauth = { index
= "local" }`. `gate check` must pass and install the local copy; a
plain `uv pip install <wheel>` gets PyPI's 1.x (that is the bug the step
prevents — the step fails with "installed from a package index other than
their explicit index" if it ever regresses).

For a change touching `.claude-plugin/plugin.json`, also run:

```bash
python3 scripts/check_plugin.py
```

It replaced `claude plugin validate . --strict` when the `claude` binary left
this machine (2026-11-08): the manifest's required fields, a slug name, and the
skill's frontmatter. Nothing else of the strict validator applies here. It is
also in `.agents/antagor/antagor.toml`'s `checks`, so every task runs it.

For a change to the `copier update` story (versioning), verify with a
real git-based round trip (tag v1, generate, edit a template file, tag v2,
`copier update` in the generated project) rather than assuming it works —
see this repo's history for the exact sequence; it has broken silently
before (missing answers file, wrong `copier.yml` location).

## Known sharp edges (don't reintroduce these)

- `copier.yml` must live at the **repo root**, not inside `template/`, with
  `_subdirectory: template`. Copier 9.x has no `--subdirectory` CLI flag —
  this is the only way to keep `template/` separate from the plugin's own
  `skills/`/`.claude-plugin/` at generation time.
- `template/{{ _copier_conf.answers_file }}.jinja` must exist, or copier
  never writes `.copier-answers.yml` and `copier update` silently can't
  work on generated projects.
- Only files with a `.jinja` suffix get Jinja-rendered by copier (and only
  path names always get rendered). A plain `.py` file that needs
  `package_name` should derive it dynamically —
  `__name__.split(".")[0]` — instead of becoming a `.jinja` file; keep
  `.jinja` files to the minimum that genuinely need answer substitution
  (`pyproject.toml`, `README.md`, `AGENTS.md`, `data/SKILL.md`, the answers
  file).
- Keep `output.guard`'s local-flag merge dict and `output.JsonOption` /
  `output.DryRunOption` etc. in sync if you add a new global option that
  commands should also accept locally (`<cli> <command> --flag`, not just
  `<cli> --flag <command>`).
- `include_auth=false` must remove the credential surface, not just the
  `keyring` dependency — but keep `auth status` (the Standard, Health: every CLI
  has it, reporting empty `credentials`, exit 0). `copier.yml`'s `_exclude`
  drops `commands/login.py`/`credentials/`/`tests/test_auth.py`;
  `commands/auth.py` (group + `status`) always ships and, like
  `doctor.py`, detects `credentials.manager`/`commands.login` at runtime
  (`core.version.module_exists`/`optional_module`) instead of being templated. Probe the
  **module**, never the package: after `include_auth` true→false a
  `credentials/` dir holding only `__pycache__` imports as a namespace
  package and `find_spec("<pkg>.credentials")` wrongly succeeds.
  `include_providers=false` (allowed only with `include_auth=false`) drops
  `providers/` and `tests/test_providers.py`; nothing outside
  `credentials/health.py` may import `providers`. If you touch any of these, regenerate with
  `include_auth=false` and run the full verify loop — this combination
  previously went untested and silently shipped a `ModuleNotFoundError` on
  `keyring` for anyone who picked "no auth".
- `README.md` is in `copier.yml`'s `_skip_if_exists`: generated once, never
  merged on `copier update` (projects rewrite it). A template change meant
  for existing projects' READMEs has to be described in SKILL.md's Update
  mode instead.
- `src/{{ package_name }}/migrations/versions` is in `_exclude` under
  `_copier_operation == 'update'`: a package's migration history is its own,
  so a change to the template's example migrations reaches only packages
  generated after it, and a package updated from an older tag keeps the
  objects those migrations created. For the same reason a file that must
  reach a package on update keeps its template name: copier applies no
  change when the template file was renamed (`.py.jinja` → `.py`) and the
  project silently keeps the old content — `0001_initial.py.jinja` holds no
  template expression and keeps the suffix for that reason.
- Optional generated parts are copier questions, not deletions:
  `include_project` (`commands/project.py`, `init`, `config`, `status`,
  `core/services.py`, `core/models.py`, `--project`), `include_auth`,
  `include_providers` (only without auth), `include_http_provider` (drops
  `providers/http.py`, `tests/test_http_provider.py` and `httpx`),
  `include_db` (keeps `core/db.py`, `core/tables.py`, `core/normalize.py`,
  `migrations/`, `commands/db.py`, `tests/test_db.py`, the database fixture in
  `tests/conftest.py`, the three Database errors in `core/errors.py.jinja`
  (guarded by `{% if include_db %}`), and the SQLAlchemy/Alembic/psycopg deps; its PostgreSQL
  test runs only under `scripts/pg_test.sh` in the generated project — a
  throwaway container on a Docker-assigned port), `include_skill` (`data/`,
  `commands/skill.py`, `core/skills.py`, `--ai`), `include_describe`
  (`commands/describe.py`, `core/opencli.py`, `core/data_files.py`),
  `include_contracts` (only with describe: `tests/contracts/`, the detach
  scripts); the install questions `install_homeserver_users` and
  `install_mac` (`[tool.rb.install]`), `dist_name_legacy` (rename
  transition). The Gitea workflow is always generated. A part is off in a new
  package and on for a package made before its question (`updating`, ADR
  0014). Shared code never imports a part: `cli.py` calls `register(app)` of
  each part module it finds (`PARTS`), a part's global option goes to
  `output.RootGroup.part_options`, `doctor` and `describe` probe the module.
  Render each branch once when you touch the workflow or `copier.yml`.
- The `_exclude` pattern of a part added after the first release tests
  `is false`, never `not`: on `copier update` copier renders the previous
  version with the new patterns (to keep what they exclude), where that
  answer is undefined — `not` would drop the part's files there, and copier
  then merges them back as the project's own additions, with conflicts.
- Human output goes through rich, which silently drops anything in
  `[...]` it takes for markup (`[[tool.rb.external]]` vanished from help).
  `output.guard`/`output.group` escape help text; `human.echo()` escapes
  its argument; only `human.echo_markup()` renders markup — escape() any
  data you put inside it.
- Three names: `package_name` (import, keychain, env prefix, project dir),
  `cli_name` (command) and `dist_name` (`[project] name`, default
  `rb-<slug>`, the Standard, Technology). The distribution name is rendered into
  `src/<pkg>/_distribution.py` (`DIST_NAME`) because an editable install
  can't be mapped from package to distribution at runtime
  (`packages_distributions()` returns nothing for it); every
  `importlib.metadata` lookup uses `DIST_NAME`, and `tests/test_cli.py`
  checks it equals `[project] name`.
- The command name is `cli_name` (copier question; `[project.scripts]`),
  which may differ from `package_name`. Runtime code gets it from
  `core.version.cli_name()` (the installed console script), never from
  `__name__`; keychain service, env var prefix and `.<package>/` stay on
  the package name. Test with `--data package_name=rb_sitemap_xml --data
  cli_name=sitemap-xml` when touching anything that names the command.
- `_exclude` patterns in `copier.yml` match the **rendered** path
  (`tests/test_auth.py`), not the template file name
  (`tests/test_auth.py.jinja`) — a pattern with `.jinja` matches nothing
  and the file is silently generated anyway.
- Typer is capped and used through its public API only (ADR 0016). Never
  build a parameter with `TyperOption`: a part's global option (`--project`,
  `--ai`) is a declaration function — `def _global_options(x: T =
  typer.Option(...))` — appended to `output.RootGroup.part_options`, and
  `RootGroup` turns it into a parameter with `typer.main.get_command`; typer
  0.29 changed the `TyperOption` constructor and that broke every generated
  CLI on install. The base class `typer.core.TyperGroup` is allowed — it is
  the documented base for `cls=`, and 0.29 did not change it; `typer.main`
  re-exports it only in passing. A `bool` option with no `is_flag` is a flag
  (typer warns about `is_flag` and drops it in a later release).
  The dependency is `typer>=0.27,<0.29`: 0.29 stays out until the template's
  own `tests/test_help.py` stops calling click's `param.type_cast_value` and
  `param.get_error_hint`, whose arity 0.29's bundled click changed. Raise the
  cap only with a green `fresh install` gate step.
- Typer ≥ 0.27 no longer depends on `click` (it ships its own parser and
  `typer.Exit`/`typer.Abort` in `typer.exceptions`). Don't `import click`
  in template code — it isn't installed in generated projects. Related:
  `no_args_is_help=True` exits 2, which is why `cli.py` and
  `output.group()` implement help-on-no-args by hand.
- `output.guard` must re-raise `typer.Exit`/`typer.Abort` before its
  catch-all `except Exception` — both subclass `RuntimeError`, so a plain
  catch-all would turn every controlled exit into an `UNEXPECTED` error.
- Template release tags must be valid PEP 440 versions (`v1.1.0`,
  `v1.2.0rc1`). copier silently ignores anything else (`v1.1.0-test`) when
  picking the latest version, so `copier update` reports nothing to do.
- `copier update` refuses to run on a dirty tree, so every artifact a tool
  in the generated project writes must be in `template/.gitignore`
  (`.coverage` from pytest-cov was missed once and blocked updates).
  When adding a dev tool, run it once and check `git status` is clean.
- Help snapshots (`tests/snapshots/help/*.txt`) are **not** shipped in
  `template/`: they contain the CLI's name, and rich re-wraps lines around
  it, so a snapshot rendered for `demotool` fails for a longer name. They
  are rendered by `copier.yml`'s `_tasks` on `copier copy` only (on
  `copier update` a project refreshes them itself — SKILL.md Update mode).
  For the same reason template command docstrings write `{cli}`, which
  `output.guard` substitutes, instead of becoming `.jinja` files.
