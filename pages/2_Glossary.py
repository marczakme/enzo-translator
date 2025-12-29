import streamlit as st
import pandas as pd

st.set_page_config(page_title="Glossary", layout="wide")
st.header("2) Glossary (PL → język docelowy)")

if "glossary_df" not in st.session_state:
    st.session_state.glossary_df = pd.DataFrame(
        [
            {"term_pl": "fotel fryzjerski", "term_target": "", "locked": True, "notes": ""},
            {"term_pl": "myjnia fryzjerska", "term_target": "", "locked": True, "notes": ""},
        ]
    )

st.caption("Uzupełnij term_target. Zaznacz locked dla terminów, które muszą być konsekwentne.")

edited = st.data_editor(
    st.session_state.glossary_df,
    use_container_width=True,
    num_rows="dynamic",
    column_config={"locked": st.column_config.CheckboxColumn("locked")}
)

st.session_state.glossary_df = edited

st.write("Podgląd (pierwsze 10):")
st.dataframe(st.session_state.glossary_df.head(10), use_container_width=True)
