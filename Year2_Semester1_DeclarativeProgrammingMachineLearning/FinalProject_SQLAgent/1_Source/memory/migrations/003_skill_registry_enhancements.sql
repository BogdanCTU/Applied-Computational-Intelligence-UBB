-- Migration 003: Skill Registry Enhancements
-- Adds is_enabled and last_discovered_at to track skill discovery and activation states.

ALTER TABLE skill_registry ADD COLUMN is_enabled INTEGER NOT NULL DEFAULT 1;
ALTER TABLE skill_registry ADD COLUMN last_discovered_at TEXT;

CREATE INDEX IF NOT EXISTS idx_skill_registry_enabled ON skill_registry(is_enabled);

