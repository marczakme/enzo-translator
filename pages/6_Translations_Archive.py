import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Translations Archive", layout="wide")
st.header("6) Translations — Archiwum (TXT)")

BASE_DIR = os.path.join("data", "translations")

LANGS = [
    ("ro", "Rumuński (RO)"),
    ("hu", "Węgierski (HU)"),
    ("el", "Grecki (GR)"),
    ("de", "Niemiecki (DE)"),
    ("cs", "Czeski (CZ)"),
    ("sk", "Słowacki (SK)"),
    ("nl", "Niderlandzki (NL)"),
    ("it", "Włoski (IT)"),
    ("fr", "Francuski (FR)"),
    ("hr", "Chorwacki (HR)"),
    ("lt", "Litewski (LT)"),
    ("fi", "Fiński (FI)"),
    ("sv", "Szwedzki (SE)"),
]

def read_index(lang_code: str) -> pd.DataFrame:
    ip = os.path.join(BASE_DIR, f"index_{lang_code}.csv")
    if os.path.exists(ip):
        df = pd.read_csv(ip)
        # sort newest first
        if "datetime" in df.columns:
            df = df.sort_values("datetime", ascending=False)
        return df
    return pd.DataFrame(columns=["datetime", "title_pl", "filename"])

tabs = st.tabs([label for _, label in LANGS])

for (lang_code, lang_label), tab in zip(LANGS, tabs):
    with tab:
        st.subheader(f"{lang_label}")

        df = read_index(lang_code)

        count = len(df)
        last_dt = df["datetime"].iloc[0] if count and "datetime" in df.columns else "—"

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Liczba tłumaczeń", count)
        with c2:
            st.metric("Ostatnie tłumaczenie", last_dt)

        if df.empty:
            st.info("Brak zapisanych tłumaczeń dla tego języka. Zrób tłumaczenie w zakładce Translate.")
            continue

        st.dataframe(df, use_container_width=True)

        st.divider()
        st.markdown("### Pobierz plik TXT")

        options = df["filename"].tolist()
        chosen = st.selectbox("Wybierz plik", options=options, key=f"file_{lang_code}")

        file_path = os.path.join(BASE_DIR, lang_code, chosen)
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                st.download_button(
                    label="⬇️ Download TXT",
                    data=f.read(),
                    file_name=chosen,
                    mime="text/plain",
                    key=f"dl_{lang_code}_{chosen}"
                )
        else:
            st.error("Plik nie istnieje (możliwy reset środowiska). Wykonaj tłumaczenie ponownie.")
