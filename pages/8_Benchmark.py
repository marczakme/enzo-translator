import streamlit as st
import pandas as pd
import os
import re
from llm_providers import chat_llm

st.set_page_config(page_title="Benchmark", layout="wide")
st.header("🧪 8) Benchmark — porównanie modeli tłumaczeń")

st.markdown(
    """
Ten tryb pozwala porównać jakość tłumaczeń wykonanych przez różne modele (OpenAI / Claude / Gemini)
dla tego samego tekstu, przy jednym, stałym reviewerze (Claude).

✅ Ten sam prompt i ten sam kontekst dla wszystkich modeli (porównywalność)  
✅ Review: zawsze Claude  
✅ Glossary: automatycznie **filtrowane**, aby nie przeładowywać promptu:
- zawsze uwzględnia terminy `locked=True`
- dodatkowo uwzględnia terminy, których `term_pl` występuje w SOURCE (NAME+BODY)
"""
)

# ======================================================
# Config
# ======================================================
lang = st.session_state.get("target_language")
label = st.session_state.get("target_market_label")
style_hint_default = st.session_state.get("style_hint", "")

if not lang:
    st.warning("Najpierw wybierz język w Configuration.")
    st.stop()

st.subheader(f"Rynek: {label}")
st.caption("Translate: OpenAI / Claude / Gemini | Review: Claude")

# ======================================================
# Helpers
# ======================================================

def load_glossary_df(lang_code: str) -> pd.DataFrame:
    path = f"data/glossary_{lang_code}.csv"
    if not os.path.exists(path):
        return pd.DataFrame(columns=["term_pl", "term_target", "locked", "notes"])

    df = pd.read_csv(path)
    for col in ["term_pl", "term_target", "locked", "notes"]:
        if col not in df.columns:
            df[col] = "" if col != "locked" else False

    df["term_pl"] = df["term_pl"].astype(str).str.strip()
    df["term_target"] = df["term_target"].astype(str).str.strip()
    df["locked"] = df["locked"].apply(lambda x: str(x).strip().lower() in ["true", "1", "yes", "y", "t"])
    df["notes"] = df["notes"].astype(str)

    # keep only meaningful rows
    df = df[(df["term_pl"].str.len() > 0) & (df["term_target"].str.len() > 0)].copy()
    df = df.drop_duplicates(subset=["term_pl"], keep="last").reset_index(drop=True)
    return df


def filter_glossary_for_source(df: pd.DataFrame, source_text: str) -> pd.DataFrame:
    """
    Keep:
    - locked=True always
    - OR term_pl appears in source_text (case-insensitive)
    """
    if df.empty:
        return df

    src = (source_text or "").lower()

    def appears(term: str) -> bool:
        t = (term or "").strip().lower()
        if not t:
            return False
        # simple containment, but avoid false positives on very short tokens
        if len(t) <= 2:
            return False
        return t in src

    mask_locked = df["locked"] == True
    mask_appears = df["term_pl"].apply(appears)

    filtered = df[mask_locked | mask_appears].copy()

    # Optional: prioritize locked first, then those that appear
    filtered["__prio"] = filtered["locked"].apply(lambda x: 0 if x else 1)
    filtered = filtered.sort_values(["__prio", "term_pl"]).drop(columns=["__prio"]).reset_index(drop=True)

    return filtered


def glossary_to_text(df: pd.DataFrame) -> str:
    if df.empty:
        return ""
    rows = []
    for _, r in df.iterrows():
        rows.append(f"- {r['term_pl']} => {r['term_target']}")
    return "\n".join(rows)


# ======================================================
# Input
# ======================================================

col1, col2 = st.columns([1, 1])

with col1:
    title_pl = st.text_input("Nazwa (PL)", placeholder="np. Fotel fryzjerski Enzo X1")
    temperature = st.slider("Temperature (dla wszystkich modeli)", 0.0, 0.8, 0.2, 0.05)

with col2:
    benchmark_context = st.text_area(
        "Kontekst benchmarku (opcjonalnie)",
        value=style_hint_default,
        height=120,
        help="Ten kontekst zostanie użyty identycznie dla OpenAI / Claude / Gemini. "
             "Jeśli puste — prompt działa bez dodatkowego kontekstu."
    )

body_pl = st.text_area("Dalsza treść (PL)", height=220)

st.divider()

# ======================================================
# Prompt templates
# ======================================================

SYSTEM_TRANSLATE = "You are a professional translator. Translate precisely. Output plain text only."
SYSTEM_REVIEW = "You are a senior linguistic reviewer."

def build_translate_user_prompt(source_text: str, glossary_block: str) -> str:
    return f"""
Target language: {label}

Context:
{benchmark_context.strip() if benchmark_context.strip() else "None"}

Mandatory terminology:
{glossary_block if glossary_block else "None"}

Rules:
- Output plain text only (no HTML)
- Preserve structure NAME/BODY
- Use mandatory terminology when applicable
- Keep numbers/units consistent
- Do not add explanations

Translate:

{source_text}
""".strip()


def build_review_user_prompt(source_text: str, translation: str, provider_name: str, glossary_block: str) -> str:
    return f"""
Compare translation quality objectively.

Mandatory terminology (must be respected):
{glossary_block if glossary_block else "None"}

Return format:
VERDICT: OK / FIX
ISSUES:
- ...
SUGGESTED FIXES:
- ...
CONFIDENCE: 0-100

SOURCE:
{source_text}

TRANSLATION ({provider_name}):
{translation}
""".strip()

# ======================================================
# Benchmark
# ======================================================

if st.button("Run benchmark", type="primary"):
    if not ((title_pl or "").strip() or (body_pl or "").strip()):
        st.warning("Uzupełnij nazwę lub treść.")
        st.stop()

    source = f"NAME:\n{title_pl.strip()}\n\nBODY:\n{body_pl.strip()}"

    # Load + filter glossary
    gdf_all = load_glossary_df(lang)
    gdf_filtered = filter_glossary_for_source(gdf_all, source)
    glossary_block = glossary_to_text(gdf_filtered)

    # UX info
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Glossary: wszystkie wpisy", int(len(gdf_all)))
    with c2:
        st.metric("Glossary: użyte w benchmarku", int(len(gdf_filtered)))
    with c3:
        locked_count = int(gdf_all["locked"].sum()) if not gdf_all.empty else 0
        st.metric("Glossary: locked (łącznie)", locked_count)

    with st.expander("Podgląd terminów użytych w benchmarku", expanded=False):
        if gdf_filtered.empty:
            st.info("Brak terminów do użycia (albo glossary puste, albo brak term_target).")
        else:
            st.dataframe(gdf_filtered[["term_pl", "term_target", "locked"]], use_container_width=True)

    providers = [("openai", "OpenAI"), ("claude", "Claude"), ("gemini", "Gemini")]
    results = {}

    # Translate (3 models)
    with st.spinner("Tłumaczenie (OpenAI / Claude / Gemini)…"):
        for code, name in providers:
            translated = chat_llm(
                provider=code,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": SYSTEM_TRANSLATE},
                    {"role": "user", "content": build_translate_user_prompt(source, glossary_block)},
                ],
            )
            results[code] = {"translation": translated}

    # Review (always Claude)
    with st.spinner("Review (Claude)…"):
        for code, name in providers:
            review = chat_llm(
                provider="claude",
                temperature=0.1,
                messages=[
                    {"role": "system", "content": SYSTEM_REVIEW},
                    {"role": "user", "content": build_review_user_prompt(source, results[code]["translation"], name, glossary_block)},
                ],
            )
            results[code]["review"] = review

    st.session_state.benchmark = {
        "context": benchmark_context,
        "source": source,
        "glossary_used": gdf_filtered.to_dict(orient="records"),
        "results": results,
    }

# ======================================================
# Output
# ======================================================

if "benchmark" in st.session_state:
    st.subheader("Wyniki benchmarku")

    with st.expander("Zastosowany kontekst, źródło i (filtrowane) glossary", expanded=False):
        st.markdown("**Kontekst:**")
        st.code(st.session_state.benchmark["context"] if st.session_state.benchmark["context"].strip() else "None")
        st.markdown("**Źródło (PL):**")
        st.code(st.session_state.benchmark["source"])

        st.markdown("**Glossary użyte w benchmarku:**")
        g_used = st.session_state.benchmark.get("glossary_used", [])
        if not g_used:
            st.info("Brak terminów użytych (puste glossary albo brak term_target).")
        else:
            st.dataframe(pd.DataFrame(g_used)[["term_pl", "term_target", "locked"]], use_container_width=True)

    tabs = st.tabs(["OpenAI", "Claude", "Gemini"])
    mapping = [("openai", "OpenAI"), ("claude", "Claude"), ("gemini", "Gemini")]

    for tab, (code, name) in zip(tabs, mapping):
        with tab:
            st.markdown(f"### Translation — {name}")
            st.code(st.session_state.benchmark["results"][code]["translation"], language="text")

            st.markdown("### Review (Claude)")
            st.code(st.session_state.benchmark["results"][code]["review"], language="text")
