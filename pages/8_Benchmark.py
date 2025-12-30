import streamlit as st
import pandas as pd
import os

from llm_providers import chat_llm, review_llm

st.set_page_config(page_title="Benchmark", layout="wide")
st.header("🧪 8) Benchmark — OpenAI vs Gemini vs Qwen | Review: Gemini")

lang = st.session_state.get("target_language")
label = st.session_state.get("target_market_label")
style_hint_default = st.session_state.get("style_hint", "")

if not lang:
    st.warning("Najpierw wybierz język w Configuration.")
    st.stop()

st.subheader(f"Rynek: {label}")
st.caption("Translate: OpenAI / Gemini / Qwen | Review: zawsze Gemini")

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

    df = df[(df["term_pl"].str.len() > 0) & (df["term_target"].str.len() > 0)].copy()
    df = df.drop_duplicates(subset=["term_pl"], keep="last").reset_index(drop=True)
    return df

def filter_glossary_for_source(df: pd.DataFrame, source_text: str) -> pd.DataFrame:
    if df.empty:
        return df
    src = (source_text or "").lower()

    def appears(term: str) -> bool:
        t = (term or "").strip().lower()
        if len(t) <= 2:
            return False
        return t in src

    mask_locked = df["locked"] == True
    mask_appears = df["term_pl"].apply(appears)

    filtered = df[mask_locked | mask_appears].copy()
    filtered["__prio"] = filtered["locked"].apply(lambda x: 0 if x else 1)
    filtered = filtered.sort_values(["__prio", "term_pl"]).drop(columns=["__prio"]).reset_index(drop=True)
    return filtered

def glossary_to_text(df: pd.DataFrame) -> str:
    if df.empty:
        return ""
    return "\n".join([f"- {r['term_pl']} => {r['term_target']}" for _, r in df.iterrows()])


col1, col2 = st.columns([1, 1])
with col1:
    title_pl = st.text_input("Nazwa (PL)", placeholder="np. Fotel fryzjerski Enzo X1")
    temperature = st.slider("Temperature (Translate, wspólne)", 0.0, 0.8, 0.2, 0.05)
with col2:
    benchmark_context = st.text_area(
        "Kontekst benchmarku (opcjonalnie)",
        value=style_hint_default,
        height=120,
        help="Ten kontekst zostanie użyty identycznie dla OpenAI / Gemini / Qwen."
    )

body_pl = st.text_area("Dalsza treść (PL)", height=220)

SYSTEM_TRANSLATE = "You are a professional translator. Translate precisely. Output plain text only."
SYSTEM_REVIEW = "You are a senior linguistic reviewer."

def build_translate_prompt(source_text: str, glossary_block: str) -> str:
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

def build_review_prompt(source_text: str, translation: str, provider_name: str, glossary_block: str) -> str:
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

st.divider()

if st.button("Run benchmark", type="primary"):
    if not ((title_pl or "").strip() or (body_pl or "").strip()):
        st.warning("Uzupełnij nazwę lub treść.")
        st.stop()

    source = f"NAME:\n{title_pl.strip()}\n\nBODY:\n{body_pl.strip()}"

    gdf_all = load_glossary_df(lang)
    gdf_filtered = filter_glossary_for_source(gdf_all, source)
    glossary_block = glossary_to_text(gdf_filtered)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Glossary: wszystkie wpisy", int(len(gdf_all)))
    with c2:
        st.metric("Glossary: użyte w benchmarku", int(len(gdf_filtered)))
    with c3:
        locked_count = int(gdf_all["locked"].sum()) if not gdf_all.empty else 0
        st.metric("Glossary: locked (łącznie)", locked_count)

    providers = [("openai", "OpenAI"), ("gemini", "Gemini"), ("qwen", "Qwen")]
    results = {}

    with st.spinner("Tłumaczenie (OpenAI / Gemini / Qwen)…"):
        for code, name in providers:
            translated = chat_llm(
                provider=code,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": SYSTEM_TRANSLATE},
                    {"role": "user", "content": build_translate_prompt(source, glossary_block)},
                ],
            )
            results[code] = {"translation": translated}

    with st.spinner("Review (Gemini)…"):
        for code, name in providers:
            review = review_llm(
                temperature=0.1,
                messages=[
                    {"role": "system", "content": SYSTEM_REVIEW},
                    {"role": "user", "content": build_review_prompt(source, results[code]["translation"], name, glossary_block)},
                ],
            )
            results[code]["review"] = review

    st.session_state.benchmark = {
        "context": benchmark_context,
        "source": source,
        "glossary_used": gdf_filtered.to_dict(orient="records"),
        "results": results,
    }

if "benchmark" in st.session_state:
    st.subheader("Wyniki benchmarku")

    with st.expander("Kontekst, źródło i glossary użyte w benchmarku", expanded=False):
        st.markdown("**Kontekst:**")
        st.code(st.session_state.benchmark["context"] if st.session_state.benchmark["context"].strip() else "None")
        st.markdown("**Źródło (PL):**")
        st.code(st.session_state.benchmark["source"])

        g_used = st.session_state.benchmark.get("glossary_used", [])
        if g_used:
            st.markdown("**Glossary użyte:**")
            st.dataframe(pd.DataFrame(g_used)[["term_pl", "term_target", "locked"]], width="stretch")

    tabs = st.tabs(["OpenAI", "Gemini", "Qwen"])
    mapping = [("openai", "OpenAI"), ("gemini", "Gemini"), ("qwen", "Qwen")]

    for tab, (code, name) in zip(tabs, mapping):
        with tab:
            st.markdown(f"### Translation — {name}")
            st.code(st.session_state.benchmark["results"][code]["translation"], language="text")
            st.markdown("### Review (Gemini)")
            st.code(st.session_state.benchmark["results"][code]["review"], language="text")
