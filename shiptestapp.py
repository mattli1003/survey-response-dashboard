# app.py

import streamlit as st
import pandas as pd
import re
from io import BytesIO
import requests, zipfile

# CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
 [data-testid="stSidebar"] a { color: black!important; }
 .sidebar .markdown-text-container ul { padding-left: 0; }
 .sidebar .markdown-text-container ul li { margin: 8px 0; list-style: none; }
 .sidebar .markdown-text-container ul li a {
   display: inline-block; width:100%; padding:8px 12px; margin-bottom:4px;
   background:#fafafa; border:1px solid #e1e5ea; border-radius:4px;
   text-decoration:none; font-weight:500;
 }
 .sidebar .markdown-text-container ul li a:hover {
   background:#f0f2f6; border-color:#c6cbd3;
 }
</style>
""", unsafe_allow_html=True)

# Page setup ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Survey Response Dashboard", layout="wide")
st.markdown('<a id="top"></a>', unsafe_allow_html=True)
st.title("📊 Survey Response Dashboard")

# Helpers ─────────────────────────────────────────────────────────────────
def clean_headers(df):
    df.columns = [re.sub(r"\s*\([^)]*\)", "", c).strip() for c in df.columns]
    return df

def drop_irrelevant(df):
    rx = re.compile(r"first.*last.*name|tracking|clean|email|\btoken\b|submitted\s*at", re.IGNORECASE)
    return df[[c for c in df.columns if not rx.search(c)]]

def summarize_simple(s):
    c = s.value_counts(dropna=False)
    p = c / c.sum() * 100
    return pd.DataFrame({
        "Response": c.index.astype(str),
        "Count":    c.values,
        "Percent (%)": p.round(1).values
    })

def summarize_multi(s):
    total = len(s.dropna())
    ex = s.dropna().str.split(",").explode().str.strip()
    c = ex.value_counts()
    p = c / total * 100
    return pd.DataFrame({
        "Response": c.index.astype(str),
        "Count":    c.values,
        "Percent (%)": p.round(1).values
    })

def make_slug(name, length=20):
    return re.sub(r"\W+", "_", name).strip("_").lower()[:length]

multi_re = re.compile(r"select.*appl", re.IGNORECASE)
photo_re = re.compile(r"(take.*picture|attach.*picture|photo)", re.IGNORECASE)

# Upload ───────────────────────────────────────────────────────────────────
uploaded = st.file_uploader("Upload your survey CSV or Excel", type=["csv","xlsx"])
if not uploaded:
    st.info("Please upload a file.")
    st.stop()

raw = pd.read_excel(uploaded) if uploaded.name.lower().endswith(".xlsx") else pd.read_csv(uploaded)

# Prepare Data ─────────────────────────────────────────────────────────────
df = clean_headers(raw.copy())
photo_cols = [c for c in df.columns if photo_re.search(c)]
df = drop_irrelevant(df)

# Sidebar: combined download ───────────────────────────────────────────────
all_summaries = []
for col in df.columns:
    if col in photo_cols:
        continue
    fn = summarize_multi if multi_re.search(col) else summarize_simple
    all_summaries.append(fn(df[col]).assign(Question=col))

combined = pd.concat(all_summaries, ignore_index=True)
buf = BytesIO()
with pd.ExcelWriter(buf, engine="openpyxl") as writer:
    combined.to_excel(writer, "All Responses", index=False)

st.sidebar.download_button(
    "📥 Download Combined Summary",
    data=buf.getvalue(),
    file_name="survey_combined_summary.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# Sidebar: segment & nav ──────────────────────────────────────────────────
segment_col = st.sidebar.selectbox("Segment by (optional):", [None] + list(df.columns))
st.sidebar.markdown("---\n## Quick Navigate")
nav = "<ul>" + "".join(f'<li><a href="#anchor_{i}">{c}</a></li>' for i, c in enumerate(df.columns)) + "</ul>"
st.sidebar.markdown(nav, unsafe_allow_html=True)

# Main display ─────────────────────────────────────────────────────────────
for i, col in enumerate(df.columns):
    st.markdown(f'<a id="anchor_{i}"></a>', unsafe_allow_html=True)
    st.header(col)

    if col in photo_cols:
        slug = make_slug(col)
        if st.button(f"📷 Build ZIP for “{col}”", key=f"build_{i}"):
            zb = BytesIO()
            with zipfile.ZipFile(zb, "w") as z:
                for idx, url in df[col].dropna().items():
                    try:
                        r = requests.get(url, timeout=5); r.raise_for_status()
                        ext = url.split(".")[-1].split("?")[0]
                        z.writestr(f"{slug}/{idx}.{ext}", r.content)
                    except:
                        pass
            st.download_button(
                f"📥 Download Photos for “{col}”",
                data=zb.getvalue(),
                file_name=f"{slug}_photos.zip",
                mime="application/zip",
                key=f"dl_{i}"
            )
    else:
        fn, subtitle = (summarize_multi, "Split-out Multi-Select") if multi_re.search(col) else (summarize_simple, "Overall")
        if segment_col and segment_col != col:
            for val in df[segment_col].dropna().unique():
                st.subheader(f"{subtitle} | {segment_col} = {val}")
                sd = fn(df[df[segment_col] == val][col])
                if fn is summarize_simple:
                    total_row = pd.DataFrame([{
                        "Response":    "Total",
                        "Count":       sd["Count"].sum(),
                        "Percent (%)": sd["Percent (%)"].sum().round(1)
                    }])
                    sd = pd.concat([sd, total_row], ignore_index=True)
                st.dataframe(sd, use_container_width=True)
        else:
            st.subheader(subtitle)
            sd = fn(df[col])
            if fn is summarize_simple:
                total_row = pd.DataFrame([{
                    "Response":    "Total",
                    "Count":       sd["Count"].sum(),
                    "Percent (%)": sd["Percent (%)"].sum().round(1)
                }])
                sd = pd.concat([sd, total_row], ignore_index=True)
            st.dataframe(sd, use_container_width=True)

# Back to Top ──────────────────────────────────────────────────────────────
st.markdown("[⬆️ Back to top](#top)", unsafe_allow_html=True)
