import streamlit as st
import pandas as pd
import time

def load_sample_data():
    progress = st.progress(0, text="Starting...")

    # Step 1: Read Excel
    progress.progress(20, text="Reading Excel file...")
    df = pd.read_excel("official_raw_data.xlsx")
    time.sleep(0.3)  # simulate delay

    # Step 2: Clean Year / Month
    progress.progress(50, text="Processing Year/Month...")
    df['Year'] = df['Year'].astype(int).astype(str)
    df['Month'] = df['Month'].astype(int).astype(str).str.zfill(2)
    time.sleep(0.3)

    # Step 3: Create Period column
    progress.progress(80, text="Creating Period column...")
    df['Period'] = pd.to_datetime(df['Year'] + "-" + df['Month'], format="%Y-%m")
    time.sleep(0.3)

    # Step 4: Save to session state
    st.session_state["official_data"] = df
    st.session_state["selected_site"] = df["Site"].unique()[0]  # init site with first one

    progress.progress(100, text="✅ Done!")

    st.success("Sample data loaded successfully, Please go to Visualization page.")
    return df


# --- Main UI ---
st.title("📃 Load sample data to try out (click below button)")

if st.button("▶️ Load Sample Data"):
    df_raw = load_sample_data()

    # Show download only after data loaded
    with open("profit_and_loss_report_sample.xlsx", "rb") as f:
        st.download_button(
            label="📥 Download Profit and Loss Report (Sample)",
            data=f,
            file_name="profit_and_loss_report_sample.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Click the button above to load sample data.")
