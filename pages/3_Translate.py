import streamlit as st
import pandas as pd
import os
import re
from openai import OpenAI

st.set_page_config(page_title="Translate", layout="wide")
st.header("3) Translate (plain text) — OpenAI + glossary + review (2-pass)")

# --------------------
# Helpers
# --------------------

def load_glossary(lang_code: str) -> pd.DataFrame:
    path = os.path.join("data", f"glossary_{lang_code}.csv")
    if os.path.exists(path):
        df = pd.read_csv(path)
        for col in ["term_pl", "term_target", "locked", "notes"]:
            if col not in df.columns:
                df[col] = "" if col != "locked" else False
        # locked may be True/False or 1/0
        df["locked"] = df["locked"].apply(lambda x: str(x).strip().lower() in ["true", "1", "yes", "y", "t"])
        df["term_pl"] = df["term_pl"].astype(str).str.strip()
        df["term_target"] = df["term_target"].astype(str).str.strip()
        df["notes"] = df["notes"].astype(str)
        return df[["term_pl", "term_target", "locked", "notes"]]
    return pd.DataFrame(columns=["term_pl", "term_target", "locked", "notes"])


def glossary_to_text(df: pd.DataFrame) -> str:
    lines = []
    for _, r in df.iterrows():
        pl = str(r["term_pl"]).strip()
        tgt = str(r["term_target"]).strip()
        if pl and tgt:
            lines.append(f"- {pl} => {tgt}")
    return "\n".join(lines)


def check_locked_terms(source_pl: str, translated: str, df: pd.DataFrame):
    """MVP check: exact substring match for term_target (may false-positive on inflection; we'll improve later)."""
    src = (source_pl or "").lower()
    tgt = (translated or "").lower()
    missing = []

    locked_df = df[df["locked"] == True]
    for _, r in locked_df.iterrows():
        pl = str(r["term_pl"]).strip()
        tt = str(r["term_target"]).strip()
        if pl and tt and pl.lower() in src and tt.lower() not in tgt:
            missing.append({"term_pl": pl, "term_target": tt})
    return missing


def extract_numbers(text: str):
    """
    Extract numbers + possible units for quick consistency checks.
    Example matches: '60', '60 cm', '1,5', '1.5', '1200W', '12 V', '10%'
    """
    if not text:
        return []
    pattern = re.compile(r"(?<!\w)(\d+(?:[.,]\d+)?)\s*([%a-zA-Z°]+)?", re.UNICODE)
    out = []
    for m in pattern.finditer(text):
        num = m.group(1)
        unit = (m.group(2) or "").strip()
        out.append(f"{num}{(' ' + unit) if unit else ''}".strip())
    # keep order but dedupe
