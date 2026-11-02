"""
ML Label Registry and Definitions for ChronicCare AI.
Provides pure functional label extractors and explicit forbidden feature lists
to prevent target leakage during model training.
"""
from __future__ import annotations

from typing import Callable, NamedTuple
import numpy as np
import pandas as pd


class LabelInfo(NamedTuple):
    name: str
    disease: str
    description: str
    extractor: Callable[[pd.DataFrame], pd.Series]
    forbidden_features: list[str]
    brfss_equivalent: str | None
    trade_off: str


def extract_diabetes_told(df: pd.DataFrame) -> pd.Series:
    s = df.get("told_diabetes", pd.Series(np.nan, index=df.index))
    out = pd.Series(np.nan, index=df.index, dtype=float)
    out[s == 1] = 1.0
    out[s == 0] = 0.0
    return out


def extract_diabetes_measured(df: pd.DataFrame) -> pd.Series:
    h = df.get("hba1c", pd.Series(np.nan, index=df.index))
    g = df.get("fasting_glucose", pd.Series(np.nan, index=df.index))
    out = pd.Series(np.nan, index=df.index, dtype=float)
    has_lab = h.notna() | g.notna()
    out[has_lab] = 0.0
    is_diab = (h >= 6.5) | (g >= 126.0)
    out[is_diab] = 1.0
    return out


def extract_diabetes_told_or_measured(df: pd.DataFrame) -> pd.Series:
    told = extract_diabetes_told(df)
    meas = extract_diabetes_measured(df)
    out = pd.Series(np.nan, index=df.index, dtype=float)
    valid = told.notna() | meas.notna()
    out[valid] = 0.0
    out[(told == 1) | (meas == 1)] = 1.0
    return out


def extract_diabetes_undiagnosed(df: pd.DataFrame) -> pd.Series:
    told = extract_diabetes_told(df)
    meas = extract_diabetes_measured(df)
    out = pd.Series(np.nan, index=df.index, dtype=float)
    evaluable = (told == 0) & meas.notna()
    out[evaluable] = 0.0
    out[(told == 0) & (meas == 1)] = 1.0
    return out


def extract_diabetes_prediabetes(df: pd.DataFrame) -> pd.Series:
    h = df.get("hba1c", pd.Series(np.nan, index=df.index))
    g = df.get("fasting_glucose", pd.Series(np.nan, index=df.index))
    told = extract_diabetes_told(df)
    out = pd.Series(np.nan, index=df.index, dtype=float)
    has_lab = (h.notna() | g.notna()) & told.notna()
    out[has_lab] = 0.0
    is_prediab = ((h >= 5.7) & (h <= 6.4)) | ((g >= 100.0) & (g <= 125.0))
    is_diab = (told == 1) | (h >= 6.5) | (g >= 126.0)
    out[is_prediab & ~is_diab] = 1.0
    out[is_diab] = 0.0
    return out


def extract_hypertension_told(df: pd.DataFrame) -> pd.Series:
    s = df.get("told_high_bp", pd.Series(np.nan, index=df.index))
    out = pd.Series(np.nan, index=df.index, dtype=float)
    out[s == 1] = 1.0
    out[s == 0] = 0.0
    return out


def extract_hypertension_meds(df: pd.DataFrame) -> pd.Series:
    s = df.get("takes_bp_meds", pd.Series(np.nan, index=df.index))
    out = pd.Series(np.nan, index=df.index, dtype=float)
    out[s == 1] = 1.0
    out[s == 0] = 0.0
    return out


def extract_hypertension_told_or_meds(df: pd.DataFrame) -> pd.Series:
    told = extract_hypertension_told(df)
    meds = extract_hypertension_meds(df)
    out = pd.Series(np.nan, index=df.index, dtype=float)
    valid = told.notna() | meds.notna()
    out[valid] = 0.0
    out[(told == 1) | (meds == 1)] = 1.0
    return out


def extract_hypertension_measured_130_80(df: pd.DataFrame) -> pd.Series:
    sbp = df.get("sbp", pd.Series(np.nan, index=df.index))
    dbp = df.get("dbp", pd.Series(np.nan, index=df.index))
    out = pd.Series(np.nan, index=df.index, dtype=float)
    has_bp = sbp.notna() & dbp.notna()
    out[has_bp] = 0.0
    out[has_bp & ((sbp >= 130.0) | (dbp >= 80.0))] = 1.0
    return out


def extract_hypertension_measured_140_90(df: pd.DataFrame) -> pd.Series:
    sbp = df.get("sbp", pd.Series(np.nan, index=df.index))
    dbp = df.get("dbp", pd.Series(np.nan, index=df.index))
    out = pd.Series(np.nan, index=df.index, dtype=float)
    has_bp = sbp.notna() & dbp.notna()
    out[has_bp] = 0.0
    out[has_bp & ((sbp >= 140.0) | (dbp >= 90.0))] = 1.0
    return out


def extract_hypertension_stage1_or_clinical(df: pd.DataFrame) -> pd.Series:
    told = extract_hypertension_told(df)
    meds = extract_hypertension_meds(df)
    meas = extract_hypertension_measured_130_80(df)
    out = pd.Series(np.nan, index=df.index, dtype=float)
    valid = told.notna() | meds.notna() | meas.notna()
    out[valid] = 0.0
    out[(told == 1) | (meds == 1) | (meas == 1)] = 1.0
    return out


LABELS: dict[str, LabelInfo] = {
    "diabetes_told": LabelInfo(
        name="diabetes_told",
        disease="diabetes",
        description="Doctor told participant they have diabetes (self-report)",
        extractor=extract_diabetes_told,
        forbidden_features=["told_diabetes", "takes_insulin", "takes_diabetes_pills", "diagnosis_year_diabetes"],
        brfss_equivalent="diabetes",
        trade_off="Simple and matches survey data, but misses ~25% of undiagnosed individuals with elevated blood sugar.",
    ),
    "diabetes_measured": LabelInfo(
        name="diabetes_measured",
        disease="diabetes",
        description="Biochemically measured diabetes (HbA1c >= 6.5% or fasting glucose >= 126 mg/dL)",
        extractor=extract_diabetes_measured,
        forbidden_features=["hba1c", "fasting_glucose", "glucose"],
        brfss_equivalent=None,
        trade_off="Biochemically objective gold standard, but limited to participants with laboratory examination samples.",
    ),
    "diabetes_told_or_measured": LabelInfo(
        name="diabetes_told_or_measured",
        disease="diabetes",
        description="Either told by a doctor OR biochemically measured (HbA1c >= 6.5 or glucose >= 126)",
        extractor=extract_diabetes_told_or_measured,
        forbidden_features=["told_diabetes", "takes_insulin", "takes_diabetes_pills", "diagnosis_year_diabetes", "hba1c", "fasting_glucose", "glucose"],
        brfss_equivalent=None,
        trade_off="Most complete epidemiological definition of total diabetes burden; slightly noisier due to self-report inclusion.",
    ),
    "diabetes_undiagnosed": LabelInfo(
        name="diabetes_undiagnosed",
        disease="diabetes",
        description="Biochemically diabetic (HbA1c >= 6.5 or glucose >= 126) but NEVER told by doctor",
        extractor=extract_diabetes_undiagnosed,
        forbidden_features=["told_diabetes", "hba1c", "fasting_glucose", "glucose", "takes_insulin", "takes_diabetes_pills"],
        brfss_equivalent=None,
        trade_off="Highest clinical utility for screening app; smaller positive sample size (~3-4% prevalence) requires careful calibration.",
    ),
    "diabetes_prediabetes": LabelInfo(
        name="diabetes_prediabetes",
        disease="diabetes",
        description="Biochemical prediabetes (HbA1c 5.7-6.4% or fasting glucose 100-125 mg/dL) and non-diabetic",
        extractor=extract_diabetes_prediabetes,
        forbidden_features=["hba1c", "fasting_glucose", "glucose", "told_diabetes", "borderline_diabetes"],
        brfss_equivalent="prediabetes",
        trade_off="Captures early preventive intervention window; high prevalence (~25-35%) with modest clinical distinctiveness.",
    ),
    "hypertension_told": LabelInfo(
        name="hypertension_told",
        disease="hypertension",
        description="Doctor told participant they have high blood pressure (self-report)",
        extractor=extract_hypertension_told,
        forbidden_features=["told_high_bp", "takes_bp_meds", "diagnosis_year_hypertension"],
        brfss_equivalent="high_bp",
        trade_off="Broad coverage across all surveys, but vulnerable to patient recall bias and untreated unawareness.",
    ),
    "hypertension_on_meds": LabelInfo(
        name="hypertension_on_meds",
        disease="hypertension",
        description="Currently taking prescribed antihypertensive medication",
        extractor=extract_hypertension_meds,
        forbidden_features=["takes_bp_meds", "told_high_bp", "medications", "diagnosis_year_hypertension"],
        brfss_equivalent="bp_meds",
        trade_off="Direct indicator of pharmacologically managed disease; only asked of participants who reported high BP.",
    ),
    "hypertension_told_or_meds": LabelInfo(
        name="hypertension_told_or_meds",
        disease="hypertension",
        description="Either told by a doctor OR currently on antihypertensive medications",
        extractor=extract_hypertension_told_or_meds,
        forbidden_features=["told_high_bp", "takes_bp_meds", "diagnosis_year_hypertension", "medications"],
        brfss_equivalent="high_bp",
        trade_off="Robust self-report standard that minimizes under-counting treated individuals whose BP is normalized.",
    ),
    "hypertension_measured_130_80": LabelInfo(
        name="hypertension_measured_130_80",
        disease="hypertension",
        description="Measured systolic BP >= 130 mmHg OR diastolic BP >= 80 mmHg (2017/2025 AHA/ACC Stage 1+)",
        extractor=extract_hypertension_measured_130_80,
        forbidden_features=["sbp", "dbp", "blood_pressure_systolic", "blood_pressure_diastolic"],
        brfss_equivalent=None,
        trade_off="Current clinical guideline definition; sensitive to white-coat effect or transient elevated readings.",
    ),
    "hypertension_measured_140_90": LabelInfo(
        name="hypertension_measured_140_90",
        disease="hypertension",
        description="Measured systolic BP >= 140 mmHg OR diastolic BP >= 90 mmHg (Classic JNC7 / Stage 2)",
        extractor=extract_hypertension_measured_140_90,
        forbidden_features=["sbp", "dbp", "blood_pressure_systolic", "blood_pressure_diastolic"],
        brfss_equivalent=None,
        trade_off="Historical standard for stage 2 hypertension; higher specificity for organ risk but misses early stage 1 elevation.",
    ),
    "hypertension_stage1_or_clinical": LabelInfo(
        name="hypertension_stage1_or_clinical",
        disease="hypertension",
        description="Clinical hypertension: Told OR on meds OR measured BP >= 130/80 mmHg",
        extractor=extract_hypertension_stage1_or_clinical,
        forbidden_features=["told_high_bp", "takes_bp_meds", "sbp", "dbp", "blood_pressure_systolic", "blood_pressure_diastolic", "medications", "diagnosis_year_hypertension"],
        brfss_equivalent=None,
        trade_off="Most comprehensive real-world label combining clinical history, pharmacotherapy, and actual cuff measurements.",
    ),
}
