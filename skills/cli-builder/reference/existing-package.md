# Existing package

The mode for a CLI or package that already exists, made from the template or not. The Standard
(`standard.md`) says what the package must be. The gate says where it is not. Do not audit by hand first.

Work on a branch, not on main. Stage or commit nothing of someone else's work: `git status` must show only your
changes. Keep the behaviour: what the package did before still works after.

## The loop

1. Run the gate in the package root:

   ```bash
   uvx --from "git+https://homeserver.tailee01ab.ts.net:3000/bolandeu/cli-generator.git@<template tag>#subdirectory=gate" gate check
   ```

   `<template tag>` is the latest tag of `cli-generator`. The gate exists only in template tags v1.21.0 and later, so
   `_commit` of an old package can point at a tag with no gate. `_commit` is the tag only after a copier update. A
   test ported from the template without an update pins that tag as a constant instead of reading `_commit`.
2. The gate stops at the first red step and prints its name. Open the Standard section that names the step, read the
   rule, fix the package, run the gate again.
3. Repeat until the last line is `release: gate passed`. A step that is skipped with a notice (`osv-scanner`,
   `gitleaks`) needs its tool: install it, run again.

`copier update` is not required to meet the Standard. A package that is not from the template gets no template
files: write the file the rule asks for.

| Red step | Standard section |
|---|---|
| `build + install wheel`, `uv lock --check`, `ruff check`, `ruff format --check`, `ty check`, `pytest`, `external dependencies` | Standard, Technology |
| `install section` | Standard, Install |
| `standard: commands` | Standard, Commands |
| `standard: json` | Standard, Output |
| `standard: errors` | Standard, Errors |
| `standard: health` | Standard, Health |
| `secret scan` | Standard, Credentials |
| `standard: docs` | Standard, Docs |
| `standard: params` | Standard, Describe |
| `standard: ci` | Standard, CI |
| `vulnerability audit`, `fresh install` | Standard, Release |

An old gate in the package is a fix like any other: remove the old release script, its tests and an old gate line in
the Antagor `checks` (`[publish] gate_command` holds the gate command, and nothing else does). Report removed tests as
removed existing tests, not as edited ones.

A tool the package uses beyond the Standard (a database, providers, a project config) has its rules in
Standard, Optional parts. The gate checks them only when the package has the part.

Rules to keep while you fix:

1. **Test first.** The failing test is committed before the code that fixes it. An existing test is never edited to fit
   the code.
2. **Surgical changes.** Touch what the red step needs. Do not reformat or "improve" other code.
3. **Fix the code, not the gate.** Do not lower a floor or add a blanket ignore. A rule the package cannot meet is
   a Recommended one it may skip; say so in its `AGENTS.md`.
4. **After `ruff check --fix`**, import every module or run the tests: the autofix deletes imports that a lazy
   `from … import` inside a function relies on.
5. **A secret found in the repo** is a real finding: tell the Human its name and file. Do not rewrite history.
   Revoking it is the Human's.

## A project under Antagor

The Architect may not commit package files, and the worker does not commit.

1. The Architect runs the gate in a throwaway clone, with temporary fixes, until it has every red step.
2. The Architect writes one task that lists all red steps.
3. The worker fixes them test-first. The red run of each new test goes in its report, not in git history.
4. Every Python module the worker touches has a module docstring. Antagor refuses the task otherwise.

## A script or CLI that is not a package yet

Skip this part when the code already builds a wheel. Do these in order, one commit each, then run the loop:

1. **Package layout.** `src/<package>/` and `pyproject.toml` with `[build-system]` and `[project.scripts]`; run it as
   an installed command, not `python foo.py`. A distribution named `rb-<slug>` (Standard, Technology).
2. **Commands without logic.** A command parses, calls one core function and renders. Move inline work into
   `core/`.
3. **Secrets out of the repo.** A key hardcoded, in a committed `.env` or in a project file moves to an environment
   variable; `.env` and `.env.*` go in `.gitignore` (Standard, Credentials). Flag it to the Human as a security fix.
4. **`--json` on every command**, the envelope and the stdout/stderr split of Standard, Output.
5. **Errors with codes and exit codes** of Standard, Errors; an unexpected exception also comes out as JSON.
6. **`doctor --json` and `auth status --json`** in the shapes of Standard, Health.
7. **Help** that meets Standard, Commands: a bare `<cli>` lists the commands, every command has `--help` with an
   `Example:` line and a `help=` on each parameter.
8. **Destructive commands** have `--dry-run`, and `--confirm` is required under `--non-interactive`.
9. **Portable code.** `pathlib`, `shutil` and `platformdirs`; no `os.system`, no `shell=True`, no fixed POSIX path.
10. **Install and release.** `[tool.rb.install]` (Standard, Install), version from the git tag (Standard, Release),
    the README and `AGENTS.md` (Standard, Docs), the local gate in `[publish] gate_command` and no workflow (Standard, CI).
11. **Dependencies on our packages** by a compatible range from the Gitea registry, not by a git tag, a branch or a
    `path =` (Standard, Install).

If the old code is small and little of it is worth keeping, scaffold a new package with the new-package mode and port
the logic into `core/`.

## A package from the template that wants updates

Use it for a package with `.copier-answers.yml`. The update is optional for the gate; do it to take the template's
fixes or when the package still has the old gate.

1. **Clean tree.** `git status` shows nothing; `copier update` refuses otherwise. Untracked files count too. Commit, or
   run `git stash -u` before the update and `git stash pop` after its commit; never delete. A
   worker that may not commit stages (`git add -A`) and runs the staged script in place of `uvx copier update`, with the
   same arguments:
   `uvx --from copier python <skill dir>/scripts/copier_update_staged.py --trust --defaults [--vcs-ref … --data k=v …]`
   (`<skill dir>` is `skills/cli-builder` of this plugin).
2. **Template source.** A package from before the Gitea move has another `_src_path` in `.copier-answers.yml`. Set
   `_src_path` to `https://homeserver.tailee01ab.ts.net:3000/bolandeu/cli-generator.git` and `repository_url` to the
   package's Gitea URL. Check with `uvx copier update --trust --defaults --pretend`: it must say "Updating to template
   version …".
3. **Answers that rename.** Without a `cli_name` answer the default is `package_name` with `_` → `-`, which renames
   the command of a package with `_` in its name: pass `--data cli_name=<the command in [project.scripts]>`. Without a
   `dist_name` answer the default `rb-<slug>` renames the distribution: to keep the name pass
   `--data dist_name=<current [project] name>`. A missing `antagor_prefix` is passed as `--data antagor_prefix=<PREFIX>`.
   The Antagor project name (`name` in the Antagor config) is the package's folder name. The update never changes
   that line. When the name differs from the folder, edit the line once by hand: later updates keep it.
4. **Update.** `uvx copier update --trust --defaults`. It three-way-merges the template diff since `_commit`; business
   logic, extra commands and tests survive. `README.md` is never touched (`_skip_if_exists`), and neither is
   `src/<package_name>/migrations/versions/`: the package's migration history is its own. An object an old example
   migration created stays in the package until the package drops it in a migration of its own.
5. **Conflicts** land as `*.rej` files or inline markers. Resolve hunk by hunk: keep the package's commands, providers
   and settings, take the template's structural changes. Never take one side wholesale (`git checkout --theirs/--ours`,
   copying the template file over). Delete each `.rej` and read `git diff` before the gate. A hunk next to a reworded template comment can carry a
   package block (e.g. `[[tool.rb.external]]`): read the diff of the package's `pyproject.toml` line by line.
6. **The old gate gone.** `git ls-files scripts/release.py` prints nothing, and
   `grep -n 'cli-core' pyproject.toml uv.lock` finds nothing. Remove what is left by hand. Edit the gate command in
   `README.md` by hand.
7. **The gate line of the Antagor config.** `.agents/antagor/antagor.toml` keeps the docstring check in `checks`,
   `heavy = ["gate check"]`, and the local gate: `[publish] gate_command` holds the command with the template tag,
   and `[publish]` names no `gate` and no `gate_status_url` (Standard, CI). The update writes that line, drops the gate
   line from an unchanged `checks` and deletes the workflow. A package of mode fast wrote its own
   `checks`: this update, once, conflicts on that one line. Resolve it: keep the package's own `checks`, with no gate
   command, and delete the conflict markers. `AGENTS.md` and `CODING_STANDARDS.md` name `gate check` and no
   workflow. A task for a worker: the
   Architect puts `.agents/antagor/antagor.toml` in `owns_paths` of the task.
8. **Lock and snapshots.** `uv lock`, then `uv run pytest --snapshot-update`. Help snapshots are rendered only on
   `copier copy` and when a template release changes a command's help: read the diff in `tests/snapshots/help/`.
9. **Gate.**

   ```bash
   uvx --from "git+https://homeserver.tailee01ab.ts.net:3000/bolandeu/cli-generator.git@<template tag>#subdirectory=gate" gate check
   ```

   Run it until it ends with `release: gate passed`. `<template tag>` is `_commit` in `.copier-answers.yml` after the update. A new template release can add a rule that
   the package's code fails: fix the code (the loop above).
10. **Release.** The update is its own task, titled `Template vX.Y.Z: …`. A
    breaking change for the package's callers is a breaking bump (minor at `0.x`).

Things the update does not do by itself:

- **Old release tooling.** `towncrier` (`[tool.towncrier]`, `changelog.d/`, the marker comment), `.githooks/`,
  `scripts/install_hooks.sh`, `herdr_name` and the hooks in `.claude/settings.json`: delete them, run
  `git config --unset core.hooksPath`, then bring the project to Antagor's current files: a package with Antagor's
  config (`.agents/antagor/antagor.toml`) runs `antagor -C <package> upgrade --apply`; a package without it runs
  `ANTAGOR_ROLE=architect antagor new --prefix <PREFIX>` as in the skill's Publish. Keep the released sections of `CHANGELOG.md`; delete
  a `## [Unreleased]` heading (a package never released renames it `## [X.Y.Z] - <date>`).
- **Version from the tag.** A `version =` line in `pyproject.toml` with no tag: tag the commit first
  (`git tag -a vX.Y.Z -m vX.Y.Z <sha>`), then use `dynamic = ["version"]` (Standard, Release).
- **No workflow.** The gate is local, so the package runs no workflow on a forge: `git rm -r .github/workflows`
  (and `.github/` if nothing else is in it), and `git rm -r .gitea/workflows` when that folder runs the gate. The
  command stays in `[publish] gate_command`.
- **Secret scan.** `brew install gitleaks`. A fake test value of the package's own goes in the root `.gitleaks.toml`
  `regexes` as one exact string (`'''^<value>$'''`), never a path or a rule disable. Any other finding is a leaked
  key (loop, rule 5). A real key leaked in history and revoked by the Human: one line per finding in
  `.gitleaksignore`, the fingerprint `<commit>:<file>:<rule>:<line>`, with no value. Never a path, a rule disable or
  the key's value. A tracked env file: `git rm --cached <file>`, and treat its values as leaked.
- **Dependencies on our packages.** In `[tool.uv.sources]` replace `rb-x = { git = "…", tag = "vX.Y.Z" }` with
  `rb-x = { index = "gitea" }`; `"rb-x>=X.Y"` stays in `dependencies`; `uv lock`.
- **Extra skills.** Skills beyond the conventions one (in `.agents/skills/`, or a patched `skill` command) move into
  `src/<package_name>/data/skills/<name>/SKILL.md` (frontmatter name `<cli>-<name>`; Standard, Package skill). Drop the
  patch of `commands/skill.py`.
- **Changing an option** (`--data include_auth=false`, `include_providers=false`): copier deletes the files the new
  answers no longer generate, and may delete a file the package edited (business logic included). Run `git status` and
  restore every deleted package file from HEAD (`git checkout HEAD -- <file>`). Delete the leftovers of the option by
  hand, and the help snapshots of commands that are gone, then run the gate. A package without credentials that does not use
  `providers/` answers `include_providers=false`; a deleted template file comes back on the next update.
- **A bare commit hash in `_commit`.** The package was generated before the template had releases; `copier update`
  works from that commit and moves `_commit` to the latest tag.
- **Help docstrings.** The help test (`uv run pytest tests/test_help.py`) prints the command paths whose docstring
  does not meet Standard, Commands. Paste them into `tests/help_allowlist.txt` (the file is the package's; the
  update never overwrites it), then bring one docstring at a time to the Standard. New commands may not be added.

### Renaming the distribution

Standard, Technology: the distribution is `rb-<slug>`. The command (`cli_name`) and the import package do not change;
only `[project] name` does.

1. `uvx copier update --trust --defaults --data dist_name=rb-<slug> --data dist_name_legacy=<old name>` (or edit
   `[project] name` by hand in a package not from the template), then `uv lock`. `src/<package>/_distribution.py`
   must carry the same name: `tests/test_cli.py` fails otherwise. `DIST_NAME_LEGACY` makes an install still
   registered under the old name report its real version until it is reinstalled; clear it
   (`--data dist_name_legacy=`) in a later release once every machine has the new name.
2. It is a breaking change for consumers: breaking bump (minor at `0.x`) in a task whose title names the old and the
   new name.
3. Every consumer, in the same wave: rename the dependency and its `[tool.uv.sources]` key
   (`"yandex-oauth>=0.2,<0.3"` → `"rb-yandex-oauth>=0.3,<0.4"`, `rb-yandex-oauth = { index = "gitea" }`), `uv lock`,
   gate, release.
4. Machines: no uninstall step. Sysadmin's tool-updater follows the new name.
