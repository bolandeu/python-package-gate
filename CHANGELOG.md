# Changelog

## Unreleased
- Gate: step `addresses` — `src/` names no host or absolute path of a person (loopback, private ranges, tailnet names, `/Users/…`); `[tool.rb.gate] addresses_allow` lists the reasoned exceptions.
- Standard: *Addresses and paths* — a package ships no address of somebody's infrastructure; such values come from an environment variable or the config, and a missing one is a clear `INVALID_ARGUMENTS`, not a default or a timeout.

### Outside epics

- Гейт переименован: дистрибутив `rb-release` → `rb-gate`, модуль `rb_release` → `rb_gate`, команда `rb-release` → `gate` (репозиторий — `python-package-gate`). Причина: правило «дистрибутив `rb-<x>`, команда `<x>`» (ADR 0004), а публикации ещё не было.
- Удалены `.agents/antagor/**` (история агента, не продукт) и parity-сьют, который сверялся с удалённым `template/scripts/release.py`.
- `copier update` в пакете режима `fast`: конфликт теперь занимает две строки (`checks` пакета и `heavy` шаблона) — разрешение и текст скилла обновлены.
- `CONTEXT.md`: один термин «Гейт» вместо двух, устаревшее определение через `release.py` убрано; `AGENTS.md` больше не отправляет к `release.py`.

## v1.27.10 — 2026-11-16

### Outside epics

- Gate: the fresh install runs describe --json, so a broken describe cannot reach a tag (CG-093)

## v1.27.9 — 2026-11-13

### Outside epics

- Template: public API only for global part options, a typer cap, and a fresh-install gate step (CG-091)
- tests/test_skills.py.jinja: get_command returns a Command to ty, so the all-parts variant fails ty check (CG-092)

## v1.27.8 — 2026-11-09

### E-012 — One gate, and it is the local one: the template stops generating a Gitea workflow

A generated package has exactly one gate — rb-release check on the machine that builds it. No .gitea/workflows/ci.yml in a new package, none in an updated one, the Standard says so, and Gitea keeps releases only.
Time: 21.1h since the epic was approved

- Template: no Gitea workflow in a generated package, and none left behind by an update (CG-084)

## v1.27.7 — 2026-11-09

### E-009 — The describe document answers a consumer's two questions: where the skill text is, and which packages are the family

A consumer of describe --json (rb-mcp, clidocs, Windmill) reads the skill text without a second process, and knows family membership from the distribution name instead of guessing it from a binary name.
Time: 22.5h since the epic was approved

- describe: x-rb-skills[] carries the bundled skill path, so its text needs no second process (CG-080)

## v1.27.6 — 2026-11-09

### E-014 — The gate and the template stop failing for reasons of their own: xdist summaries and the Database errors

A package's contract step reads its summary under pytest-xdist, and the Database errors ship only with the db part — so neither a green suite looks broken nor a package carries errors it cannot raise.
Time: 2.1h since the epic was approved

- Gate, consumer contracts: the summary counts the cases under pytest-xdist (CG-089)
- The Database errors ship only with the db part (CG-090)

## v1.27.5 — 2026-11-08

### E-008 — describe: the param metadata and hidden are specified, and the gate checks them

A consumer reads one describe --json and knows every option and argument without guessing: a type, a default (null when there is none), repeatability. The Standard names these fields and hidden; the gate refuses a document that breaks them.
Time: 6.5h since the epic was approved

- Template emits x-rb-default always; the Standard names x-rb-type/default/multiple and hidden; the gate checks a param entry (CG-079)

### E-009 — The describe document answers a consumer's two questions: where the skill text is, and which packages are the family

A consumer of describe --json (rb-mcp, clidocs, Windmill) reads the skill text without a second process, and knows family membership from the distribution name instead of guessing it from a binary name.
Time: 6.5h since the epic was approved

- Standard: family membership is the distribution name rb-*, and the tool's own name is x-rb-tool.tool (CG-081)

### E-010 — Two plans stop being files: their put-off items become ideas, and the freeze list is reachable

docs/plans/ is empty: every put-off item of the freeze list and every gap left by the simple-standard plan is an idea in this repository's list, with a number the Human can see, and no plan file duplicates the Standard.
Time: 6.3h since the epic was approved

- Two plans become ideas: every put-off item of the freeze list and the simple-standard leftovers gets a number (CG-082)

### E-011 — The plugin manifest check survives without the claude binary

A change to .claude-plugin/plugin.json or to the skill frontmatter is still checked by the project checks, with no external binary: a script in the repository does the part of 'claude plugin validate --strict' that applies here.
Time: 5.9h since the epic was approved

- scripts/check_plugin.py: the plugin manifest check without the claude binary (CG-083)

### E-012 — One gate, and it is the local one: the template stops generating a Gitea workflow

A generated package has exactly one gate — rb-release check on the machine that builds it. No .gitea/workflows/ci.yml in a new package, none in an updated one, the Standard says so, and Gitea keeps releases only.
Time: 4.8h since the epic was approved

- Standard and SKILL: the local gate is the only gate; Update mode deletes the old workflow (CG-085)
- This repository: template-gate.yml and its tests go, and the workflow check in AGENTS.md with them (CG-086)

### E-013 — Two template edges from the plan extraction: example tables and a ctx-only signature

A generated package carries no example tables inside its own core/tables.py, and the docstring checker does not treat a ctx-only signature change as a logic change.
Time: 1.7h since the epic was approved

- The db part ships no example tables inside the package own core/tables.py (CG-087)
- The docstring checker does not count a ctx-only signature change as a logic change (CG-088)

## v1.27.4 — 2026-10-27

### Outside epics

- Template CI no longer runs on tag pushes (three identical gates per release) (CG-078)

## v1.27.3 — 2026-10-23

### Outside epics

- Generated packages run coverage with the ctrace core (sysmon on 3.14 grows memory per CLI invoke) (CG-077)
- Antagor project name in generated packages is the folder name, not the CLI name (CG-076)

## v1.27.2 — 2026-10-23

### Outside epics

- Gate finds the commands of a CLI whose help is translated (CG-074)
- Update instructions: option change can delete edited files; stash, conflicts, revoked keys (CG-075)

## v1.27.1 — 2026-10-22

### E-007 — Simpler package upkeep: one gate line, a gate that lists every red step, documented modules

A template update touches the gate tag in one package file and never conflicts on it; one gate run shows every red step; every module a package gets from the template has a module docstring. Every change makes the template, its upkeep, its updates or its use by packages simpler; none adds a new part.
Time: 2.1h since the epic was approved

- rb-release check --keep-going runs every step and lists all failed steps (CG-072)
- Every Python module a package gets from the template has a module docstring; init's help names the package's folder (CG-073)

## v1.27.0 — 2026-10-22

### E-007 — Simpler package upkeep: one gate line, a gate that lists every red step, documented modules

A template update touches the gate tag in one package file and never conflicts on it; one gate run shows every red step; every module a package gets from the template has a module docstring. Every change makes the template, its upkeep, its updates or its use by packages simpler; none adds a new part.
Time: 1.5h since the epic was approved

- The gate command with its tag lives only in the package's CI workflow; Antagor's checks hold no gate (CG-071)

## v1.26.8 — 2026-10-22

### Outside epics

- The package's config test no longer asserts Antagor's prefix rule or schema (CG-070)

## v1.26.7 — 2026-10-22

### Outside epics

- Antagor owns its files: the template ships only package facts and the skill runs antagor new (CG-069)

## v1.26.6 — 2026-10-21

### Outside epics

- A package with the remote gate passes the template's CI test, and the template gate runs the whole suite of a fast-mode package (CG-067)
- Error messages and verbose lines keep text in square brackets in human output (CG-068)

## v1.26.5 — 2026-10-21

### Outside epics

- Template keeps Antagor's ignore file, takes only Antagor's prefixes, and its config test lets a package set its own checks (CG-066)

## v1.26.4 — 2026-10-21

### Outside epics

- Template follows Antagor's own rules: it stops shipping and testing Antagor's ignore file (scratch/), and the prefix question takes Antagor's prefixes (MEDIAGEN) (CG-065)

## v1.26.3 — 2026-10-21

### Outside epics

- Package docs take Antagor's own layout skeleton and keep only the package's rules; the template and skill do not retell Antagor (CG-064)

## v1.26.2 — 2026-10-21

### Main

- existing-package mode: no per-package remote-gate-accept (one --any-repo consent covers every package)


## v1.26.1 — 2026-10-21

### Outside epics

- Template follows current Antagor: only package facts in its Antagor files, remote publish gate, heavy gate, and this repo's CI checks against Antagor main every night (CG-063)

## v1.26.0 — 2026-10-21

### Outside epics

- doctor is healthy on a server with env credentials and no keychain, and outside a project (CG-061)
- doctor stays offline, and the package CI runs on the remote gate's branch antagor/publish-* (CG-062)

## v1.25.8 — 2026-10-21

### Outside epics

- Gate runs on Python 3.11 again, so a package on requires-python >=3.11 takes a new gate tag with no Python change (CG-060)

## v1.25.7 — 2026-10-21

### Outside epics

- Tests pass in CI as on the Mac: the template's tests pass under the CI variables, and the gate runs pytest with them (CG-057)
- Package rules say when a change is the Architect's hand fix and when it is a task (CG-058)

## v1.25.6 — 2026-10-21

### Outside epics

- One Python everywhere: packages and the gate require Python 3.14, and CI runs on 3.14 (CG-056)

## v1.25.5 — 2026-10-21

### Outside epics

- Template-gate CI: drop the antagor --version step line (antagor has no such option) (CG-055)

## v1.25.4 — 2026-10-21

### Outside epics

- Existing-package mode and Standard: the Antagor path, the gate tag of an old package, the old gate, the install choice, the gate in CI after the push (CG-054)

## v1.25.3 — 2026-10-21

### Outside epics

- This repo's template gate runs in Gitea Actions on homeserver (CG-053)

## v1.25.2 — 2026-10-21

### Outside epics

- Template, gate and skill cite no cli-generator development docs: no old reference files, § numbers, ADRs or ticket ids (CG-052)

## v1.25.1 — 2026-10-21

### Outside epics

- Standard names no ADR of cli-generator: packages have their own docs/adr (CG-051)

## v1.25.0 — 2026-10-20

### E-006 — Minimal template with optional parts, and the skill in two modes

A new package from the template has only what the Standard makes mandatory and passes the gate; each optional part is one copier question, off by default, on when the package needs it. Existing packages lose nothing on copier update. The skill has two modes: new package (template, then gate) and existing package (gate, then fix every red step by the Standard section it names).
Time: 1.1h since the epic was approved

- Skill: SKILL.md picks the mode; the new-package mode is template, then gate (CG-048)
- Skill: the existing-package mode is gate, then fix each red step by its Standard section (CG-049)
- Template gate: the update round from the previous tag expects the parts that package had, not every part (CG-050)

## v1.24.0 — 2026-10-20

### E-006 — Minimal template with optional parts, and the skill in two modes

A new package from the template has only what the Standard makes mandatory and passes the gate; each optional part is one copier question, off by default, on when the package needs it. Existing packages lose nothing on copier update. The skill has two modes: new package (template, then gate) and existing package (gate, then fix every red step by the Standard section it names).
Time: 0.8h since the epic was approved

- Template: a minimal package by default, each optional part a copier question; no docs/OpenCLI, CI always (CG-047)

## v1.23.2 — 2026-10-20

### Outside epics

- Skill and README run the gate through uvx; no rb-cli-core or adopt_core left (CG-046)

## v1.23.1 — 2026-10-20

### Outside epics

- The gate takes --json given as a global option: a chained group's steps pass json and errors (CG-045)

## v1.23.0 — 2026-10-20

### E-005 — One Standard, checked by the gate; the gate lives in cli-generator and cli-core is retired

One short English Standard (skills/cli-builder/reference/standard.md) with every rule marked mandatory or recommended. rb-release check verifies every mandatory rule from outside, on any package, and names the rule it fails. The gate's code lives in this repo (gate/); a package runs it with one uvx command pinned to the template tag, as a development tool only. cli-core is gone: repo, project, folder and registry package.
Time: 1.6h since the epic was approved

- standard.md: one English Standard with every rule marked Mandatory or Recommended, replacing the three reference files (CG-044)

## v1.22.0 — 2026-10-20

### E-005 — One Standard, checked by the gate; the gate lives in cli-generator and cli-core is retired

One short English Standard (skills/cli-builder/reference/standard.md) with every rule marked mandatory or recommended. rb-release check verifies every mandatory rule from outside, on any package, and names the rule it fails. The gate's code lives in this repo (gate/); a package runs it with one uvx command pinned to the template tag, as a development tool only. cli-core is gone: repo, project, folder and registry package.
Time: 1.3h since the epic was approved

- The gate checks the Standard's mandatory rules from outside and names the section a package breaks (CG-043)

## v1.21.0 — 2026-10-20

### E-005 — One Standard, checked by the gate; the gate lives in cli-generator and cli-core is retired

One short English Standard (skills/cli-builder/reference/standard.md) with every rule marked mandatory or recommended. rb-release check verifies every mandatory rule from outside, on any package, and names the rule it fails. The gate's code lives in this repo (gate/); a package runs it with one uvx command pinned to the template tag, as a development tool only. cli-core is gone: repo, project, folder and registry package.
Time: 0.9h since the epic was approved

- The gate moves into gate/ of this repo; the template runs it through uvx at its tag instead of copying it (CG-042)

## v1.20.10 — 2026-10-20

### Outside epics

- Packages can bundle extra agent skills; skill install, skill list and describe serve them (CG-041)

## v1.20.9 — 2026-10-20

### Outside epics

- copier_update_staged.py runs on a clean tree too, so a worker always uses it (CG-037)

## v1.20.8 — 2026-10-20

### Outside epics

- Update mode works for a worker that may not commit; step 14 names .agents/antagor/antagor.toml (CG-036)

## v1.20.7 — 2026-10-19

### E-004 — Packages can take the release gate from rb-cli-core (adopt_core), first step of the core library

A package that answers adopt_core=yes runs the gate as 'uv run rb-release check' from rb-cli-core (Gitea registry, version range >=0.1.2,<0.2); its copy of scripts/release.py is gone; CI, antagor.toml and the project docs call the command; the gate output and exit codes are the same as before. A package that answers no is untouched. The skill tells a package agent each step; new packages start with yes.
Time: 0.8h since the epic was approved

- Switching an existing package to adopt_core keeps its own readme: test and Update step follow (CG-035)

## v1.20.6 — 2026-10-19

### E-004 — Packages can take the release gate from rb-cli-core (adopt_core), first step of the core library

A package that answers adopt_core=yes runs the gate as 'uv run rb-release check' from rb-cli-core (Gitea registry, version range >=0.1.2,<0.2); its copy of scripts/release.py is gone; CI, antagor.toml and the project docs call the command; the gate output and exit codes are the same as before. A package that answers no is untouched. The skill tells a package agent each step; new packages start with yes.
Time: 0.6h since the epic was approved

- Install instructions in generated README and skill are right for a Gitea repository_url (CG-034)

## v1.20.5 — 2026-10-19

### E-004 — Packages can take the release gate from rb-cli-core (adopt_core), first step of the core library

A package that answers adopt_core=yes runs the gate as 'uv run rb-release check' from rb-cli-core (Gitea registry, version range >=0.1.2,<0.2); its copy of scripts/release.py is gone; CI, antagor.toml and the project docs call the command; the gate output and exit codes are the same as before. A package that answers no is untouched. The skill tells a package agent each step; new packages start with yes.
Time: 0.6h since the epic was approved

- Skill and standard: new packages take the gate from rb-cli-core; Update mode has the switch step (CG-032)
- Template: CI, antagor checks and project docs call rb-release check when the project has no gate script (CG-033)

## v1.20.4 — 2026-10-19

### E-004 — Packages can take the release gate from rb-cli-core (adopt_core), first step of the core library

A package that answers adopt_core=yes runs the gate as 'uv run rb-release check' from rb-cli-core (Gitea registry, version range >=0.1.2,<0.2); its copy of scripts/release.py is gone; CI, antagor.toml and the project docs call the command; the gate output and exit codes are the same as before. A package that answers no is untouched. The skill tells a package agent each step; new packages start with yes.
Time: 0.3h since the epic was approved

- Template: adopt_core question takes the gate from rb-cli-core (CG-031)

## v1.20.3 — 2026-10-19

### E-003 — Packages under the sysadmin contract: Gitea CI, secret scan, registry deps, key names, update readiness

A package generated or updated from the new template release has a green CI in Gitea, a gate that refuses a committed secret, dependencies on our packages through the Gitea registry, Gitea URLs in its copier answers, and a template update that runs without questions or keys. The skill's Update mode tells a package agent every step. A report shows which packages lag behind the latest template tag.
Time: 0.6h since the epic was approved

- Standard and skill follow the sysadmin contract; Update mode has the migration steps (CG-029)
- Template CI installs osv-scanner and gitleaks, so CI runs the full gate (CG-030)

## v1.20.2 — 2026-10-19

### E-003 — Packages under the sysadmin contract: Gitea CI, secret scan, registry deps, key names, update readiness

A package generated or updated from the new template release has a green CI in Gitea, a gate that refuses a committed secret, dependencies on our packages through the Gitea registry, Gitea URLs in its copier answers, and a template update that runs without questions or keys. The skill's Update mode tells a package agent every step. A report shows which packages lag behind the latest template tag.
Time: 0.6h since the epic was approved

- Gate refuses committed secrets and resolves our packages only from the Gitea index (CG-027)

## v1.20.1 — 2026-10-19

### E-003 — Packages under the sysadmin contract: Gitea CI, secret scan, registry deps, key names, update readiness

A package generated or updated from the new template release has a green CI in Gitea, a gate that refuses a committed secret, dependencies on our packages through the Gitea registry, Gitea URLs in its copier answers, and a template update that runs without questions or keys. The skill's Update mode tells a package agent every step. A report shows which packages lag behind the latest template tag.
Time: 0.2h since the epic was approved

- Template CI runs in Gitea Actions (CG-026)
- Template updates run unattended, and a report shows lagging packages (CG-028)

## v1.20.0 — 2026-10-18

### E-002 — Auto-install: every package declares [tool.rb.install]; the skill no longer messages sysadmin

A package made by the skill carries [tool.rb.install]; after its first tag sysadmin's tool-updater (homeserver) and Mac agent install it with no message and no tools.toml edit; the skill installs it once on the Mac right after the first tag for instant use.
Time: 0.3h since the epic was approved

- Gate: release.py --check refuses a missing or malformed [tool.rb.install] (CG-024)
- Contract and skill: [tool.rb.install] decides installation; the skill installs once on the Mac and no longer messages sysadmin (CG-025)

## v1.19.0 — 2026-10-18

### E-002 — Auto-install: every package declares [tool.rb.install]; the skill no longer messages sysadmin

A package made by the skill carries [tool.rb.install]; after its first tag sysadmin's tool-updater (homeserver) and Mac agent install it with no message and no tools.toml edit; the skill installs it once on the Mac right after the first tag for instant use.
Time: 0.2h since the epic was approved

- Template: [tool.rb.install] in every generated project, from copier questions (CG-023)

## v1.18.2 — 2026-10-18

### Outside epics

- Шаблон: тесты проходят в Gitea Actions — снимки справки при GITHUB_ACTIONS, detach видит зомби как завершённый (CG-020)

## v1.18.1 — 2026-10-18

### Outside epics

- Справка: правки по ревью E-001 — пример не запускает callback, код EXAMPLE_OUTSIDE_PATH, тексты (CG-019)

## v1.18.0 — 2026-10-18

### E-001 — Human help for every CLI: docs command and help standard in the template

Every generated CLI has '<cli> docs': a deterministic OpenCLI document InSpectra renders into a readable HTML page; the help standard lives in reference/help-standard.md and a test enforces it on every command, with a project allowlist for old commands; describe stays the same machine contract plus arity.maximum.
Time: 1.3h since the epic was approved

- Шаблон: тест стандарта справки над каждой командой и allowlist проекта (CG-017)

## v1.17.0 — 2026-10-18

### E-001 — Human help for every CLI: docs command and help standard in the template

Every generated CLI has '<cli> docs': a deterministic OpenCLI document InSpectra renders into a readable HTML page; the help standard lives in reference/help-standard.md and a test enforces it on every command, with a project allowlist for old commands; describe stays the same machine contract plus arity.maximum.
Time: 1.1h since the epic was approved

- Шаблон: команда docs — OpenCLI-документ для InSpectra, describe + arity.maximum (CG-016)
- Справочники: стандарт справки (help-standard.md), docs в architecture/conventions, Update mode (CG-018)

## v1.16.1 — 2026-10-18

### Outside epics

- Публикация: убрать запасной путь new-repo-in-gitea.sh, сообщать sysadmin о новом репо (CG-015)

## v1.16.0 — 2026-10-18

### Outside epics

- Убрать агента tools из навыка, справочников и шаблона; публикация через Gitea (CG-014)

## v1.15.0 — 2026-10-06

### Changed

- Идея: линтер или check для правил httpx-вне-providers и print() (CG-011)
- Шаблон: тест AGENTS.md без магического числа, FAILED в check_template.sh (CG-013)

### Documentation

- Навык: Update mode для проекта со старым скриптом релиза и деплоя (CG-012)

## v1.14.0 — 2026-10-06

### Changed

- Шаблон: убрать мёртвый staged и укрепить default antagor_prefix (CG-008)
- Шаблон: правки CODING_STANDARDS, CONTEXT и README по ревью CG-006 (CG-010)

### Documentation

- Навык и справочники плагина: Antagor вместо towncrier, хуков и ручного релиза (CG-007)

## v1.13.0 — 2026-10-06

### Added

- Шаблон: AGENTS.md и CLAUDE.md проекта — только указатели (CG-009)

## v1.12.0 — 2026-10-06

### Added

- Шаблон: раскладка методологии (AGENTS-указатели, CONTEXT, CODING_STANDARDS, docs/adr) (CG-006)

## v1.11.0 — 2026-10-06

### Added

- Шаблон: .agents/antagor, deploy.sh и вопрос antagor_prefix (CG-005)

## v1.10.0 — 2026-10-06

### Added

- Шаблон: убрать свои хуки проекта (.githooks, install_hooks.sh, .claude/settings.json) (CG-004)

## v1.9.0 — 2026-10-06

### Added

- Шаблон без towncrier и фрагментов, release.py — только --check (CG-003)

## v1.8.3 — 2026-10-06

### Changed

- scripts/deploy.sh: push main+тег и уведомление tools о версии шаблона (CG-002)

## v1.8.2 — 2026-10-06

### Changed

- scripts/check_template.sh: гейт шаблона одной командой (CG-001)
