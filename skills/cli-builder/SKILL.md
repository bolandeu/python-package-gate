---
name: cli-builder
description: Use when the task is to create a new CLI tool/package, or to refactor/audit an existing CLI or script onto a single shared architecture (Python + uv + Typer, project-local config, OS-keychain credentials, dual human/JSON output, AI-readable errors). Triggers on requests like "create a CLI for X", "build a command-line tool that...", "refactor this script into a proper CLI", "bring this package under our CLI architecture".
---

# CLI Builder

This skill produces every CLI tool under one architecture, so that a year from
now any of them can be opened by a coding agent and understood without
re-deriving conventions. Pick the mode first, then follow its file.

- **New package** — no working CLI exists yet: read `reference/new-package.md`.
- **Existing CLI or package** — a CLI, script or package already exists (with or
  without a `.copier-answers.yml`): read `reference/existing-package.md`.

Read `reference/standard.md` (the Standard) once per session before
generating or judging any code — it is what every package must
(**Mandatory**, checked by the gate) and should (**Recommended**) be.

The Standard governs the package's *shape*. The code you actually write
inside it is governed by these four rules instead
(adapted from the MIT-licensed [karpathy-guidelines](https://github.com/multica-ai/andrej-karpathy-skills)):

1. **Think before coding.** State assumptions; if multiple interpretations
   exist, present them instead of picking silently; push back if the task
   implies more than it needs.
2. **Simplicity first.** Minimum code that solves the task — no commands,
   providers, or config fields beyond what was asked; no abstractions for
   single-use code; no error handling for scenarios that can't happen.
3. **Surgical changes.** Touch only what the request requires — don't
   reformat, "improve," or refactor adjacent code you weren't asked to touch.
4. **Goal-driven execution, test first.** Turn the task into a verifiable
   check rather than looping on "make it work" — the gate is that check.
   TDD is required and checked (`~/Work/dev/docs/testing.md`): the failing
   test is committed before the code, and its red run goes into the readiness
   report; an existing test is never edited to fit the code — the gate lists
   every test changed or gone since the last tag (`existing tests`), and each
   goes into the report with its reason; acceptance cases come from dev
   with the user, contract tests from the consumer — you write the unit tests
   and pass theirs; mutation testing (`uv run --group mutation mutmut run`)
   now and then, outside the gate.

## Publish

The primary store is Gitea: `https://homeserver.tailee01ab.ts.net:3000/bolandeu/<name>`.
Nobody pushes to GitHub — never run `gh repo create` or a push to a GitHub
remote. `[tool.rb.install]` in `pyproject.toml` decides who installs the
package (Standard, Install). This skill sends no message to sysadmin.

Do this after the gate is green. Always *offer* publishing; don't leave the
package sitting unreleased without asking.

1. **Prepare the local repo.** If the directory isn't a git repo yet:
   `git init -b main && git add -A && git commit -m "Initial commit"`, then
   `git remote add origin https://homeserver.tailee01ab.ts.net:3000/bolandeu/<name>.git`. Then run
   `ANTAGOR_ROLE=architect antagor new --prefix <PREFIX>`: with origin set and that role, `new` runs no repository
   script and asks nothing. It writes Antagor's own files, ignore lines and hooks. Give the Human the steps it lists.
   Commit what it wrote, then tag the commit — the version comes from the tag: `git tag -a v0.1.0 -m v0.1.0`.
2. **Push to Gitea.** The first push on repo init is allowed without asking:
   ```bash
   git push -u origin main --follow-tags
   ```
   The first push creates the repo (push-to-create in the `bolandeu` org;
   outside it Gitea refuses with 403). A new tool going into service needs the
   user's yes **before** its repo exists. If the user declines, say that the
   placeholder in README.md and `src/<package_name>/data/SKILL.md` needs
   filling once a repo exists.
3. **Install once on the Mac**, unless `install_mac` is false:
   ```bash
   uv tool install --index gitea=https://homeserver.tailee01ab.ts.net:3000/api/packages/bolandeu/pypi/simple <dist_name> && <cli_name> --version
   ```
   It must print `0.1.0`. If the registry has no wheel yet, retry later; do not
   install the checkout (`uv tool install .`) and do not use the mirror.
4. **The package knows its own URL.** `repository_url` in
   `.copier-answers.yml`, README.md ("Install") and
   `src/<package_name>/data/SKILL.md` ("Installation") carry the real Gitea URL,
   not an `<owner>/<repo>` placeholder. Commit this before the push.
5. **Releases after that** go through Antagor. Pick the version part by SemVer
   (Standard, Release). One task per change.

## Non-negotiables

The parts of the Standard most likely to get skipped under time pressure:

- Every command has a human mode and a `--json` mode.
- Errors are `CliError` subclasses with a stable `code` and the exit-code table
  (Standard, Errors); every command is wrapped in `@output.guard`; human errors
  go to stderr, stdout carries data only.
- A bare `<cli>` or `<cli> <group>` prints help and exits 0 — groups are made
  with `output.group(...)`, never `typer.Typer(...)`.
- No secret in project config, the repo or arguments.
- `doctor` and `auth status --json` keep their exact shape (Standard, Health).
- The bundled `data/SKILL.md` stays conventions-only: no command list.
- Changed a command's behaviour → update its docstring in the same commit, then
  `uv run pytest --snapshot-update` and read the `tests/snapshots/help/` diff.
  Never bypass the docstring check with `SKIP_DOCSTRING_CHECK` (humans only).
- Versions come only from git tags; dependencies on our other tools by version range
  from the Gitea registry.
- The gate (`gate check`, run through `uvx` at the template tag) is green before every commit. It is local:
  `[publish] gate_command` of `.agents/antagor/antagor.toml` writes the command; Antagor's `checks` hold no gate.
