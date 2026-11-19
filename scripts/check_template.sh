#!/bin/sh
# Template gate: run the repo tests and the tests of gate/, regenerate template/ as the minimal package
# (default answers), a package with every optional part, credentials alone in a publish-only variant (no
# homeserver users, no Mac) and providers without credentials, prove copier update rounds from the
# previous release tag and from v1.20.10 (the last template that copied the gate) keep every part and drop the
# Gitea workflow, check the rendered [tool.rb.install] and which parts each package has, run the generated
# project's checks and the release gate from this working tree's gate/ through uvx, and check the Antagor project
# name on copy and on update, in place and with a destination argument. Non-zero exit on any failure.
# Usage: sh scripts/check_template.sh
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
WORK=$(mktemp -d "${TMPDIR:-/tmp}/cli-gen-check.XXXXXX")
trap 'rm -rf "$WORK"' EXIT INT TERM

step() { printf '\n==> [%s] %s\n' "$VARIANT" "$*"; }

run() {
    step "$*"
    "$@" || { printf '\nFAILED [%s]: %s\n' "$VARIANT" "$*" >&2; exit 1; }
}

# The last template version that copied the gate into scripts/release.py.
GATE_COPY_TAG=v1.20.10
STANDARD=https://homeserver.tailee01ab.ts.net:3000/bolandeu/cli-generator/src/branch/main/skills/cli-builder/reference/standard.md

fail() { printf '\nFAILED [%s]: %s\n' "$VARIANT" "$*" >&2; exit 1; }

# check_gate_files: the project has no copy of the gate, no adopt_core answer and no rb-cli-core in any
# tracked file; the local gate is the only gate: `[publish] gate_command` of the Antagor config writes the uvx
# gate command at the template tag of .copier-answers.yml and no workflow does; Antagor's checks hold the
# docstring check and no gate command; AGENTS.md and CODING_STANDARDS.md name the gate and no workflow; AGENTS.md
# and the package skill link the Standard and cite no § numbers
check_gate_files() {
    run test ! -e scripts/release.py
    grep -q adopt_core .copier-answers.yml && fail "adopt_core in .copier-answers.yml"
    git grep -q rb-cli-core && fail "rb-cli-core in $(git grep -l rb-cli-core | tr '\n' ' ')"
    tag=$(sed -n 's/^_commit: //p' .copier-answers.yml)
    gate="uvx --from \"git+https://github.com/bolandeu/python-package-gate.git@$tag#subdirectory=gate\" gate check"
    grep -qF "$gate" .agents/antagor/antagor.toml || fail ".agents/antagor/antagor.toml does not call: $gate"
    # README.md is the project's own (copier skips it on update): an old one may still hold the command
    holders=$(git grep -lF 'uvx --from "git+https://github.com/bolandeu/python-package-gate.git@' -- . ':!README.md' | tr '\n' ' ')
    [ "$holders" = ".agents/antagor/antagor.toml " ] || fail "the gate command is in: $holders"
    run python3 -c "
import tomllib
c = tomllib.load(open('.agents/antagor/antagor.toml', 'rb'))
assert 'python3 scripts/check_command_docstrings.py' in c['checks'], c['checks']
assert not any('rb-gate' in check for check in c['checks']), c['checks']
"
    for file in AGENTS.md CODING_STANDARDS.md; do
        grep -qF 'gate check' "$file" || fail "$file does not name the gate"
        grep -qF '.gitea/workflows' "$file" && fail "$file names a Gitea workflow"
    done
    for file in AGENTS.md src/demotool/data/SKILL.md; do
        [ "$file" = AGENTS.md ] || [ -e "$file" ] || continue  # the package skill is an optional part
        grep -qF "$STANDARD" "$file" || fail "$file does not link the Standard"
        grep -q '§' "$file" && fail "$file cites a § number"
    done
    return 0
}

# check_antagor_files: the Antagor config runs the gate locally, with no remote gate status;
# AGENTS.md and CODING_STANDARDS.md hold no Antagor rule, no commit-first TDD and no machine-local path
check_antagor_files() {
    run python3 -c "
import tomllib
c = tomllib.load(open('.agents/antagor/antagor.toml', 'rb'))
publish = c['publish']
assert publish.get('gate', 'local') == 'local', publish
assert 'gate_status_url' not in publish, publish
assert publish['gate_command'].endswith('#subdirectory=gate\" gate check'), publish
assert c['heavy'] == ['gate check'], c.get('heavy')
assert 'gate_command' not in c, c
"
    for file in AGENTS.md CODING_STANDARDS.md; do
        grep -qiE 'hand.?fix|hand_fix' "$file" && fail "$file has a hand-fix line"
        grep -q '~/Work/' "$file" && fail "$file names ~/Work/"
        grep -qE 'коммит.* первым|Тест коммитится' "$file" && fail "$file says a test is committed first"
    done
    return 0
}

# part_files <part>: the files of an optional part in a package named demotool; `docs` is the docs
# command and its OpenCLI document, which left the template
part_files() {
    case $1 in
    project) echo src/demotool/commands/project.py src/demotool/commands/init.py src/demotool/commands/config.py \
        src/demotool/commands/status.py src/demotool/core/services.py src/demotool/core/models.py \
        tests/test_project.py tests/test_services.py ;;
    auth) echo src/demotool/commands/login.py src/demotool/credentials tests/test_auth.py ;;
    providers) echo src/demotool/providers tests/test_providers.py ;;
    http) echo src/demotool/providers/http.py tests/test_http_provider.py ;;
    db) echo src/demotool/core/db.py src/demotool/core/tables.py src/demotool/core/normalize.py \
        src/demotool/migrations src/demotool/commands/db.py tests/test_db.py tests/test_normalize.py scripts/pg_test.sh ;;
    skill) echo src/demotool/commands/skill.py src/demotool/core/skills.py src/demotool/data/SKILL.md tests/test_skills.py ;;
    describe) echo src/demotool/commands/describe.py src/demotool/core/opencli.py src/demotool/core/data_files.py \
        tests/test_describe.py tests/data/opencli.schema.json ;;
    contracts) echo tests/contracts tests/test_contracts.py tests/test_contract_runner.py scripts/detach.py \
        scripts/run_detached.sh scripts/runs_status.sh tests/test_detach.py ;;
    docs) echo src/demotool/commands/docs.py src/demotool/core/docs.py tests/test_docs.py ;;
    *) fail "unknown part $1" ;;
    esac
}

# expect_parts <present|absent> <part...>: every file of each part is in the project in the cwd, or none is
expect_parts() {
    want=$1
    shift
    for part in "$@"; do
        for path in $(part_files "$part"); do
            if [ -e "$path" ]; then
                [ "$want" = present ] || fail "$path of the part $part is there"
            else
                [ "$want" = absent ] || fail "$path of the part $part is missing"
            fi
        done
    done
}

# expect_commands <help page...>: the help snapshots the copy task wrote are exactly these pages
expect_commands() {
    found=$(ls tests/snapshots/help | sed 's/\.txt$//' | sort | tr '\n' ' ')
    wanted=$(printf '%s\n' "$@" | sort | tr '\n' ' ')
    [ "$found" = "$wanted" ] || fail "help pages: $found, expected: $wanted"
}

# expect_root_options <present|absent> <option...>: the root --help lists each option, or none of them
expect_root_options() {
    want=$1
    shift
    root_help=$(env -u GITHUB_ACTIONS -u FORCE_COLOR -u PY_COLORS uv run demotool --help)
    for option in "$@"; do
        if printf '%s' "$root_help" | grep -qE -- "$option( |$)"; then
            [ "$want" = present ] || fail "the root help lists $option"
        else
            [ "$want" = absent ] || fail "the root help does not list $option"
        fi
    done
}

# run_gate: the gate from this working tree's gate/ through uvx; it changes neither pyproject.toml
# nor uv.lock. --no-cache: uvx reuses its cached build of a local directory even when the code changed
# (--refresh and --reinstall do not help, uv 0.10). Arguments go to uvx: `--python 3.11` runs the gate
# on the lowest Python a package may declare.
run_gate() {
    before=$(cat pyproject.toml uv.lock | shasum)
    run uvx --no-cache "$@" --from "$ROOT/gate" gate check
    [ "$(cat pyproject.toml uv.lock | shasum)" = "$before" ] || fail "the gate changed pyproject.toml or uv.lock"
}

# run_gate_on_python_311: the gate on Python 3.11, the lowest a package may declare, over a copy of the
# project in the cwd made 3.11-valid: the template's 3.14-only `except A, B:` gets parentheses and
# requires-python goes to >=3.11 (the gate parses the package's sources with the Python it runs on).
run_gate_on_python_311() {
    dest="$WORK/python311"
    run git clone -q "$PWD" "$dest"
    (
        cd "$dest" || exit 1
        run sed -i.bak -E 's/^requires-python = .*/requires-python = ">=3.11"/' pyproject.toml
        run rm pyproject.toml.bak
        run sed -i.bak -E 's/except ([A-Za-z_.]+(, [A-Za-z_.]+)+):/except (\1):/' \
            $(git ls-files '*.py')
        run find . -name '*.bak' -not -path './.git/*' -delete
        run uv lock -q
        run uv sync -q --python 3.11
        run uv run ruff format -q .
        run git add -A
        run git -c user.name=gate -c user.email=gate@example.invalid commit -q -m python311
        run git -c user.name=gate -c user.email=gate@example.invalid tag -f -a v0.1.0 -m v0.1.0
        run_gate --python 3.11
    ) || exit 1
}

# write_antagor_files, check_antagor_files_kept: the files Antagor owns, as Antagor writes them. The template
# ships none of them; a package that has them keeps them through `copier update`.
ANTAGOR_IGNORE='state/
receipts/
scratch/
'
write_antagor_files() {
    mkdir -p .agents/antagor docs/adr
    printf '%s' "$ANTAGOR_IGNORE" >.agents/antagor/.gitignore
    [ -e CLAUDE.md ] || printf '# CLAUDE.md\n\nRead AGENTS.md.\n' >CLAUDE.md
    [ -e docs/adr/README.md ] || printf '# ADR format\n' >docs/adr/README.md
}
check_antagor_files_kept() {
    [ "$(cat .agents/antagor/.gitignore)" = "$(printf '%s' "$ANTAGOR_IGNORE")" ] || fail "the Antagor ignore file changed"
    for file in CLAUDE.md docs/adr/README.md .agents/antagor/.gitignore; do
        [ "$(git show "HEAD:$file")" = "$(cat "$file")" ] || fail "$file changed in the update"
        test ! -e "$file.rej" || fail "$file has a conflict"
    done
}
# expect_no_antagor_files: a package rendered from the template has none of the files Antagor owns
expect_no_antagor_files() {
    for file in CLAUDE.md docs/adr/README.md .agents/antagor/.gitignore; do
        test ! -e "$file" || fail "the template ships $file"
    done
    for file in AGENTS.md CONTEXT.md CODING_STANDARDS.md .agents/antagor/antagor.toml; do
        test -f "$file" || fail "the template does not ship $file"
    done
    for line in .DS_Store Thumbs.db; do
        grep -qxF "$line" .gitignore || fail ".gitignore lacks $line"
    done
}

# check_module_docstrings: every Python module of the rendered project in the cwd (not of an updated one, which
# keeps files the template no longer renders for it) starts with a module docstring;
# names the modules that do not. The project's own Python parses them: the template uses syntax of its Python
check_module_docstrings() {
    step "every Python module has a module docstring"
    missing=$(find . -name '*.py' -not -path './.git/*' -not -path './.venv/*' | uv run -q python -c "
import ast, sys
for path in sys.stdin.read().split():
    if ast.get_docstring(ast.parse(open(path).read())) is None:
        print(path)
")
    [ -z "$missing" ] || fail "modules without a module docstring: $(echo $missing)"
}

# verify_project <expected (homeserver, mac) as a Python literal>: the checks of a
# generated project, run inside it, then the gate
verify_project() {
    expected_install=$1
    shift
    run uv sync -q
    run uv run python -c "import tomllib; i = tomllib.load(open('pyproject.toml', 'rb'))['tool']['rb']['install']; \
assert (i['homeserver'], i['mac']) == $expected_install, i"
    run uv run ruff check .
    run uv run ruff format --check .
    run uv run ty check
    run env GITHUB_ACTIONS=true FORCE_COLOR=1 PY_COLORS=1 uv run pytest -q
    run git add -A
    run git -c user.name=gate -c user.email=gate@example.invalid commit -q -m i
    run git -c user.name=gate -c user.email=gate@example.invalid tag -a v0.1.0 -m v0.1.0
    check_gate_files
    run_gate
    check_antagor_files
}

# expect_no_gate_workflow: no CI workflow runs the gate — it runs locally (the Standard, CI). A release workflow is
# allowed and shipped: a tag builds the wheel and the sdist and attaches them to the GitHub release.
expect_no_gate_workflow() {
    found=$(grep -rl "gate check" .gitea .github 2>/dev/null || true)
    [ -z "$found" ] || { printf '%s\n' "$found" >&2; fail "a workflow runs the gate"; }
}

# expect_database_errors <present|absent>: the rendered core/errors.py defines the three Database errors, or none
# of them (the db part brings them: a package without it has nothing to raise them)
expect_database_errors() {
    want=$1
    for name in DatabaseUnavailable DatabaseNotMigrated DatabaseTooNew; do
        if grep -q "^class $name(" src/demotool/core/errors.py; then
            [ "$want" = present ] || fail "core/errors.py defines $name without the db part"
        else
            [ "$want" = absent ] || fail "core/errors.py does not define $name with the db part"
        fi
    done
}

# check_variant <name> <expected (homeserver, mac) as a Python literal> [copier --data args...]: the
# shell stays in the project, so the caller checks its parts, then goes back with `cd "$ROOT"`
check_variant() {
    VARIANT=$1
    expected_install=$2
    shift 2
    dest="$WORK/$VARIANT"
    run uvx copier copy "$ROOT" "$dest" \
        --data package_name=demotool --data project_name=Demo \
        --data description=d --data author_name=A "$@" \
        --defaults --trust -q --vcs-ref HEAD
    cd "$dest"
    run git init -q
    run test -f .agents/antagor/antagor.toml
    expect_no_antagor_files
    expect_no_gate_workflow
    check_module_docstrings
    verify_project "$expected_install"
    expect_parts absent docs
}

# generate_at <name> <template tag> [copier copy --data args...]: a committed project generated from
# that tag in $WORK/<name>; the shell stays in it. The copy resolves as on that tag's release day
# (UV_EXCLUDE_NEWER): its own task (pytest --snapshot-update of tests/test_help.py) must run on the typer it was
# released with — a tag before the typer cap resolves 0.29, whose bundled click breaks that test.
generate_at() {
    VARIANT=$1
    from=$2
    shift 2
    dest="$WORK/$VARIANT"
    run env "UV_EXCLUDE_NEWER=$(git -C "$ROOT" log -1 --format=%cI "$from")" uvx copier copy "$ROOT" "$dest" \
        --data package_name=demotool --data project_name=Demo \
        --data description=d --data author_name=A "$@" \
        --defaults --trust -q --vcs-ref "$from"
    cd "$dest"
    run git init -q
    run git add -A
    run git -c user.name=gate -c user.email=gate@example.invalid commit -q -m previous
    write_antagor_files
    run git add -A
    run git -c user.name=gate -c user.email=gate@example.invalid commit -q --allow-empty -m antagor-files
}

# update_staged [copier update args...]: update the project in the cwd to the working tree through the worker
# script (stdin closed, no credential variables)
update_staged() {
    run env -u GH_TOKEN -u GITHUB_TOKEN -u GITHUB_READ_TOKEN -u GITEA_TOKEN -u DOPPLER_TOKEN \
        uvx --from copier python "$ROOT/skills/cli-builder/scripts/copier_update_staged.py" \
        --trust --defaults -q --vcs-ref HEAD "$@" </dev/null
}

# antagor_name: the project name in the Antagor config of the project in the cwd
antagor_name() {
    python3 -c "import tomllib; print(tomllib.load(open('.agents/antagor/antagor.toml', 'rb'))['name'])"
}

# check_name_update <name> <expected name> <in-place|with-dest> [hand-named] [copier copy --data args...]: generate a
# package with the command gsc from the previous release tag (hand-named: then write the expected name into its
# Antagor config by hand; an empty expected name: the name the tag wrote) and update it to the working tree, in place or with the project as the destination
# argument. The Antagor config holds the expected name and has no conflict.
check_name_update() {
    variant=name-$1
    expected=$2
    how=$3
    shift 3
    hand_named=false
    if [ "${1:-}" = hand-named ]; then hand_named=true; shift; fi
    generate_at "$variant" "$previous" --data cli_name=gsc "$@"
    if [ "$hand_named" = true ]; then
        run sed -i.bak "s/^name = .*/name = \"$expected\"/" .agents/antagor/antagor.toml
        run rm .agents/antagor/antagor.toml.bak
        run git -c user.name=gate -c user.email=gate@example.invalid commit -q -am hand-named
    fi
    [ -n "$expected" ] || expected=$(antagor_name)
    if [ "$how" = with-dest ]; then update_staged "$(pwd -P)"; else update_staged; fi
    test ! -e .agents/antagor/antagor.toml.rej || fail "the Antagor config has a conflict"
    grep -q '^<<<<<<< ' .agents/antagor/antagor.toml && fail "the Antagor config has a conflict"
    [ "$(antagor_name)" = "$expected" ] || fail "the Antagor name is $(antagor_name), expected: $expected"
    cd "$ROOT"
}

# check_update_round <name> <template tag> [copier copy --data args...]: with CLEAN_TREE=1 the staged
# change is skipped and the script runs on a clean, committed tree. Generate from that tag, make a
# staged, uncommitted change, update to the working tree through the worker script, check the
# change survived and no file of the package was removed but those in $REMOVABLE (the docs command,
# its OpenCLI document and what left the template before) and every part of $PARTS is still there, then
# run the full checks in the updated project.
check_update_round() {
    generate_at "$@"
    if [ -n "${FAST_CHECKS:-}" ]; then
        # A package of mode fast: its checks are its own, without the gate command.
        run python3 - <<'PY'
import re
path = ".agents/antagor/antagor.toml"
text = open(path).read()
text = re.sub(r"(?m)^checks = .*$", 'checks = ["uv run pytest -q --no-cov {test_paths}", "python3 scripts/check_command_docstrings.py"]', text)
open(path, "w").write(text)
PY
        run git add -A
        run git -c user.name=gate -c user.email=gate@example.invalid commit -q -m fast-checks
    fi
    if [ -z "${CLEAN_TREE:-}" ]; then
        # The change a worker that may not commit holds: `_src_path` written another way (a trailing slash).
        run sed -i.bak -E 's|^(_src_path: .*[^/])$|\1/|' .copier-answers.yml
        run rm .copier-answers.yml.bak
        grep -qE '^_src_path: .*/$' .copier-answers.yml || { printf '\nFAILED [%s]: gate edit missing\n' "$VARIANT" >&2; exit 1; }
    fi
    update_staged
    if [ -n "${FAST_CHECKS:-}" ]; then
        # The lines both sides changed: the template dropped the gate from `checks` and renamed the gate in `heavy`,
        # the package wrote its own `checks`. One conflict, two lines; the package keeps its `checks`, the template's
        # `heavy` is taken, as the update step of the skill says.
        conflicts=$(grep -rlE '^<<<<<<< ' . --exclude-dir=.git --exclude-dir=.venv | tr '\n' ' ')
        [ -z "$conflicts" ] || [ "$conflicts" = "./.agents/antagor/antagor.toml " ] || fail "conflicts in: $conflicts"
        run python3 - <<'PY'
import re
path = ".agents/antagor/antagor.toml"
text = open(path).read()
text = re.sub(r"(?ms)^<<<<<<< .*?\n=======\n.*?\n>>>>>>> [^\n]*\n", 'checks = ["uv run pytest -q --no-cov {test_paths}", "python3 scripts/check_command_docstrings.py"]\nheavy = ["gate check"]\n', text)
open(path, "w").write(text)
PY
    fi
    if [ -z "${CLEAN_TREE:-}" ]; then
        grep -qE '^_src_path: .*/$' .copier-answers.yml || { printf '\nFAILED [%s]: staged change lost\n' "$VARIANT" >&2; exit 1; }
    fi
    removed=$(git ls-tree -r --name-only HEAD | while IFS= read -r path; do
        [ -e "$path" ] || printf '%s\n' "$path"
    done)
    for path in $removed; do
        case " $REMOVABLE " in
        *" $path "*) ;;
        *) fail "copier update removed $path" ;;
        esac
    done
    expect_parts present $PARTS
    expect_parts absent docs
    expect_no_gate_workflow
    check_antagor_files_kept
    # The help page of the docs command is the project's own file: the update leaves it to the project.
    run rm -f tests/snapshots/help/docs.txt
    # A template release that changes a help text or `describe` changes the snapshots: the project
    # refreshes them after an update (copier's task runs on copy only).
    run uv run --quiet pytest --snapshot-update --no-cov -q -p no:cacheprovider tests/test_help.py tests/test_describe.py
    verify_project '(["rbtools"], True)'
    cd "$ROOT"
}

VARIANT=repo-tests
run uv run --with pytest --with pyyaml pytest -q "$ROOT/tests"
VARIANT=gate-tests
run uv run --directory "$ROOT/gate" ruff check .
run uv run --directory "$ROOT/gate" ruff format --check .
run uv run --directory "$ROOT/gate" ty check
run uv run --directory "$ROOT/gate" pytest -q

VARIANT=template
grep -rq include_ci "$ROOT/copier.yml" "$ROOT/template" && fail "include_ci is still in the template"
grep -rq 'TyperOption' "$ROOT/template" && fail "template code builds a TyperOption: a part declares its global option in a signature"

check_variant minimal '(["rbtools"], True)' --data repository_url=https://homeserver.tailee01ab.ts.net:3000/bolandeu/demo
run_gate_on_python_311
expect_parts absent project auth providers db skill describe contracts
expect_database_errors absent
expect_commands auth auth-status doctor run
expect_root_options absent --project --ai
cd "$ROOT"
check_variant all-parts '(["rbtools"], True)' --data include_project=true --data include_auth=true \
    --data include_db=true --data include_skill=true --data include_describe=true --data include_contracts=true
expect_parts present project auth providers http db skill describe contracts
expect_database_errors present
expect_root_options present --project --ai
cd "$ROOT"
check_variant auth-publish-only '([], False)' --data include_auth=true \
    --data install_homeserver_users= --data install_mac=false \
    --data repository_url=https://github.com/bolandeu/demo
expect_parts present auth providers http
expect_parts absent project db skill describe contracts
cd "$ROOT"
check_variant providers-without-auth '(["rbtools"], True)' --data include_providers=true --data include_http_provider=false
expect_parts present providers
expect_parts absent auth http
cd "$ROOT"
VARIANT=prefix
for prefix in MEDIAGEN ABCDEFGHIJ; do
    run uvx copier copy "$ROOT" "$WORK/prefix-$prefix" --data package_name=demotool --data project_name=Demo \
        --data description=d --data author_name=A --data antagor_prefix=$prefix --defaults --trust -q --vcs-ref HEAD
    grep -qx "prefix = \"$prefix\"" "$WORK/prefix-$prefix/.agents/antagor/antagor.toml" || fail "prefix $prefix not in antagor.toml"
done
for prefix in ABCDEFGHIJK mg 1AB; do
    step "copier refuses antagor_prefix=$prefix"
    if uvx copier copy "$ROOT" "$WORK/prefix-bad" --data package_name=demotool --data project_name=Demo \
        --data description=d --data author_name=A --data antagor_prefix=$prefix --defaults --trust -q --vcs-ref HEAD >/dev/null 2>&1; then
        fail "antagor_prefix=$prefix was accepted"
    fi
done
VARIANT=antagor-name
# The Antagor project name is the destination folder of `copier copy`, never the command or the repository name.
GSC_URL=https://homeserver.tailee01ab.ts.net:3000/bolandeu/google-search-console
mkdir -p "$WORK/name-dot/demo-folder"
run uvx copier copy "$ROOT" "$WORK/demo-folder" --data package_name=demotool --data project_name=Demo \
    --data description=d --data author_name=A --data cli_name=gsc --data repository_url=$GSC_URL \
    --defaults --trust -q --vcs-ref HEAD
[ "$(cd "$WORK/demo-folder" && antagor_name)" = demo-folder ] || fail "the name is not demo-folder"
(
    cd "$WORK/name-dot/demo-folder" || exit 1
    run uvx copier copy "$ROOT" . --data package_name=demotool --data project_name=Demo \
        --data description=d --data author_name=A --data cli_name=gsc --data repository_url=$GSC_URL \
        --defaults --trust -q --vcs-ref HEAD
    [ "$(antagor_name)" = demo-folder ] || fail "the name of a copy into . is not demo-folder"
) || exit 1
VARIANT=fast-config
run uvx copier copy "$ROOT" "$WORK/fast-config" --data package_name=demotool --data project_name=Demo \
    --data description=d --data author_name=A --defaults --trust -q --vcs-ref HEAD
(
    cd "$WORK/fast-config"
    # A package of mode fast with Antagor's own lines: its checks without the gate command, a worker, a changed
    # review section; the full gate only through the remote gate and `heavy`.
    run python3 - <<'PY'
import re
path = ".agents/antagor/antagor.toml"
text = open(path).read()
text = re.sub(r"(?m)^checks = .*$", 'checks = ["uv run pytest -q --no-cov {test_paths}", "python3 scripts/check_command_docstrings.py"]', text)
text = text.replace('heavy = ["gate check"]', 'mode = "fast"\nworker = "claude-code"\nheavy = ["gate check"]')
text = text.replace('required_types = ["feature", "bugfix"]', 'required_types = ["feature"]\nreviewer = "claude-code"')
# Antagor owns the schema number and the prefix rule: the package's tests do not assert them.
text = re.sub(r"(?m)^schema = .*$", "schema = 2", text)
text = re.sub(r"(?m)^prefix = .*$", 'prefix = "ABCDEFGHIJKL"', text)
open(path, "w").write(text)
PY
    run uv sync -q
    run uv run pytest -q --no-cov
) || exit 1
previous=$(git -C "$ROOT" tag --list 'v*' --sort=-v:refname | head -n 1)
[ -n "$previous" ] || { VARIANT=update-round; fail "no release tag to update from"; }
# An update never changes the Antagor name: neither a name written by hand nor the command the template wrote.
DATAIO_URL=https://github.com/bolandeu/rb-dataio
check_name_update dataio dataio in-place hand-named --data repository_url=$DATAIO_URL
check_name_update dataio-dest dataio with-dest hand-named --data repository_url=$DATAIO_URL
check_name_update unedited "" in-place --data repository_url=$GSC_URL
check_name_update unedited-dest "" with-dest --data repository_url=$GSC_URL
DOCS_FILES=$(part_files docs)
# A package from a tag that still rendered the Gitea workflow loses it on update: the gate is local now.
WORKFLOW_FILES=".gitea/workflows/ci.yml tests/test_ci.py"
REMOVABLE="$DOCS_FILES $WORKFLOW_FILES"
# A tag with the part questions generates a package with every part on (its default is none); an older tag
# had the parts without questions (ADR 0014).
if git -C "$ROOT" show "$previous:copier.yml" | grep -q '^include_project:'; then
    PARTS="project auth providers http db skill describe contracts"
    check_update_round update-round "$previous" --data include_project=true --data include_auth=true \
        --data include_db=true --data include_skill=true --data include_describe=true --data include_contracts=true
    FAST_CHECKS=1
    check_update_round update-fast-checks "$previous" --data include_project=true \
        --data include_auth=true --data include_db=true --data include_skill=true --data include_describe=true \
        --data include_contracts=true
    FAST_CHECKS=
else
    PARTS="project auth providers http skill describe contracts"
    check_update_round update-round "$previous"
    FAST_CHECKS=1
    check_update_round update-fast-checks "$previous"
    FAST_CHECKS=
fi
PARTS="project auth providers http skill describe contracts"
REMOVABLE="$DOCS_FILES $WORKFLOW_FILES scripts/release.py tests/data/index/gitea/rb_x-0.1.0-py3-none-any.whl tests/data/index/pypi/rb_x-0.9.0-py3-none-any.whl"
check_update_round update-from-copy "$GATE_COPY_TAG"

printf '\nOK: template gate passed (repo tests, gate tests, minimal, all parts, credentials publish-only, providers without credentials, update rounds)\n'
