import streamlit as st
import pandas as pd
from datetime import datetime

# 1. PAGE SETUP
st.set_page_config(page_title="TDS Compliance Pro V4", layout="wide")

# Professional Styling
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #eee; }
    h1 { color: #1e3a8a; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_data():
    try:
        df = pd.read_excel("TDS_Master_Data.xlsx", engine='openpyxl')
        df.columns = [c.strip() for c in df.columns]
        # Standardize text data
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()
        
        df['Effective From'] = pd.to_datetime(df['Effective From'], errors='coerce')
        df['Effective To'] = pd.to_datetime(df['Effective To'], errors='coerce').fillna(pd.Timestamp('2099-12-31'))
        return df
    except Exception as e:
        st.error(f"Setup Error: {e}. Check if TDS_Master_Data.xlsx is in the repo.")
        return None

df = load_data()

if df is not None:
    st.sidebar.title("🛡️ Admin Panel")
    st.sidebar.success("V4 Active: Professional Edition")
    st.sidebar.markdown("---")
    st.sidebar.write("This model uses multi-layer filtering for Section 194I and 194C compliance.")

    st.title("🏛️ TDS Compliance Professional - V4")
    st.caption(f"System Date: {datetime.now().strftime('%d %B, %Y')} | Data Source: TDS_Master_Data.xlsx")
    st.write("---")

    # INPUT AREA
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.subheader("📋 Transaction Info")
        sections = sorted([s for s in df['Section'].unique() if s != 'nan'])
        section = st.selectbox("1. Select Section", options=sections)
        
        # Layer 1: Filter by Section
        f_df = df[df['Section'] == section]
        
        # Layer 2: Nature of Payment
        natures = sorted([n for n in f_df['Nature of Payment'].unique() if n != 'nan'])
        nature_sel = st.selectbox("2. Nature of Payment", options=natures)
        
        # Amount
        amount = st.number_input("3. Amount (INR)", min_value=0.0, value=250000.0)

    with col2:
        st.subheader("👤 Payee Config")
        
        # Layer 3: Smart Payee Category detection
        sub_f = f_df[f_df['Nature of Payment'] == nature_sel]
        p_types = sorted([p for p in sub_f['Payee Type'].unique() if p != 'nan'])
        
        if len(p_types) > 1:
            payee_sel = st.selectbox("4. Category of Payee", options=p_types)
        else:
            payee_sel = p_types[0] if p_types else "Any Resident"
            st.info(f"Detected Category: **{payee_sel}**")

        pan_status = st.radio("5. PAN Available?", ["Yes", "No"], horizontal=True)
        pay_date = st.date_input("6. Date of Payment")
        calc_mode = st.radio("7. Basis", ["Single Transaction", "Aggregate (Full Year)"], horizontal=True)

    st.write("---")

    # CALCULATION
    if st.button("🚀 EXECUTE COMPLIANCE CHECK", use_container_width=True):
        target = pd.to_datetime(pay_date)
        final_match = sub_f[sub_f['Payee Type'] == payee_sel]
        rule = final_match[(final_match['Effective From'] <= target) & (final_match['Effective To'] >= target)]
        
        if rule.empty and not final_match.empty:
            rule = final_match.sort_values(by='Effective From', ascending=False).head(1)

        if not rule.empty:
            sel = rule.iloc[0]
            try:
                base_rate = float(sel['Rate of TDS (%)'])
                thresh = float(sel['Threshold Amount (Rs)'])
                
                # Apply 194C Aggregate logic
                if section == "194C" and calc_mode == "Aggregate (Full Year)":
                    thresh = 100000.0
                
                # PAN Penalty
                final_rate = 20.0 if pan_status == "No" else base_rate
                
                # Dashboard Results
                r1, r2, r3 = st.columns(3)
                
                if amount > thresh:
                    tax = (amount * final_rate) / 100
                    r1.metric("TDS PAYABLE", f"₹{tax:,.2f}", delta="DEDUCT NOW", delta_color="inverse")
                    r2.metric("RATE", f"{final_rate}%")
                    r3.metric("LIMIT", f"₹{thresh:,.0f}", delta="BREACHED")
                    st.success("### ✅ Status: Compliance Action Required")
                else:
                    r1.metric("TDS PAYABLE", "₹0.00", delta="COMPLIANT")
                    r2.metric("POTENTIAL RATE", f"{final_rate}%")
                    r3.metric("LIMIT", f"₹{thresh:,.0f}", delta="SAFE")
                    st.warning("### ⚠️ Status: No TDS Required (Below Threshold)")

                with st.expander("📝 View Legal Basis"):
                    st.write(f"**Rule:** {sel['Nature of Payment']}")
                    st.write(f"**Payer Category:** {sel['Payer Category']}")
                    st.info(f"**Statutory Note:** {sel['Notes']}")
            except:
                st.error("Error: Check numeric values in Excel.")
