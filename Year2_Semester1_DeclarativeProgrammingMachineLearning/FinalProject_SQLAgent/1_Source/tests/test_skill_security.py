"""Security and boundary tests for the Domain Skill System.

Verifies:
- Path traversal and symlink confinement.
- Disallowance of executable file extensions (.py, .sh, .exe, etc.).
- File size boundary enforcement.
- Detection of circular and missing dependencies.
- Rejection of malformed metadata or duplicate skill IDs.
"""

from __future__ import annotations

import os
from pathlib import Path
import pytest

from agent.skill_manager import (
    CircularSkillDependencyError,
    ExcessiveSkillSizeError,
    MissingSkillDependencyError,
    SkillManager,
    SkillSecurityError,
    SkillValidationError,
)


def test_path_traversal_detection(tmp_path: Path) -> None:
    skills_root = tmp_path / "skills"
    skills_root.mkdir()

    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    secret_file = outside_dir / "secret.txt"
    secret_file.write_text("super_secret_credentials", encoding="utf-8")

    manager = SkillManager(skills_dir=skills_root)

    # Attempting to validate path outside skills_root should raise SkillSecurityError
    with pytest.raises(SkillSecurityError, match="escapes root skill boundary"):
        manager._validate_safe_path(secret_file, skills_root)


def test_symlink_escape_detection(tmp_path: Path) -> None:
    skills_root = tmp_path / "skills"
    skills_root.mkdir()

    outside_target = tmp_path / "target_outside"
    outside_target.mkdir()
    outside_file = outside_target / "outside.txt"
    outside_file.write_text("some external data", encoding="utf-8")

    # Create symlink inside skills_root pointing outside
    symlink_dir = skills_root / "escaped_skill"
    try:
        symlink_dir.symlink_to(outside_target, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation not supported in this environment")

    # When SkillManager discovers skills, it immediately detects the symlink escape
    with pytest.raises(SkillSecurityError, match="escapes root skill boundary"):
        SkillManager(skills_dir=skills_root)


def test_forbidden_executable_extensions(tmp_path: Path) -> None:
    skills_root = tmp_path / "skills"
    skills_root.mkdir()

    skill_dir = skills_root / "bad_skill"
    skill_dir.mkdir()

    executable_file = skill_dir / "exploit.py"
    executable_file.write_text("print('exploit')", encoding="utf-8")

    # Discovery should immediately reject the directory containing forbidden executable file
    with pytest.raises(SkillSecurityError, match="forbidden executable file extension"):
        SkillManager(skills_dir=skills_root)

    # Test .sh script as well
    executable_file.unlink()
    sh_file = skill_dir / "run.sh"
    sh_file.write_text("#!/bin/bash\necho 1", encoding="utf-8")
    with pytest.raises(SkillSecurityError, match="forbidden executable file extension"):
        SkillManager(skills_dir=skills_root)


def test_file_size_limit_enforcement(tmp_path: Path) -> None:
    skills_root = tmp_path / "skills"
    skills_root.mkdir()

    skill_dir = skills_root / "large_skill"
    skill_dir.mkdir()

    large_file = skill_dir / "SKILL.md"
    # Write 1500 bytes when limit is 1000 bytes
    large_file.write_text("A" * 1500, encoding="utf-8")

    manager = SkillManager(skills_dir=skills_root, max_file_size_bytes=1000)

    with pytest.raises(ExcessiveSkillSizeError, match="exceeds maximum permitted size"):
        manager._check_file_size(large_file)


def test_circular_dependency_detection(tmp_path: Path) -> None:
    skills_root = tmp_path / "skills"
    skills_root.mkdir()

    # Skill A depends on Skill B
    dir_a = skills_root / "skill_a"
    dir_a.mkdir()
    (dir_a / "metadata.yaml").write_text(
        """
skill_id: skill_a
name: Skill A
description: First skill
version: 1.0.0
category: general
dependencies:
  - skill_b
""",
        encoding="utf-8",
    )
    (dir_a / "SKILL.md").write_text("# Skill A", encoding="utf-8")

    # Skill B depends on Skill A
    dir_b = skills_root / "skill_b"
    dir_b.mkdir()
    (dir_b / "metadata.yaml").write_text(
        """
skill_id: skill_b
name: Skill B
description: Second skill
version: 1.0.0
category: general
dependencies:
  - skill_a
""",
        encoding="utf-8",
    )
    (dir_b / "SKILL.md").write_text("# Skill B", encoding="utf-8")

    manager = SkillManager(skills_dir=skills_root)

    with pytest.raises(CircularSkillDependencyError, match="Circular skill dependency detected"):
        manager.resolve_dependencies(["skill_a"])


def test_missing_dependency_detection(tmp_path: Path) -> None:
    skills_root = tmp_path / "skills"
    skills_root.mkdir()

    dir_a = skills_root / "skill_orphan"
    dir_a.mkdir()
    (dir_a / "metadata.yaml").write_text(
        """
skill_id: skill_orphan
name: Skill Orphan
description: Orphan skill
version: 1.0.0
category: general
dependencies:
  - nonexistent_parent
""",
        encoding="utf-8",
    )
    (dir_a / "SKILL.md").write_text("# Skill Orphan", encoding="utf-8")

    manager = SkillManager(skills_dir=skills_root)

    with pytest.raises(MissingSkillDependencyError, match="missing dependency"):
        manager.resolve_dependencies(["skill_orphan"])


def test_missing_skill_markdown_document(tmp_path: Path) -> None:
    skills_root = tmp_path / "skills"
    skills_root.mkdir()

    bad_dir = skills_root / "incomplete_skill"
    bad_dir.mkdir()
    (bad_dir / "metadata.yaml").write_text(
        """
skill_id: incomplete_skill
name: Incomplete
description: Missing markdown
version: 1.0.0
category: general
""",
        encoding="utf-8",
    )
    # Note: SKILL.md is deliberately not created

    with pytest.raises(SkillValidationError, match="missing 'SKILL.md'"):
        SkillManager(skills_dir=skills_root)


def test_duplicate_skill_id_detection(tmp_path: Path) -> None:
    skills_root = tmp_path / "skills"
    skills_root.mkdir()

    # Skill in folder 1
    dir1 = skills_root / "dir1"
    dir1.mkdir()
    (dir1 / "metadata.yaml").write_text(
        """
skill_id: same_skill_id
name: Skill One
description: First
version: 1.0.0
category: general
""",
        encoding="utf-8",
    )
    (dir1 / "SKILL.md").write_text("# Skill 1", encoding="utf-8")

    # Skill in folder 2 with identical skill_id
    dir2 = skills_root / "dir2"
    dir2.mkdir()
    (dir2 / "metadata.yaml").write_text(
        """
skill_id: same_skill_id
name: Skill Two
description: Second
version: 1.0.0
category: general
""",
        encoding="utf-8",
    )
    (dir2 / "SKILL.md").write_text("# Skill 2", encoding="utf-8")

    with pytest.raises(SkillValidationError, match="Duplicate skill_id 'same_skill_id'"):
        SkillManager(skills_dir=skills_root)
