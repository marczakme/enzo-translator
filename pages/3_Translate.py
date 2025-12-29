import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime
from openai import OpenAI

# ======================================================
# Page setup
# ======================================================
st.set_page_config(page_title="Translate", layout="wide")
st.header("3) Translate — Name + Body + Review + Archiwum (TXT)")

# ======================================================
# Helpers
# ======================================================

def safe_slug(text: str, max_len: int = 60) -> str:
    """Create filesystem-safe slug."""
    text = (text or "").strip().lower()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^a-z0-9\-ąćęłńóśźżäöüßàáâãåçèéêëìíîïòóôõùúûñýÿčďěňřšťžğışİ]+", "-", text, flags=re.IGNORECASE)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    if not text:
        text = "translation"
    return text[:max_len]

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
    df["locked"] = df["locked"].apply(lambda x: str(x).strip().lower() in ["true", "1", "yes", "y", "t"])

    return df[["term_pl", "term_target", "locked", "notes"]]

def glossary_to_text(df: pd.DataFrame) -> str:
    rows = []
    for _, r in df.iterrows():
        if r["term_pl"] and r["term_target"]:
            rows.append(f"- {r['term_pl']} => {r['term_target']}")
    return "\n".join(rows)

def check_locked_terms(source: str, target: str, df: pd.DataFrame):
    missing = []
    src = (source or "").lower()
    tgt = (target or "").lower()
    for _, r in df[df["locked"] == True].iterrows():
        pl = (r["term_pl"] or "").strip()
        tt = (r["term_target"] or "").strip()
        if pl and tt and pl.lower() in src and tt.lower() not in tgt:
            missing.append({"term_pl": pl, "term_target": tt})
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
    # preserve order, dedupe
    return list(dict.fromkeys(results))

def diff_numbers(src, tgt):
    tgt_norm = {x.replace(",", ".") for x in tgt}
    missing = []
    for s in src:
        if s.replace(",", ".") not in tgt_norm:
            missing.append(s)
    return missing

def ensure_dirs(lang_code: str):
    base = os.path.join("data", "translations", lang_code)
    os.makedirs(base, exist_ok=True)
    return base

def index_path(lang_code: str):
    return os.path.join("data", "translations", f"index_{lang_code}.csv")

def append_index(lang_code: str, row: dict):
    ip = index_path(lang_code)
    os.makedirs(os.path.dirname(ip), exist_ok=True)

    if os.path.exists(ip):
        df = pd.read_csv(ip)
    else:
        df = pd.DataFrame(columns=["datetime", "title_pl", "filename"])

    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(ip, index=False)

def build_txt_payload(dt_str, title_pl, body_pl, title_tgt, body_tgt, review_report, label):
    return "\n".join([
        f"DATE: {dt_str}",
        f"LANGUAGE/MARKET: {label}",
        "",
        "=== SOURCE (PL) ===",
        f"NAME: {title_pl}",
        "",
        "BODY:",
        body_pl,
        "",
        "=== TRANSLATION ===",
        f"NAME: {title_tgt}",
        "",
        "BODY:",
        body_tgt,
        "",
        "=== REVIEW REPORT ===",
        review_report or "(no review report)",
        ""
    ])

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
# UI inputs (NAME + BODY)
# ======================================================

title_pl = st.text_input("Nazwa (PL)", placeholder="np. Fotel fryzjerski Enzo X1")
body_pl = st.text_area("Dalsza treść (PL)", height=220, placeholder="Wklej opis produktu po polsku…")

glossary_df = load_glossary(lang)
glossary_text = glossary_to_text(glossary_df)

with st.expander("Glossary dla tego języka"):
    st.dataframe(glossary_df, use_container_width=True)

temperature = st.slider("Temperature", 0.0, 0.8, 0.2, 0.05)

st.caption("Kliknij Translate — system zrobi tłumaczenie + review, a następnie zapisze TXT do archiwum dla tego języka.")

# ======================================================
# Translate + Review (2-pass)
# ======================================================

if st.button("Translate (auto-review + save TXT)", type="primary"):
    if not (title_pl or body_pl).strip():
        st.warning("Uzupełnij przynajmniej nazwę lub treść.")
        st.stop()

    # PASS 1: Translation
    system_translate = (
        "You are a senior professional translator and localization expert. "
        "Translate precisely for native speakers in the given market/industry. "
        "Use natural, expert tone (not marketing fluff). "
        "Do not add explanations."
    )

    user_translate = (
        f"Source language: Polish\n"
        f"Target market/language: {label}\n\n"
        "Industry / style context:\n"
        f"{style_hint}\n\n"
        "Mandatory terminology (use mapped terms, inflect naturally if needed):\n"
        f"{glossary_text if glossary_text else 'None'}\n\n"
        "Rules:\n"
        "- Preserve all numbers, units, parameters\n"
        "- Do not shorten content\n"
        "- Output plain text only\n\n"
        "Translate the following two fields and keep them separate.\n"
        "Return format EXACTLY:\n"
        "NAME:\n"
        "<translated name>\n"
        "BODY:\n"
        "<translated body>\n\n"
        "SOURCE:\n"
        f"NAME:\n{title_pl}\n"
        f"BODY:\n{body_pl}"
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

    translated_full = resp1.choices[0].message.content.strip()

    # Parse NAME/BODY
    def parse_named_fields(text: str):
        name = ""
        body = ""
        m_name = re.search(r"NAME:\s*\n(.+?)(?=\nBODY:\s*\n)", text, re.DOTALL | re.IGNORECASE)
        m_body = re.search(r"BODY:\s*\n(.+)$", text, re.DOTALL | re.IGNORECASE)
        if m_name:
            name = m_name.group(1).strip()
        if m_body:
            body = m_body.group(1).strip()
        # fallback: if parsing failed, put all into body
        if not name and not body:
            body = text.strip()
        return name, body

    title_tgt, body_tgt = parse_named_fields(translated_full)

    st.session_state.title_tgt = title_tgt
    st.session_state.body_tgt = body_tgt

    # PASS 2: Review
    system_review = (
        "You are a senior linguist reviewer. "
        "Review translation quality, factual fidelity and terminology consistency. "
        "Be strict. Do NOT rewrite the full translation; list issues and suggested fixes."
    )

    user_review = (
        f"Market/language: {label}\n\n"
        "Mandatory terminology:\n"
        f"{glossary_text if glossary_text else 'None'}\n\n"
        "Return your response in this exact format:\n"
        "VERDICT: OK / FIX\n"
        "ISSUES: bullet list (max 8)\n"
        "SUGGESTED FIXES: bullet list (max 8)\n"
        "CONFIDENCE: 0-100\n\n"
        "SOURCE (PL):\n"
        f"NAME:\n{title_pl}\n\n"
        f"BODY:\n{body_pl}\n\n"
        "TRANSLATION:\n"
        f"NAME:\n{title_tgt}\n\n"
        f"BODY:\n{body_tgt}\n"
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

    # Local QA (locked + numbers) on combined text
    src_combined = f"{title_pl}\n\n{body_pl}"
    tgt_combined = f"{title_tgt}\n\n{body_tgt}"

    st.session_state.locked_missing = check_locked_terms(src_combined, tgt_combined, glossary_df)
    st.session_state.missing_numbers = diff_numbers(extract_numbers(src_combined), extract_numbers(tgt_combined))

    # SAVE TXT
    dt = datetime.now()
    dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
    ts = dt.strftime("%Y%m%d_%H%M%S")
    base_dir = ensure_dirs(lang)

    slug = safe_slug(title_pl if title_pl.strip() else "translation")
    filename = f"{ts}_{slug}.txt"
    file_path = os.path.join(base_dir, filename)

    payload = build_txt_payload(dt_str, title_pl, body_pl, title_tgt, body_tgt, review_report, label)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(payload)

    append_index(lang, {"datetime": dt_str, "title_pl": title_pl.strip(), "filename": filename})

    st.success(f"Zapisano do archiwum: data/translations/{lang}/{filename}")

# ======================================================
# OUTPUT
# ======================================================

title_tgt = st.session_state.get("title_tgt", "")
body_tgt = st.session_state.get("body_tgt", "")
review_report = st.session_state.get("review_report", "")
verdict = st.session_state.get("review_verdict", "")
locked_missing = st.session_state.get("locked_missing", [])
missing_numbers = st.session_state.get("missing_numbers", [])

if title_tgt or body_tgt:
    st.subheader("Wynik tłumaczenia")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**NAME (tłumaczenie)**")
        st.text_area("", title_tgt, height=90)
    with c2:
        st.markdown("**BODY (tłumaczenie)**")
        st.text_area("", body_tgt, height=240)

    st.subheader("QA — automatyczne alerty")

    if locked_missing:
        st.error("Terminologia (locked): braki")
        st.dataframe(pd.DataFrame(locked_missing), use_container_width=True)
    else:
        st.success("Terminologia (locked): OK ✅")

    if missing_numbers:
        st.error("Liczby/jednostki: część wartości z PL nie występuje w tłumaczeniu (sprawdź ręcznie):")
        st.write(", ".join(missing_numbers[:120]))
    else:
        st.success("Liczby/jednostki: OK ✅")

    st.subheader("Review (pełna treść)")
    if verdict == "OK":
        st.success("VERDICT: OK ✅")
    elif verdict == "FIX":
        st.warning("VERDICT: FIX ⚠️")
    else:
        st.info("VERDICT: (brak)")

    st.code(review_report or "(brak raportu)", language="text")
else:
    st.info("Uzupełnij nazwę i/lub treść, potem kliknij Translate (auto-review + save TXT).")
