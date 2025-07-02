# app.py

import streamlit as st
import pandas as pd
import re
from io import BytesIO

# ─── 0. Custom CSS ───────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Force sidebar link color to black */
  [data-testid="stSidebar"] a,
  [data-testid="stSidebar"] a:link,
  [data-testid="stSidebar"] a:visited,
  [data-testid="stSidebar"] a:hover {
    color: black !important;
  }
  /* Sidebar button‐style nav items */
  .sidebar .markdown-text-container ul { padding-left: 0; }
  .sidebar .markdown-text-container ul li { list-style: none; margin: 8px 0; }
  .sidebar .markdown-text-container ul li a {
    display: inline-block; width: 100%; padding: 8px 12px; margin-bottom: 4px;
    background-color: #fafafa; border: 1px solid #e1e5ea; border-radius: 4px;
    text-decoration: none; font-weight: 500;
  }
  .sidebar .markdown-text-container ul li a:hover {
    background-color: #f0f2f6; border-color: #c6cbd3;
  }
</style>
""", unsafe_allow_html=True)

# ─── 1. Page config & title ──────────────────────────────────────────────────
st.set_page_config(page_title="Survey Response Dashboard", layout="wide")

# Anchor at the very top
st.markdown('<a id="top"></a>', unsafe_allow_html=True)

st.title("📊 Survey Response Dashboard")

# ─── 2. Helpers ──────────────────────────────────────────────────────────────
def clean_headers(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [re.sub(r"\s*\([^)]*\)", "", c).strip() for c in df.columns]
    return df

def drop_irrelevant(df: pd.DataFrame) -> pd.DataFrame:
    patterns = [
        r"first.*last.*name", r"tracking", r"clean", r"email",
        r"take.*picture", r"attach.*picture", r"photo",
        r"\btoken\b", r"submitted\s*at"
    ]
    rx = re.compile("|".join(patterns), flags=re.IGNORECASE)
    return df[[c for c in df.columns if not rx.search(c)]]

def summarize(series: pd.Series) -> pd.DataFrame:
    counts = series.value_counts(dropna=False)
    percents = series.value_counts(normalize=True, dropna=False).mul(100)
    return pd.DataFrame({
        "Response": counts.index.astype(str),
        "Count": counts.values,
        "Percent (%)": percents.round(1).values
    })

# ─── 3. Upload CSV or Excel ──────────────────────────────────────────────────
uploaded = st.file_uploader("Upload your survey CSV or Excel", type=["csv","xlsx"])
if not uploaded:
    st.info("Please upload a file.")
    st.stop()

if uploaded.name.lower().endswith(".xlsx"):
    df = pd.read_excel(uploaded)
else:
    df = pd.read_csv(uploaded)

# ─── 4. Clean & drop unwanted ─────────────────────────────────────────────────
df = clean_headers(df)
df = drop_irrelevant(df)

# ─── 5. Sidebar: combined download ────────────────────────────────────────────
all_summaries = [ summarize(df[c]).assign(Question=c) for c in df.columns ]
combined = pd.concat(all_summaries, ignore_index=True)
buf = BytesIO()
with pd.ExcelWriter(buf, engine="openpyxl") as writer:
    combined.to_excel(writer, sheet_name="All Responses", index=False)
xlsx_data = buf.getvalue()

st.sidebar.download_button(
    "📥 Download Combined Summary",
    data=xlsx_data,
    file_name="survey_combined_summary.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# ─── 6. Sidebar: segmentation selector ─────────────────────────────────────────
segment_col = st.sidebar.selectbox(
    "Segment by (optional):",
    options=[None] + list(df.columns),
    index=0
)

# ─── 7. Sidebar: quick navigate ───────────────────────────────────────────────
st.sidebar.markdown("---\n## Quick Navigate")
nav = "<ul>\n"
for i, col in enumerate(df.columns):
    nav += f'  <li><a href="#anchor_{i}">{col}</a></li>\n'
nav += "</ul>"
st.sidebar.markdown(nav, unsafe_allow_html=True)

# ─── 8. Main area: display summaries ──────────────────────────────────────────
for i, col in enumerate(df.columns):
    # inject question anchor
    st.markdown(f'<a id="anchor_{i}"></a>', unsafe_allow_html=True)
    st.header(col)
    if segment_col and segment_col != col:
        for val in df[segment_col].dropna().unique():
            subset = df[df[segment_col] == val]
            st.subheader(f"{segment_col} = {val}")
            st.dataframe(summarize(subset[col]), use_container_width=True)
    else:
        st.subheader("Overall")
        st.dataframe(summarize(df[col]), use_container_width=True)

# ─── 9. Back to Top link at bottom ───────────────────────────────────────────
st.markdown("[⬆️ Back to top](#top)", unsafe_allow_html=True)
