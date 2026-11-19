# Plan extraction, 2026-11-08

Verdicts for every bullet of `docs/plans/freeze-list.md` and every decision of
`docs/plans/simple-standard.md`, taken by CG-082 (E-010) before the two files were removed. The `open` rows are ideas `CG-IDEA-007` … `CG-IDEA-023`.

# CG-082 — done: 47 verdicts, 17 items stay open

Every bullet of `docs/plans/freeze-list.md` (16 bullets, 45 sub-items) and every decision of
`docs/plans/simple-standard.md` has a verdict. 17 items stay `open`: each gets one candidate idea title
below, for the Architect to turn into `antagor idea add` on main.

Nothing was written to `.agents/antagor/ideas/`. Neither plan file is deleted. Both files carry a
three-line header that names this extraction; `antagor layout check` stays red until the Human approves
the deletion — expected, not a finding.

Verdicts: `open` 17, `done` 25, `elsewhere` 6, `dropped` 3.

## What I checked

- `skills/cli-builder/reference/standard.md`, its sections by name — Technology, Commands, Output,
  Errors, Health, Credentials, Install, Docs, CI, Release, Optional parts.
- The gate: `gate/rb_gate/gate.py` (steps, `_CONTRACT_RESULT`, `install_locked`, `check_index_sources`)
  and `gate/standard/__init__.py` (`probe_env`, `Package.run_each`, the `standard:` rules).
- `skills/cli-builder/reference/existing-package.md` and `SKILL.md`.
- `copier.yml`, `template/.agents/antagor/antagor.toml.jinja`, `template/.gitea/workflows/ci.yml.jinja`,
  `template/pyproject.toml.jinja`, `template/tests/*`, `template/src/*/core/tables.py`,
  `template/src/*/core/errors.py`, `template/src/*/core/skills.py`, `template/src/*/core/opencli.py`,
  `template/scripts/check_command_docstrings.py`.
- `scripts/check_template.sh`, `CHANGELOG.md`, `docs/adr/`.
- Unchecked: nothing was run. The checks of this task are `manual`, and the work changes no code. I did
  not look at the worktrees of semkit, mediagen, llmkit or the Antagor repo; a verdict that names one of
  them rests on this repo's files only.

## docs/plans/freeze-list.md

Evidence names the commit, the rule or the epic of a `done` item, the owner of an `elsewhere` item, or
the reason of a `dropped` one.

| Item | Verdict | Evidence | Idea title |
|---|---|---|---|
| F1.1 `check_template.sh` rewrites a rendered package with `sed` for its 3.11 round | open | the `sed` rewrite is still there (`scripts/check_template.sh`, `run_gate_on_python_311`); the gate still declares `requires-python = ">=3.11"` | check_template.sh: a 3.11 fixture package instead of sed rewriting a rendered one |
| F2.1 a busy runner outlasts `gate_timeout_minutes` (exit 124) | elsewhere | antagor: the setting and the wait are Antagor's; this repo publishes with `gate = "local"` (`antagor.toml`) | antagor: a busy runner outlasts the gate timeout |
| F3.1 a package with a browser needs Playwright install, `--shm-size=1g`, `CRAWLEE_DISABLE_BROWSER_SANDBOX=1` in its CI | open | Standard, CI holds only two bullets, neither names a browser | Standard, CI: what a package that drives a browser adds to the workflow |
| F4.1 `copier update` needs `git stash -u` first and `--trust` always | done | `existing-package.md`, "A package from the template that wants updates", steps 1 and 4 | — |
| F4.2 changing an option deleted an edited package file | done | `existing-package.md`, "Changing an option": `git status`, restore from HEAD | — |
| F4.3 a conflict next to a reworded comment drops a package block | done | `existing-package.md` step 5: read the diff of `pyproject.toml` line by line | — |
| F4.4 template example tables merge into `tables.py` as duplicates | open | `template/src/*/core/tables.py` still ships `items`, `responses` and the views as examples | the db part ships no example table inside the package's own `core/tables.py` |
| F4.5 template tests assume the default project folder | done | `template/tests/test_project.py` builds its own folder (`init(tmp_path, name="demo")`) | — |
| F4.6 the gate's pytest step runs with CI colour variables; help and describe snapshots may hold a Mac data-dir path | done | CG-057; `probe_env()` strips the CI variables for CLI runs; `core/opencli.py::_sqlite_file` publishes the path relative to the data dir | — |
| F4.7 a leaked key: a fingerprint-only `.gitleaksignore` line is not in the Standard | done | Standard, Credentials: one fingerprint line per revoked finding | — |
| F4.8 an old `.git/hooks/pre-commit` with only the docstring check can be deleted | done | `existing-package.md`, "Old release tooling": delete `.githooks/` and `install_hooks.sh`, unset `core.hooksPath` | — |
| F4.9 the docstring checker flags a `ctx`-only signature change | open | `template/scripts/check_command_docstrings.py` dumps `node.args` whole | check_command_docstrings: a `ctx`-only signature change is not a logic change |
| F4.10 `skills.frontmatter()` keeps YAML quotes | open | `core/skills.py::frontmatter` returns `value.strip()`, quotes included | `core/skills.frontmatter()` strips a matching pair of YAML quotes |
| F4.11 doctor checks report `status` ok/warn/fail | done | Standard, Health: a `doctor` check has a boolean `ok`; `status` belongs to `auth status` only | — |
| F5.1 a package's own `core/db.py` or `commands/db.py` collides with the `db` part | open | Standard, Database, "Turn on" names no case of an existing module of the package | Standard, Database: a package's own db module next to the db part |
| F5.2 `errors.py` keeps the Database* errors without `include_db` | open | `template/src/*/core/errors.py` ships `DatabaseUnavailable`, `DatabaseNotMigrated`, `DatabaseTooNew` in every package | the Database* errors ship only with the db part |
| F5.3 files a package deleted (`core/deps.py`) stay deleted though new template code imports them | open | `core/deps.py` is imported by `commands/doctor.py` and `core/opencli.py`; `existing-package.md` names no such case | update flow: a template module the package deleted comes back when new code imports it |
| F5.4 `AGENTS.md` is not written when `CLAUDE.md` exists | done | the template ships `AGENTS.md.jinja`; `CLAUDE.md` is in `_exclude` (`copier.yml`) | — |
| F5.5 the 3.11 → 3.14 jump needs ruff fixes (UP047, `except (A, B)`) | done | CG-056 (v1.25.6) moved every package to 3.14; the 3.11 round rewrites `except A, B` itself | — |
| F5.6 rich elides long option names under the CI env | done | CG-057, CG-068; `probe_env()` + `tests/test_help.py` pin `COLUMNS`, `NO_COLOR`, `TERM` | — |
| F5.7 `uv.lock` changes are not in the conflict list | done | `existing-package.md` step 8, "Lock and snapshots": `uv lock` | — |
| F5.8 README install lines are the package's to fix | done | `README.md` is in `_skip_if_exists`; `existing-package.md` step 5 edits it by hand | — |
| F6.1 `gate_status_url` takes the repository name from `repository_url` (the GitHub mirror) | open | `template/.agents/antagor/antagor.toml.jinja` still renders the last path segment of `repository_url` | `gate_status_url` names the package's Gitea repo, not its GitHub mirror |
| F7.1 the contracts step misses `[gw0]` lines under pytest-xdist | open | `gate/rb_gate/gate.py`, `_CONTRACT_RESULT`, and its `-vv` run has no `-p no:xdist` | gate, consumer contracts: the summary survives pytest-xdist |
| F8.1 the gate line of a ported CI workflow has the tag pasted by hand | done | `existing-package.md`, "The loop", step 1: a ported workflow pins the tag as a constant | — |
| F8.2 help snapshots need the render env pinned in conftest | open | the template pins it inside `tests/test_help.py`; `existing-package.md` does not name it for a package's own test | existing package: a help test pins `COLUMNS`, `NO_COLOR` and `TERM` |
| F8.3 a stale `.git/hooks/pre-commit` stops `antagor new`, and the agents' classifiers refuse `rm` | elsewhere | antagor: the hook policy and the classifier are Antagor's | antagor: a stale `.git/hooks/pre-commit` blocks `antagor new` |
| F8.4 a package not from the template has no `[publish]` block | done | `existing-package.md`, "Old release tooling": `antagor new --prefix <PREFIX>` writes it | — |
| F8.5 a library's install step is not spelled out | done | Standard, Install: a library has `homeserver = []` and `mac = false` | — |
| F9.1 a package not from the template has no `scripts/deploy.sh`, and a hand commit cannot add it | open | merged with F9.2: Standard, Release says what a version does, not what a hand-made package puts in `[publish]` | Standard, Release: `deploy.sh` and `deploy_command` for a package not from the template |
| F9.2 without `deploy_command` `antagor publish` tags locally and pushes nothing | open | same idea as F9.1 | (with F9.1) |
| F9.3 the template `ci.yml` comment names `.copier-answers.yml` | dropped | the comment is the template's own workflow; a ported one pins the tag (`existing-package.md` step 1); CG-IDEA-001 may drop CI altogether | — |
| F9.4 no library variant of `AGENTS.md` and the workflow in the docs | open | Standard, Docs and CI name one package shape; only Install spells out a library | Standard, Docs and CI: what a library's `AGENTS.md` and workflow say |
| F9.5 `task-create` needs `--no-epic --confirmed` without an epic; the Antagor config is the Architect's on main | elsewhere | antagor | antagor: `task-create` without an epic |
| F10.1 a dependency by a GitHub git URL passes the local gate and fails CI at `uv sync`; no gate step catches it | open | Standard, Install recommends the Gitea registry; `gate/rb_gate/gate.py` checks only explicit-index sources. Related to IDEA-248 | the gate refuses a `[tool.uv.sources]` git URL for one of our packages |
| F10.2 fixing a package before `antagor new` leaves those commits out of the first changelog | elsewhere | antagor | antagor: the first changelog misses the commits before `antagor new` |
| F11.1 the template side of the Antagor config drops the package's own `worker` and extra `checks` | done | `existing-package.md` step 7 keeps the package's `checks`; the template's config carries no `worker` key | — |
| F12.1 the CI runner's Python 3.11.2 wraps an `except*` re-raise in an ExceptionGroup | dropped | CG-056 (v1.25.6) made every package require 3.14 | — |
| F12.2 the gate's missing-`doctor` step was not in the brief's red list | done | `existing-package.md` maps each red step to its Standard section, `standard: health` included | — |
| F12.3 `antagor publish --main` does not merge a task in `publish` | elsewhere | antagor (`antagor publish <id>`) | antagor: `publish --main` and a task in `publish` |
| F13.1 an update replaces the package's own copies of `test_ci.py` and `test_scripts.py` | open | `existing-package.md` says to report removed tests, not that the update replaces those two files | existing package: the update replaces the package's copies of `test_ci.py` and `test_scripts.py` |
| F13.2 `task-create` `[check: …]` must equal a `--check` string; `--read-first` counts with the body's "Read first" | elsewhere | antagor | antagor: `[check: …]` and `--read-first` rules of `task-create` |
| F13.3 a Renovate PR left open by a hand update closes itself | dropped | no work: Renovate closes it on its next run | — |
| F14.1 parallel code and the machine's size: a candidate Recommended rule | open | Standard, Technology has no rule on a worker count; the template CI sets no `PYTEST_XDIST_AUTO_NUM_WORKERS` | Standard, Technology: parallel code takes its worker count from the machine |
| F15.1 three identical gates per release; the `tags` trigger can go | done | CG-078 (v1.27.4): the workflow runs on `main`, `antagor/publish-*` and a pull request, not on a tag | — |
| F16.1 Antagor times each gate step from Gitea's log stamps; the line format stays | done | CG-072; the gate prints one `<tool>: <check> … <result>` line per step | — |
| F16.2 run the per-command Standard checks in one process or in parallel | done | `gate/standard/__init__.py::Package.run_each` runs them in a thread pool | — |

## docs/plans/simple-standard.md

One row per decision; the last five rows are the other parts of the plan.

| Part | Verdict | Where it lives now | Idea title |
|---|---|---|---|
| S1 minimal template, the rest optional parts | done | Standard, Optional parts; ADR 0003, ADR 0014; `copier.yml` | — |
| S2 two kinds of rule: Mandatory (gate) and Recommended | done | Standard, opening paragraph; ADR 0011 | — |
| S3 one Standard; `SKILL.md` holds only the agent's steps | done | `skills/cli-builder/reference/standard.md`, `SKILL.md` | — |
| S4 the package is standalone; the output and error layer is code in the package; the core is a development tool | done | Standard, Technology (two Recommended rules); ADR 0013 | — |
| S5 the skill in two modes | done | `SKILL.md`, `reference/new-package.md`, `reference/existing-package.md` | — |
| S6 meeting the Standard means a green gate; every Mandatory rule is checked by machine | done | Standard, opening paragraph; ADR 0011 | — |
| S7 the gate lives in this repo (`gate/`), one version with the template, command `rb-gate` | done | ADR 0013; `gate/`; the CI workflow of a package | — |
| S8 `clidocs` stays outside; the `docs` command is gone; `describe` is an optional part | done | ADR 0008; Standard, Describe | — |
| S9 the Standard is frozen: a new rule needs a package that breaks without it | open | nowhere: the freeze decision exists only in this plan file (a grep of `*.md` outside `.agents/` finds it nowhere else) | Standard, intro: a new rule needs a package that breaks without it |
| S10 order: Standard, minimal template, skill, rollout | done | v1.21.0 … v1.25.0 (ADR 0013, ADR 0011, E-005, E-006) | — |
| S11 the Standard document: English, one file, links by section name | done | `standard.md`; `scripts/check_template.sh` fails an `AGENTS.md` or a package skill that does not link the Standard, or that cites a `§` number | — |
| S12 the Mandatory list | done | Standard, Technology … Release, each rule naming its gate step | — |
| S13 the optional parts and their rules | done | Standard, Optional parts: Project, Credentials and providers, HTTP, Database, Package skill, Describe, Consumer contracts, Detach | — |
| S14 the core-library plan is replaced by this one | done | ADR 0013 | — |

## Notes for the Architect

1. A row that says `elsewhere` is a message for another project: `antagor` six times. File them there,
   not here.
2. F10.1 overlaps IDEA-248 ("Our packages depend on each other through the Gitea registry"); the gate
   step is the part IDEA-248 does not cover. Fold, or file next to it.
3. F3.1, F9.3 and F15.1 touch the CI of a generated package. CG-IDEA-001 ("No Gitea CI in the standard")
   would make F3.1 moot and F15.1 a half step. Decide the order.
4. S9 is the only leftover of the plan with no home; the other eight decisions are shipped.
