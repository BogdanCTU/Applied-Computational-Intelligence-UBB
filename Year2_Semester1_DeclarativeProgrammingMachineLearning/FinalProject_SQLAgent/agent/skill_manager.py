"""Domain Skill Manager for Local Report SQL Agent.

Handles:
- Safe, deterministic filesystem discovery of Markdown domain skills.
- Metadata and semver validation.
- Dependency resolution with Kahn's algorithm cycle detection.
- Token-budget-aware selective skill loading without truncation.
- Persistent SQLite registry synchronization.
- Path traversal and symlink escape security controls.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from agent.skill_models import (
    CURRENT_SKILL_SYSTEM_VERSION,
    LoadedSkill,
    SkillLoadResult,
    SkillMetadata,
    SkillValidationResult,
    estimate_tokens,
    safe_parse_yaml,
)
from config.paths import resolve_path

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SkillError(Exception):
    """Base exception for skill-system failures."""


class SkillNotFoundError(SkillError):
    """Raised when a requested skill ID does not exist."""


class SkillValidationError(SkillError):
    """Raised when skill metadata or files fail validation."""


class MissingSkillDependencyError(SkillError):
    """Raised when a required skill dependency is missing or disabled."""


class CircularSkillDependencyError(SkillError):
    """Raised when a cyclic dependency chain is detected among skills."""


class ExcessiveSkillSizeError(SkillError):
    """Raised when a skill markdown instruction exceeds permitted file size limits."""


class SkillSecurityError(SkillError):
    """Raised when path traversal, symlink escape, or unsafe files are detected."""


# ---------------------------------------------------------------------------
# Skill Manager
# ---------------------------------------------------------------------------


class SkillManager:
    """Discovers, validates, registers, and selectively loads domain skills."""

    def __init__(
        self,
        skills_dir: Path | str | None = None,
        repository: Any | None = None,
        *,
        max_file_size_bytes: int = 500_000,
        auto_sync_repo: bool = True,
    ) -> None:
        if skills_dir:
            self.skills_dir = Path(skills_dir).resolve()
        else:
            from config.paths import app_root, is_frozen, resource_root

            cand = None
            if is_frozen():
                for alt in [resource_root() / "skills", app_root() / "skills"]:
                    if alt.exists() and any(alt.iterdir()):
                        cand = alt
                        break
            if cand is None:
                cand = resolve_path("skills")
            if not cand.exists():
                pkg_cand = Path(__file__).resolve().parents[1] / "skills"
                if pkg_cand.exists() and any(pkg_cand.iterdir()):
                    cand = pkg_cand
            self.skills_dir = cand

        self.repository = repository
        self.max_file_size_bytes = int(max_file_size_bytes)
        self.auto_sync_repo = auto_sync_repo

        self._skills: dict[str, SkillMetadata] = {}
        self._skill_docs: dict[str, Path] = {}
        self._skill_meta_paths: dict[str, Path] = {}

        if self.skills_dir.exists():
            self.discover_skills()

    # -----------------------------------------------------------------------
    # Discovery & Validation
    # -----------------------------------------------------------------------

    def discover_skills(self) -> list[SkillMetadata]:
        """Scan skills_dir for valid subdirectories with metadata.yaml and SKILL.md.

        Deterministic: Scans directories in alphabetical order.
        """
        self._skills.clear()
        self._skill_docs.clear()
        self._skill_meta_paths.clear()

        if not self.skills_dir.exists():
            log.warning("Skills directory does not exist: %s", self.skills_dir)
            return []

        # List subdirectories sorted deterministically
        subdirs = sorted([d for d in self.skills_dir.iterdir() if d.is_dir()])
        discovered: list[SkillMetadata] = []

        for subdir in subdirs:
            # 1. Path safety check for subdirectory and its contents
            self._validate_safe_path(subdir, self.skills_dir)
            for item in subdir.iterdir():
                self._validate_safe_path(item, self.skills_dir)

            # Look for metadata file (.yaml, .yml, or .json)
            meta_candidates = [
                subdir / "metadata.yaml",
                subdir / "metadata.yml",
                subdir / "metadata.json",
            ]
            meta_file = next((f for f in meta_candidates if f.exists()), None)
            if not meta_file:
                continue

            self._validate_safe_path(meta_file, self.skills_dir)
            self._check_file_size(meta_file)

            # Look for instruction markdown file
            doc_candidates = [
                subdir / "SKILL.md",
                subdir / "skill.md",
                subdir / "INSTRUCTIONS.md",
            ]
            doc_file = next((f for f in doc_candidates if f.exists()), None)
            if not doc_file:
                raise SkillValidationError(
                    f"Skill directory '{subdir.name}' is missing 'SKILL.md' instruction document."
                )

            self._validate_safe_path(doc_file, self.skills_dir)
            self._check_file_size(doc_file)

            # Parse and validate metadata
            try:
                raw_text = meta_file.read_text(encoding="utf-8")
                parsed_dict = safe_parse_yaml(raw_text)
                metadata = SkillMetadata.model_validate(parsed_dict)
            except Exception as e:
                raise SkillValidationError(
                    f"Failed to parse skill metadata in '{meta_file}': {e}"
                ) from e

            # Check for duplicate skill IDs across subdirectories
            if metadata.skill_id in self._skills:
                raise SkillValidationError(
                    f"Duplicate skill_id '{metadata.skill_id}' found in '{subdir.name}' "
                    f"(already defined at '{self._skill_meta_paths[metadata.skill_id]}')."
                )

            # If skill already exists in persistent repository, honor its persisted is_enabled status
            if self.repository and hasattr(self.repository, "get_registered_skill"):
                try:
                    existing = self.repository.get_registered_skill(metadata.skill_id)
                    if existing is not None and "is_enabled" in existing:
                        metadata.is_enabled = bool(existing["is_enabled"])
                except Exception as e:
                    log.debug("Could not read persistent enabled state for '%s': %s", metadata.skill_id, e)

            self._skills[metadata.skill_id] = metadata
            self._skill_docs[metadata.skill_id] = doc_file
            self._skill_meta_paths[metadata.skill_id] = meta_file
            discovered.append(metadata)

            # Synchronize with SQLite repository if configured
            if self.repository and self.auto_sync_repo and hasattr(self.repository, "register_skill"):
                try:
                    self.repository.register_skill(
                        skill_id=metadata.skill_id,
                        name=metadata.name,
                        domain=metadata.category,
                        version=metadata.version,
                        file_path=str(doc_file),
                        description=metadata.description,
                        is_enabled=metadata.is_enabled,
                        metadata={
                            "tags": metadata.tags,
                            "supported_task_types": metadata.supported_task_types,
                            "required_capabilities": metadata.required_capabilities,
                            "dependencies": metadata.dependencies,
                            "min_system_version": metadata.min_system_version,
                        },
                    )
                except Exception as e:
                    log.warning("Failed syncing skill '%s' to sqlite registry: %s", metadata.skill_id, e)

        log.info("Discovered %d domain skills from %s", len(discovered), self.skills_dir)
        return discovered

    def validate_skill(self, skill_id: str) -> SkillValidationResult:
        """Perform full validation of a discovered skill, its files, and dependencies."""
        errors: list[str] = []
        warnings: list[str] = []

        if skill_id not in self._skills:
            return SkillValidationResult(
                is_valid=False,
                skill_id=skill_id,
                errors=[f"Skill ID '{skill_id}' not found among discovered skills."],
            )

        meta = self._skills[skill_id]
        doc_path = self._skill_docs[skill_id]

        if not doc_path.exists():
            errors.append(f"Instruction markdown file missing: {doc_path}")

        # Check dependencies
        for dep in meta.dependencies:
            if dep not in self._skills:
                errors.append(f"Referenced dependency skill '{dep}' does not exist.")
            elif not self._skills[dep].is_enabled:
                warnings.append(f"Required dependency '{dep}' is currently disabled.")

        # Check for circular dependencies
        try:
            self.resolve_dependencies([skill_id])
        except CircularSkillDependencyError as c_err:
            errors.append(str(c_err))
        except Exception as o_err:
            errors.append(str(o_err))

        return SkillValidationResult(
            is_valid=(len(errors) == 0),
            skill_id=skill_id,
            errors=errors,
            warnings=warnings,
            details={"version": meta.version, "category": meta.category},
        )

    # -----------------------------------------------------------------------
    # Metadata & Listing
    # -----------------------------------------------------------------------

    def get_skill_metadata(self, skill_id: str) -> SkillMetadata:
        """Fetch metadata for a discovered skill."""
        if skill_id not in self._skills:
            raise SkillNotFoundError(f"Skill with ID '{skill_id}' not found.")
        return self._skills[skill_id]

    def list_skills(
        self,
        category: str | None = None,
        *,
        enabled_only: bool = True,
    ) -> list[SkillMetadata]:
        """List discovered skills matching criteria, sorted by skill_id."""
        results: list[SkillMetadata] = []
        for s in self._skills.values():
            if enabled_only and not s.is_enabled:
                continue
            if category and s.category.lower() != category.strip().lower():
                continue
            results.append(s)

        return sorted(results, key=lambda x: x.skill_id)

    def enable_skill(self, skill_id: str) -> None:
        """Enable a skill for selection and execution."""
        meta = self.get_skill_metadata(skill_id)
        meta.is_enabled = True
        if self.repository and hasattr(self.repository, "set_skill_enabled"):
            self.repository.set_skill_enabled(skill_id, True)

    def disable_skill(self, skill_id: str) -> None:
        """Disable a skill from being selected or loaded."""
        meta = self.get_skill_metadata(skill_id)
        meta.is_enabled = False
        if self.repository and hasattr(self.repository, "set_skill_enabled"):
            self.repository.set_skill_enabled(skill_id, False)

    # -----------------------------------------------------------------------
    # Dependency Resolution
    # -----------------------------------------------------------------------

    def resolve_dependencies(self, skill_ids: list[str]) -> list[str]:
        """Resolve all prerequisite skills in deterministic topological order using Kahn's algorithm."""
        if not skill_ids:
            return []

        # 1. Collect all transitive dependencies
        collected_ids: set[str] = set()
        to_process = list(skill_ids)

        while to_process:
            curr_id = to_process.pop(0)
            if curr_id in collected_ids:
                continue
            if curr_id not in self._skills:
                raise MissingSkillDependencyError(
                    f"Skill '{curr_id}' not found while resolving dependencies."
                )
            collected_ids.add(curr_id)
            meta = self._skills[curr_id]
            for dep in meta.dependencies:
                if dep not in self._skills:
                    raise MissingSkillDependencyError(
                        f"Skill '{curr_id}' references missing dependency '{dep}'."
                    )
                if dep not in collected_ids:
                    to_process.append(dep)

        # 2. Build DAG
        in_degree: dict[str, int] = {sid: 0 for sid in collected_ids}
        adj: dict[str, list[str]] = {sid: [] for sid in collected_ids}

        for sid in collected_ids:
            meta = self._skills[sid]
            for dep in meta.dependencies:
                if dep in collected_ids:
                    adj[dep].append(sid)
                    in_degree[sid] += 1

        # 3. Kahn's Algorithm with deterministic tie-breaking (sorted queue)
        queue = sorted([sid for sid, deg in in_degree.items() if deg == 0])
        ordered: list[str] = []

        while queue:
            curr = queue.pop(0)
            ordered.append(curr)
            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
            queue.sort()

        if len(ordered) != len(collected_ids):
            unresolved = sorted([sid for sid, deg in in_degree.items() if deg > 0])
            raise CircularSkillDependencyError(
                f"Circular skill dependency detected involving: {unresolved}"
            )

        return ordered

    # -----------------------------------------------------------------------
    # Loading & Token Budget Management
    # -----------------------------------------------------------------------

    def load_skill(self, skill_id: str) -> LoadedSkill:
        """Load markdown instructions for an individual enabled skill."""
        meta = self.get_skill_metadata(skill_id)
        if not meta.is_enabled:
            raise SkillError(f"Cannot load disabled skill '{skill_id}'.")

        doc_path = self._skill_docs[skill_id]
        self._validate_safe_path(doc_path, self.skills_dir)
        self._check_file_size(doc_path)

        content = doc_path.read_text(encoding="utf-8")
        tokens = estimate_tokens(content)

        return LoadedSkill(
            metadata=meta,
            content=content,
            file_path=str(doc_path),
            char_count=len(content),
            estimated_tokens=tokens,
        )

    def load_skills(
        self,
        skill_ids: list[str],
        *,
        max_total_tokens: int | None = None,
    ) -> SkillLoadResult:
        """Selectively load multiple skills respecting dependencies and token budget.

        Never truncates a skill partially: if the entire skill cannot fit in the remaining
        token budget, it is listed in excluded_skills with an explicit note.
        """
        # Resolve full dependency chain in order
        try:
            resolved_order = self.resolve_dependencies(skill_ids)
        except SkillError as e:
            return SkillLoadResult(
                loaded_skills=[],
                excluded_skills=skill_ids,
                total_tokens=0,
                token_budget=max_total_tokens,
                errors=[str(e)],
            )

        loaded: list[LoadedSkill] = []
        loaded_ids: set[str] = set()
        excluded: list[str] = []
        current_tokens = 0
        errors: list[str] = []

        for sid in resolved_order:
            meta = self._skills.get(sid)
            if not meta or not meta.is_enabled:
                excluded.append(sid)
                continue

            # Cascade exclusion: downstream skill cannot be loaded without its prerequisite skills
            unsatisfied = [dep for dep in meta.dependencies if dep not in loaded_ids]
            if unsatisfied:
                log.warning(
                    "Excluding skill '%s' because prerequisite dependencies were not loaded: %s",
                    sid,
                    unsatisfied,
                )
                excluded.append(sid)
                continue

            try:
                skill = self.load_skill(sid)
            except Exception as e:
                excluded.append(sid)
                errors.append(f"Failed loading skill '{sid}': {e}")
                continue

            if max_total_tokens is not None:
                if current_tokens + skill.estimated_tokens > max_total_tokens:
                    log.warning(
                        "Skill '%s' (tokens=%d) exceeds remaining token budget (%d / %d). Excluding.",
                        sid,
                        skill.estimated_tokens,
                        current_tokens,
                        max_total_tokens,
                    )
                    excluded.append(sid)
                    continue

            loaded.append(skill)
            loaded_ids.add(sid)
            current_tokens += skill.estimated_tokens

        return SkillLoadResult(
            loaded_skills=loaded,
            excluded_skills=excluded,
            total_tokens=current_tokens,
            token_budget=max_total_tokens,
            errors=errors,
        )

    # -----------------------------------------------------------------------
    # Deterministic Skill Selection
    # -----------------------------------------------------------------------

    def select_skills(
        self,
        task_type: str | None = None,
        *,
        required_capabilities: list[str] | None = None,
        tags: list[str] | None = None,
        explicit_skill_ids: list[str] | None = None,
    ) -> list[str]:
        """Select relevant skills based on task context and dependencies without LLM calls.

        Deterministic: Matches supported_task_types, capabilities, tags, and expands dependencies.
        """
        candidates: set[str] = set()

        if explicit_skill_ids:
            for sid in explicit_skill_ids:
                if sid in self._skills and self._skills[sid].is_enabled:
                    candidates.add(sid)

        target_type = task_type.strip().lower() if task_type else None
        target_caps = {c.strip().lower() for c in (required_capabilities or [])}
        target_tags = {t.strip().lower() for t in (tags or [])}

        for meta in self._skills.values():
            if not meta.is_enabled:
                continue

            # Match task type
            if target_type and any(tt.lower() == target_type for tt in meta.supported_task_types):
                candidates.add(meta.skill_id)
                continue

            # Match capabilities
            if target_caps and any(c.lower() in target_caps for c in meta.required_capabilities):
                candidates.add(meta.skill_id)
                continue

            # Match tags
            if target_tags and any(t.lower() in target_tags for t in meta.tags):
                candidates.add(meta.skill_id)
                continue

        # Resolve full dependency chain in topological order
        if not candidates:
            return []

        return self.resolve_dependencies(sorted(candidates))

    # -----------------------------------------------------------------------
    # Security Guards
    # -----------------------------------------------------------------------

    def _validate_safe_path(self, target: Path, base: Path) -> None:
        """Enforce path traversal and symlink confinement."""
        try:
            resolved_target = target.resolve()
            resolved_base = base.resolve()
            resolved_target.relative_to(resolved_base)
        except (ValueError, RuntimeError) as e:
            raise SkillSecurityError(
                f"Security violation: path '{target}' escapes root skill boundary '{base}'."
            ) from e

        # Disallow hidden or executable extensions
        forbidden_suffixes = {".py", ".sh", ".bash", ".exe", ".bin", ".bat", ".cmd", ".dll"}
        if target.suffix.lower() in forbidden_suffixes:
            raise SkillSecurityError(
                f"Security violation: forbidden executable file extension in skill directory: '{target}'."
            )

    def _check_file_size(self, file_path: Path) -> None:
        """Enforce maximum file size on untrusted skill files."""
        try:
            size = file_path.stat().st_size
            if size > self.max_file_size_bytes:
                raise ExcessiveSkillSizeError(
                    f"File '{file_path.name}' exceeds maximum permitted size "
                    f"({size} bytes > {self.max_file_size_bytes} bytes)."
                )
        except OSError as e:
            raise SkillError(f"Could not stat file '{file_path}': {e}") from e

