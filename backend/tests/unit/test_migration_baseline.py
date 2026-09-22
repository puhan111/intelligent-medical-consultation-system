import importlib

import pytest


migration = importlib.import_module(
    "migrations.versions.7d2a61f4c9be_initial_schema"
)


def test_frozen_migration_columns_match_current_baseline():
    tables = migration._baseline_metadata_tables()

    assert {table.name for table in tables} == migration.BASELINE_TABLES


def test_model_column_change_requires_a_new_revision(monkeypatch):
    changed = dict(migration.BASELINE_COLUMNS)
    changed["reports"] = changed["reports"] + ("unmigrated_column",)
    monkeypatch.setattr(migration, "BASELINE_COLUMNS", changed)

    with pytest.raises(RuntimeError, match=r"changed_tables=\['reports'\]"):
        migration._baseline_metadata_tables()
