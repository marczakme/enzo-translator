import streamlit as st
import pandas as pd
import os
import re
from openai import OpenAI

# ======================================================
# Page setup
# ======================================================
st.set_page_config(page_title="Translate", layout="wide")
st.header("3) Translate — Translate + Review (2-pass)")

# ======================================================
# Helpers
# ======================================================

def load_glossary(lang_code: str) -> pd.DataFrame:
    path = os.path.join("data", f"glossary_{lang_code}.csv")
    if not os.path.exists(path):
        return pd.DataFrame(columns=["term_pl", "term_target", "locked", "notes"])

    df = pd.read_csv(path)

    for col in ["term_pl", "term_target", "locked", "notes"]:
        if col not in df.columns:
            df[col] = "" if col != "locked" else False

    df["term_pl"] = df["term_pl"].astype(str).str.strip()
    df["term_target"] = df["term_target"].astype(str).str.strip()
    df["notes"] = df["notes"].astype(str)
    df["locked"] = df["locked"].apply(
        lambda x: str(x).strip().lower() in ["true", "1", "yes", "y", "t"]
    )

    return df[["term_pl", "term_target", "locked", "notes"]]


def glossary_to_text(df: pd.DataFrame) -> str:
    rows = []
    for _, r in df.iterrows():
        if r["term_pl"] and r["term_target"]:
            rows.append(f"- {r['term_pl']} => {r['term_target']}")
    return "\n".join(rows)


def check_locked_terms(source: str, target: str, df: pd.DataFrame):
    missing = []
    src = source.lower()
    tgt = target.lower()

    for _, r in df[df["locked"] == True].iterrows():
        pl = r["term_pl"].lower()
        tt = r["term_target"].lower()
        if pl in src and tt not in tgt:
            missing.append({
                "term_pl": r["term_pl"],
                "term_target": r["term_target"]
            })
    return missing


def extract_numbers(text: str):
    if not text:
        return []
    pattern = re.compile(r"(\d+(?:[.,]\d+)?)\s*([a-zA-Z%°]+)?")
    results = []
    for m in pattern.finditer(text):
        num = m.group(1)
        unit = m.group(2) or ""
        results.append(f"{num}{unit}")
    return list(dict.fromkeys(results))


def diff_numbers(src, tgt):
    tgt_norm = {x.replace(",", ".") for x in tgt}
    missing = []
    for s in src:
        if s.replace(",", ".") not in tgt_norm:
            missing.append(s)
    return missing


# ======================================================
# Configuration
# ======================================================

lang = st.session_state.get("target_language")
label = st.session_state.get("target_market_label")
style_hint = st.session_state.get("style_hint", "")

if not lang or not label:
    st.warning("Najpierw wybierz język/rynek w Configuration.")
    st.stop()

st.subheader(f"Rynek docelowy: {label}")

# ======================================================
# OpenAI
# ======================================================

if "openai" not in st.secrets or "api_key" not in st.secrets["openai"]:
    st.error("Brak OpenAI API key w Secrets.")
    st.stop()

client = OpenAI(api_key=st.secrets["openai"]["api_key"])
model = st.secrets["openai"].get("model", "gpt-4.1-mini")

# ======================================================
# UI
# ======================================================

source_text = st.text_area(
    "Tekst po polsku (plain text)",
    height=220,
    placeholder="Wklej opis produktu po polsku…"
)

glossary_df = load_glossary(lang)
glossary_text = glossary_to_text(glossary_df)

with st.expander("Glossary dla tego języka"):
    st.dataframe(glossary_df, use_container_width=True)

temperature = st.slider(
    "Temperature (niżej = większa konsekwencja terminologiczna)",
    0.0, 0.8, 0.2, 0.05
)

st.caption("Kliknij Translate — system automatycznie wykona tłumaczenie i review językowe.")

# ======================================================
# Translate + Review
# ======================================================

if st.button("Translate (auto-review)", type="primary"):

    if not source_text.strip():
        st.warning("Wklej tekst do tłumaczenia.")
        st.stop()

    # ---------- PASS 1: TRANSLATION ----------
    system_translate = (
        "You are a senior professional translator and localization expert. "
        "Translate precisely for native speakers in the given market. "
        "Use correct grammar and natural professional tone. "
        "Do NOT add explanations."
    )

    user_translate = (
        f"Source language: Polish\n"
        f"Target market/language: {label}\n\n"
        "Mandatory terminology (use mapped terms, inflect naturally if needed):\n"
        f"{glossary_text if glossary_text else 'None'}\n\n"
        "Rules:\n"
        "- Preserve all numbers, units, parameters\n"
        "- Do not shorten content\n"
        "- Output plain text only\n\n"
        "Text:\n"
        f"{source_text}"
    )

    with st.spinner("Pass 1/2 — tłumaczenie…"):
        resp1 = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_translate},
                {"role": "user", "content": user_translate},
            ],
        )

    translated = resp1.choices[0].message.content.strip()
    st.session_state.translated = translated

    # ---------- PASS 2: REVIEW ----------
    system_review = (
        "You are a senior linguist reviewer. "
        "Check accuracy, terminology consistency and naturalness. "
        "Do not rewrite the full text unless necessary."
    )

    user_review = (
        f"Market: {label}\n\n"
        "Mandatory terminology:\n"
        f"{glossary_text if glossary_text else 'None'}\n\n"
        "Return format EXACTLY:\n"
        "VERDICT: OK / FIX\n"
        "ISSUES:\n"
        "- ...\n"
        "SUGGESTED FIXES:\n"
        "- ...\n"
        "CONFIDENCE: 0-100\n\n"
        "SOURCE (PL):\n"
        f"{source_text}\n\n"
        "TRANSLATION:\n"
        f"{translated}"
    )

    with st.spinner("Pass 2/2 — review językowe…"):
        resp2 = client.chat.completions.create(
            model=model,
            temperature=0.1,
            messages=[
                {"role": "system", "content": system_review},
                {"role": "user", "content": user_review},
            ],
        )

    review_report = resp2.choices[0].message.content.strip()
    st.session_state.review_report = review_report

    verdict_match = re.search(r"VERDICT:\s*(OK|FIX)", review_report, re.IGNORECASE)
    st.session_state.review_verdict = verdict_match.group(1).upper() if verdict_match else ""

    # ---------- LOCAL QA ----------
    st.session_state.locked_missing = check_locked_terms(
        source_text, translated, glossary_df
    )
    st.session_state.missing_numbers = diff_numbers(
        extract_numbers(source_text),
        extract_numbers(translated)
    )

# ======================================================
# OUTPUT
# ======================================================

if "translated" in st.session_state:

    st.subheader("Wynik tłumaczenia")
    st.text_area("", st.session_state.translated, height=260)

    st.subheader("QA — automatyczne alerty")

    if st.session_state.locked_missing:
        st.error("Brakuje wymuszonych terminów (locked):")
        st.dataframe(pd.DataFrame(st.session_state.locked_missing), use_container_width=True)
    else:
        st.success("Terminologia (locked): OK")

    if st.session_state.missing_numbers:
        st.error("Niektóre liczby/jednostki z PL nie występują w tłumaczeniu:")
        st.write(", ".join(st.session_state.missing_numbers))
    else:
        st.success("Liczby i jednostki: OK")

    st.subheader("Review językowe (pełna treść)")
    st.code(st.session_state.review_report, language="text")

    verdict = st.session_state.review_verdict
    if verdict == "OK":
        st.success("VERDICT: OK — tekst gotowy do publikacji")
    elif verdict == "FIX":
        st.warning("VERDICT: FIX — zalecane poprawki przed publikacją")
