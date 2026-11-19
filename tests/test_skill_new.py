"""SKILL.md routes to the two mode files; the new-package mode is template, optional parts, own commands, gate."""

import re
from pathlib import Path

SKILLS = Path(__file__).resolve().parent.parent / "skills" / "cli-builder"
SKILL = (SKILLS / "SKILL.md").read_text()
NEW_PACKAGE = (SKILLS / "reference" / "new-package.md").read_text()

QUESTIONS = [
    "include_project",
    "include_auth",
    "include_providers",
    "include_http_provider",
    "include_db",
    "include_skill",
    "include_describe",
    "include_contracts",
]


def test_skill_routes_to_both_mode_files():
    assert "reference/new-package.md" in SKILL
    assert "reference/existing-package.md" in SKILL


def test_skill_has_no_scaffold_refactor_or_update_section():
    headings = re.findall(r"^#+ .*$", SKILL, re.M)
    found = [h for h in headings if re.search(r"Scaffold|Refactor|Update", h)]
    assert not found, found


def test_skill_keeps_frontmatter_and_trigger_description():
    match = re.match(r"---\nname: cli-builder\ndescription: (.+)\n---\n", SKILL)
    assert match, "frontmatter name/description missing"
    assert "create a CLI" in match.group(1)


def test_new_package_copies_the_template_with_minimal_defaults():
    command = re.search(r"uvx copier copy .*?(?=```)", NEW_PACKAGE, re.S)
    assert command, "no copier copy command"
    assert "--defaults" in command.group(0)
    assert "cli-generator.git" in command.group(0)


def test_new_package_lists_every_optional_part_by_its_copier_question():
    missing = [question for question in QUESTIONS if f"`{question}`" not in NEW_PACKAGE]
    assert not missing, missing
    assert "Standard" in NEW_PACKAGE and "Optional parts" in NEW_PACKAGE


def test_new_package_runs_the_uvx_gate_before_every_commit():
    assert "gate check" in NEW_PACKAGE
    assert "#subdirectory=gate" in NEW_PACKAGE
    assert "before every commit" in NEW_PACKAGE


def test_steps_come_in_the_order_template_parts_commands_gate():
    order = [
        NEW_PACKAGE.index(title)
        for title in (
            "## 2. Copy the template",
            "## 3. Turn on only",
            "## 4. Write the package's own commands",
            "## 5. Gate",
        )
    ]
    assert order == sorted(order)
