import os
import streamlit as st
import pandas as pd
from pyairtable import Api
from dotenv import load_dotenv

load_dotenv()
st.set_page_config(page_title="Endo Practice", layout="wide")

@st.cache_data(ttl=60)
def fetch_data():
    airtable = Api(os.getenv("AIRTABLE_API_KEY"))
    table = airtable.table(os.getenv("AIRTABLE_BASE_ID"), os.getenv("AIRTABLE_TABLE_NAME"))
    records = table.all()
    if not records: 
        return pd.DataFrame()
    
    df = pd.DataFrame([r["fields"] for r in records])
    
    # SAFETY FIX: Ensure all columns exist even if Airtable hides empty ones
    expected_numeric = ["Patients", "Total_Fee", "Paid", "Balance"]
    for col in expected_numeric:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        
    return df

st.title("🦷 Practice Analytics")
df = fetch_data()

if df.empty:
    st.info("No records yet.")
else:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Patients", int(df["Patients"].sum()))
    c2.metric("Billed", f"₹{int(df['Total_Fee'].sum()):,}")
    c3.metric("Collected", f"₹{int(df['Paid'].sum()):,}")
    c4.metric("Pending", f"₹{int(df['Balance'].sum()):,}")
    
    st.dataframe(df, use_container_width=True)