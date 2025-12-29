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
    seen = set()
    uniq = []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def diff_numbers(src_nums, tgt_nums):
    """Return nums present in source but not in target."""
    tgt_set = set([x.replace(",", ".") for x in tgt_nums])
    missing = []
    for s in src_nums:
        s_norm = s.replace(",", ".")
        if s_norm not in tgt_set:
            missing.append(s)
    return missing


# --------------------
# Configuration
# --------------------

lang = st.session_state.get("target_language")
label = st.session_state.get("target_market_label")
style_hint = st.session_state.get("style_hint", "")

if not lang or not label:
    st.warning("Najpierw wybierz język/rynek w Configuration.")
    st.stop()

st.subheader(f"Rynek: {label}")

# --------------------
# OpenAI
# --------------------

if "openai" not in st.secrets or "api_key" not in st.secrets["openai"]:
    st.error("Brak OpenAI API key w Secrets.")
    st.stop()

client = OpenAI(api_key=st.secrets["openai"]["api_key"])
model = st.secrets["openai"].get("model", "gpt-4.1-mini")

# --------------------
# UI
# --------------------

if "translated_text" not in st.session_state:
    st.session_state.translated_text = ""
if "review_report" not in st.session_state:
    st.session_state.review_report = ""
if "review_verdict" not in st.session_state:
    st.session_state.review_verdict = ""
if "review_suggestions" not in st.session_state:
    st.session_state.review_suggestions = ""

source_text = st.text_area(
    "Tekst po polsku (plain text)",
    height=220,
    placeholder="Wklej tekst po polsku…"
)

glossary_df = load_glossary(lang)
glossary_text = glossary_to_text(glossary_df)

with st.expander("Glossary dla tego języka"):
    st.dataframe(glossary_df, use_container_width=True)

temperature = st.slider("Temperature (niżej = bardziej konsekwentnie)", 0.0, 0.8, 0.2, 0.05)

st.caption("Kliknij Translate — aplikacja zrobi tłumaczenie oraz automatyczny Review (2-pass).")

# --------------------
# Translate + Review (2-pass)
# --------------------

if st.button("Translate (auto-review)", type="primary"):
    if not source_text.strip():
        st.warning("Wklej tekst do tłumaczenia.")
        st.stop()

    # PASS 1: Translation
    system_translate = (
        "You are a senior professional translator and localization expert. "
        "Translate precisely for native speakers in the given market/industry. "
        "Use a natural, expert tone (not marketing fluff). "
        "Do not add explanations."
    )

    user_translate = (
        "Source language: Polish\n"
        f"Target language / market: {label}\n\n"
        "Industry / style context:\n"
        f"{style_hint}\n\n"
        "Mandatory terminology (Polish => Target).\n"
        "If the Polish term appears, you MUST use the mapped target term (inflect naturally if needed):\n"
        f"{glossary_text if glossary_text else 'None'}\n\n"
        "Rules:\n"
        "- Do not translate numbers, units, product codes\n"
        "- Do not shorten content\n"
        "- Output plain text only\n\n"
        "Text to translate:\n"
        f"{source_text}"
    )

    with st.spinner("Pass 1/2: tłumaczenie…"):
        resp1 = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_translate},
                {"role": "user", "content": user_translate},
            ],
        )

    translated = resp1.choices[0].message.content.strip()
    st.session_state.translated_text = translated

    # PASS 2: Review / QA (LLM)
    # We'll ask for a structured, short report + verdict + suggestions.
    system_review = (
        "You are a senior linguist reviewer. "
        "Review the translation quality and terminology consistency. "
        "Be strict about factual fidelity. "
        "Do NOT rewrite the full translation unless asked; provide issues and suggestions."
    )

    user_review = (
        f"Market/language: {label}\n"
        "Task: review the translation.\n\n"
        "Mandatory terminology (Polish => Target) that must be respected:\n"
        f"{glossary_text if glossary_text else 'None'}\n\n"
        "Return your response in this exact format:\n"
        "VERDICT: OK / FIX\n"
        "ISSUES: bullet list (max 8)\n"
        "SUGGESTED FIXES: bullet list (max 8)\n"
        "CONFIDENCE: 0-100\n\n"
        "SOURCE (Polish):\n"
        f"{source_text}\n\n"
        "TRANSLATION:\n"
        f"{translated}"
    )

    with st.spinner("Pass 2/2: review językowy…"):
        resp2 = client.chat.completions.create(
            model=model,
            temperature=0.1,
            messages=[
                {"role": "system", "content": system_review},
                {"role": "user", "content": user_review},
            ],
        )

    review_text = resp2.choices[0].message.content.strip()
    st.session_state.review_report = review_text

    # Try to extract verdict
    verdict_match = re.search(r"VERDICT:\s*(OK|FIX)", review_text, re.IGNORECASE)
    verdict = verdict_match.group(1).upper() if verdict_match else ""
    st.session_state.review_verdict = verdict

    # Local (non-LLM) red flags: locked terms + numbers consistency
    locked_missing = check_locked_terms(source_text, translated, glossary_df)

    src_nums = extract_numbers(source_text)
    tgt_nums = extract_numbers(translated)
    missing_nums = diff_numbers(src_nums, tgt_nums)

    st.session_state.review_suggestions = ""  # placeholder for future auto-fix step

    # Store red flags in session for display
    st.session_state._locked_missing = locked_missing
    st.session_state._missing_nums = missing_nums

# --------------------
# Output
# --------------------

translated_text = st.session_state.get("translated_text", "")

st.text_area(
    "Wynik tłumaczenia",
    value=translated_text,
    height=260
)

# --------------------
# QA display
# --------------------
if translated_text:
    st.subheader("QA — automatyczne alerty (red flags)")

    locked_missing = st.session_state.get("_locked_missing", [])
    missing_nums = st.session_state.get("_missing_nums", [])

    if locked_missing:
        st.error(f"Terminologia (locked): brakuje {len(locked_missing)} wymuszonych terminów.")
        st.dataframe(pd.DataFrame(locked_missing), use_container_width=True)
    else:
        st.success("Terminologia (locked): OK ✅")

    if missing_nums:
        st.error("Liczby/jednostki: część wartości z PL nie występuje w tłumaczeniu (sprawdź ręcznie):")
        st.write(", ".join(missing_nums[:80]))
    else:
        st.success("Liczby/jednostki: OK ✅")

    st.subheader("Review (LLM)")
    verdict = st.session_state.get("review_verdict", "")
    if verdict == "OK":
        st.success("VERDICT: OK ✅ (możesz publikować, jeśli red flags są OK)")
    elif verdict == "FIX":
        st.warning("VERDICT: FIX ⚠️ (zalecane poprawki przed publikacją)")
    else:
        st.info("VERDICT: (nie wykryto w raporcie — zajrzyj do treści review)")

    st.text_area("Raport Review", value=st.session_state.get("review_report", ""), height=240)
else:
    st.info("Wklej tekst i kliknij Translate (auto-review).")
