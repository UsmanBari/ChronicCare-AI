"""
Unit tests for DHS dataset loader skeleton and variables audit.
"""
from pathlib import Path

import pytest
from ml.datasets.dhs import (
    EXPECTED_VARIABLES,
    SUPPORTED_COUNTRIES,
    DhsDataNotAvailable,
    load_dhs,
)


def test_dhs_data_not_available_on_missing_file(tmp_path: Path):
    """Verify that load_dhs raises DhsDataNotAvailable when data files are missing."""
    # Test with explicit non-existent path
    with pytest.raises(DhsDataNotAvailable) as exc_info:
        load_dhs("india_nfhs5", path=tmp_path / "missing_nfhs5.dta")
    assert "not found" in str(exc_info.value).lower()
    assert issubclass(DhsDataNotAvailable, FileNotFoundError)

    # Test with default path (handles both unset and set CHRONICCARE_DATA_DIR)
    with pytest.raises(DhsDataNotAvailable) as exc_info_def:
        load_dhs("india_nfhs5")
    assert "not found" in str(exc_info_def.value).lower()


def test_dhs_unsupported_country():
    """Verify that load_dhs rejects unsupported country names."""
    with pytest.raises(ValueError) as exc_info:
        load_dhs("pakistan_2024")
    assert "unsupported" in str(exc_info.value).lower()


def test_dhs_all_supported_countries_raise_when_absent():
    """Verify that each supported country raises DhsDataNotAvailable when file absent."""
    for country in SUPPORTED_COUNTRIES:
        with pytest.raises(DhsDataNotAvailable):
            load_dhs(country)


def test_dhs_expected_variables_all_marked_to_confirm():
    """
    CRITICAL AUDIT:
    Every expected variable code must be explicitly marked 'TO CONFIRM'
    per project clinical and regulatory integrity guidelines.
    """
    required_concepts = [
        "sbp1",
        "sbp2",
        "sbp3",
        "dbp1",
        "dbp2",
        "dbp3",
        "random_glucose",
        "fasting_glucose",
        "age",
        "sex",
        "height",
        "weight",
        "current_bp_medication",
    ]

    for concept in required_concepts:
        assert concept in EXPECTED_VARIABLES, f"Missing required biomarker concept: {concept}"
        info = EXPECTED_VARIABLES[concept]
        assert "TO CONFIRM" in info["code"], f"Variable code for {concept} not marked 'TO CONFIRM': {info['code']}"
        assert len(info["description"]) > 5

