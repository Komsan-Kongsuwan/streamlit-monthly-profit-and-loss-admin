# streamlit_monthly_profit_and_loss/chart_page.py
import streamlit as st
import pandas as pd
import plotly.express as px
import re

def render_chart_page():
    # --- Reduce top and side margins/paddings of the page ---
    st.markdown("""
        <style>
            .block-container {
                padding-top: 1.5rem;
                padding-left: 1rem;
                padding-right: 1rem;
                padding-bottom: 0rem;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <style>
            /* Target only sidebar site buttons */
            section[data-testid="stSidebar"] div.stButton > button {
                font-size: 12px !important;
                padding: 0.1rem 0.25rem !important;
                height: auto !important;      /* let it shrink naturally */
                min-height: 40px !important;  /* force smaller baseline */
                border-radius: 6px !important;
                line-height: 1.2px !important;
            }
    
            /* Also shrink the <p> text inside */
            section[data-testid="stSidebar"] div.stButton p {
                font-size: 12px !important;
                margin: 0 !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    if "official_data" not in st.session_state:
        st.warning("⚠️ Data not found. Please upload excel files or load sample data first.")
        st.stop()

    # --- Prepare data safely ---
    df_raw = st.session_state["official_data"].copy()
    df_raw['Amount'] = pd.to_numeric(df_raw['Amount'], errors='coerce').fillna(0)

    # ✅ Normalize Year/Month before creating Period (handles int/float from Excel)
    df_raw['Year'] = df_raw['Year'].astype(float).astype(int).astype(str)
    df_raw['Month'] = df_raw['Month'].astype(float).astype(int).astype(str).str.zfill(2)
    df_raw['Period'] = pd.to_datetime(df_raw['Year'] + "-" + df_raw['Month'], format="%Y-%m", errors='coerce')

    # --- Sites list & resilient selection ---
    sites = sorted([s for s in df_raw['Site'].dropna().unique().tolist() if str(s).strip() != ""])
    if not sites:
        st.error("No sites found in the current data.")
        st.stop()

    # Create a simple signature of current dataset to detect data switches
    data_signature = (tuple(sites), df_raw['Period'].min(), df_raw['Period'].max())
    if st.session_state.get("data_signature") != data_signature:
        # Dataset changed → reset selected site to first
        st.session_state["data_signature"] = data_signature
        st.session_state["selected_site"] = sites[0]

    # Initialize or repair selection if missing/out-of-range
    if "selected_site" not in st.session_state or st.session_state.selected_site not in sites:
        st.session_state.selected_site = sites[0]

    # --- Sidebar: Site navigate buttons ---
    for site in sites:
        if st.sidebar.button(site, use_container_width=True):
            st.session_state.selected_site = site

    site_code = st.session_state.selected_site

    # --- Filter data for selected site ---
    df_site = df_raw[df_raw['Site'] == site_code].copy()
    if df_site.empty:
        st.info(f"No data for selected site: {site_code}")
        st.stop()

    # --- Monthly Comparison Summary ---
    item_order = [
        "[1045]-Revenue Total", "[1046]-Variable Cost",
        "[1047]-Marginal Profit", "[1048]-Fix Cost",
        "[1050]-Gross Profit",
        "[1051]-Expense Total", "[1052]-Operate Profit"
    ]
    df_selected = df_site[df_site['Item Detail'].isin(item_order)].copy()

    # Choose latest/prior months safely
    latest_month = df_selected['Period'].max()
    if pd.isna(latest_month):  # if summary rows missing, fall back to any available month for the site
        latest_month = df_site['Period'].max()

    if pd.isna(latest_month):
        st.info("No valid Period values in data.")
        st.stop()

    # If there is no real previous month in data, we still show comparison vs prior calendar month (values will be 0)
    prior_in_data = df_selected[df_selected['Period'] < latest_month]['Period'].max()
    prior_month = prior_in_data if pd.notna(prior_in_data) else (latest_month - pd.DateOffset(months=1))

    cost_items = {"[1046]-Variable Cost", "[1048]-Fix Cost", "[1051]-Expense Total"}

    def get_star_rating(is_cost=False, this_month_val=0, last_month_val=0):
        diff = this_month_val - last_month_val
        pct = (diff / last_month_val * 100) if last_month_val != 0 else 0
        if is_cost:
            if pct < -30: return "⭐⭐⭐⭐"
            elif pct <= -20: return "⭐⭐⭐"
            elif pct <= -10: return "⭐⭐"
            elif pct <= 0: return "⭐"
            elif pct <= 10: return "🚨"
            elif pct <= 20: return "🚨🚨"
            elif pct <= 30: return "🚨🚨🚨"
            else: return "🚨🚨🚨🚨"
        else:
            if this_month_val > 0:
                if pct > 50: return "⭐⭐⭐⭐"
                elif pct >= 25: return "⭐⭐⭐"
                elif pct >= 5: return "⭐⭐"
                elif pct >= 0: return "⭐"
                elif pct >= -5: return "🚨"
                elif pct >= -25: return "🚨🚨"
                elif pct >= -50: return "🚨🚨🚨"
                else: return "🚨🚨🚨🚨"
            else:
                if this_month_val > -5000: return "🚨"
                elif this_month_val >= -50000: return "🚨🚨"
                elif this_month_val >= -100000: return "🚨🚨🚨"
                elif this_month_val >= -500000: return "🚨🚨🚨🚨"
                else: return "🚨🚨🚨🚨"

    comparison_data = []
    for item in item_order:
        this_month_val = df_selected[(df_selected['Period'] == latest_month) & (df_selected['Item Detail'] == item)]['Amount'].sum()
        last_month_val = df_selected[(df_selected['Period'] == prior_month) & (df_selected['Item Detail'] == item)]['Amount'].sum()
        diff = this_month_val - last_month_val
        pct = (diff / last_month_val * 100) if last_month_val != 0 else 0
        is_cost = item in cost_items
        rating = get_star_rating(is_cost=is_cost, this_month_val=this_month_val, last_month_val=last_month_val)
        arrow, color = ("▲", "red") if (is_cost and this_month_val > last_month_val) else \
                       ("▼", "green") if is_cost else \
                       ("▲", "green") if this_month_val > last_month_val else ("▼", "red")

        comparison_data.append({
            "Item": item.split("]-")[-1],
            "Current": f"{this_month_val:,.0f} THB",
            "Previous": f"{last_month_val:,.0f} THB",
            "Diff": f"{abs(diff):,.0f} THB",
            "Pct": f"{abs(pct):.2f} %",
            "Arrow": arrow,
            "Month1": latest_month.strftime("%b-%Y"),
            "Month2": prior_month.strftime("%b-%Y"),
            "Color": color,
            "Rating": rating
        })

    # --- Comparison Summary Inline (7 boxes in one line) ---
    st.markdown(f"""
        <p style='margin-top:0; margin-bottom:0.5rem; color:#333; font-size:20px; font-weight:bold'>
            Site : {site_code} - Visualize - Revenue/Cost/Profit - {latest_month.strftime('%B %Y')}
        </p>
    """, unsafe_allow_html=True)

    cols = st.columns(7)  # 🔹 exactly 7 boxes
    for col, data in zip(cols, comparison_data):
        col.markdown(f"""
        <div style="border:1px solid #ccc; border-radius:6px; padding:6px;
                    background-color:#f9f9f9; box-shadow:1px 1px 3px rgba(0,0,0,0.1);
                    font-size:11px;">
            <p style="font-size:11px; font-weight:bold; margin-bottom:4px; color:#333;">
                {data['Item']} {data['Rating']}
            </p>
            <p style="margin:2px 0; font-size:12px;"><b>{data['Month2']}:</b> 
                <span style="color:black;">{data['Previous']}</span></p>
            <p style="margin:2px 0; font-size:12px; font-weight:bold;"><b>{data['Month1']}:</b> 
                <span style="color:black;">{data['Current']}</span></p>
            <p style="margin-top:2px; color:{data['Color']}; font-size:12px;">
                {data['Arrow']} {data['Pct']} = {data['Diff']}
            </p>
        </div>
        <br>
        """, unsafe_allow_html=True)

    # --- Line & Bar Chart Side by Side (70:30 layout) ---
    items = sorted(df_site['Item Detail'].dropna().unique())
    selected_items = st.multiselect("Select Item Detail Chart", items, default=["[1045]-Revenue Total"])
    if not selected_items:
        st.info("Select at least one item.")
        st.stop()

    col1, col2 = st.columns([6, 4])  # 70% line chart, 30% bar chart

    with col1:
        line_df = df_site[df_site['Item Detail'].isin(selected_items)] \
            .groupby(['Item Detail', 'Period'], as_index=False)['Amount'].sum()
        fig_line = px.line(line_df, x='Period', y='Amount', color='Item Detail', markers=False)
        fig_line.update_layout(
            height=240,
            margin=dict(l=10, r=10, t=40, b=20),
            showlegend=False,
            xaxis_title = "",
            yaxis_title = "",
            hovermode="x",   # vertical hover across traces       
            xaxis=dict(
                showspikes=True,       # enable spike line
                spikemode="across",    # line across entire plot
                spikesnap="cursor",    # follow mouse cursor
                showline=False,
                spikedash="dash",
                spikecolor="red",
                spikethickness=1
            ),
            hoverlabel=dict(
                bgcolor="#7F7F7F",   # tooltip background
                font_size=12,
                font_color="white"
            ),            
        )
        st.plotly_chart(fig_line, use_container_width=True)
    
    with col2:
        bar_df = df_site[df_site['Item Detail'].isin(selected_items)] \
            .groupby(['Item Detail', 'Year'], as_index=False)['Amount'].sum()
        fig_bar = px.bar(bar_df, x='Year', y='Amount', color='Item Detail', text_auto='.2s')
    
        # Move legend to bottom
        fig_bar.update_layout(
            height=240,
            margin=dict(l=10, r=10, t=40, b=40),  # add some bottom margin for legend
            legend=dict(
                orientation='h',    # horizontal legend
                y=-0.2,             # vertical position (below plot)
                x=0.0,              # horizontal start (left)
                xanchor='left',
                yanchor='top'
            ),
            xaxis_title = "",
            yaxis_title = "",
            legend_title = None
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # --- Rolling 24-Month Revenue Table ---
    if not selected_items:
        st.info("Select at least one item for the rolling table.")
    else:
        # Filter revenue for selected items
        df_revenue = df_site[df_site["Item Detail"].isin(selected_items)].copy()
        
        if not df_revenue.empty:
            # Group by Period and Item Detail
            df_revenue = (
                df_revenue.groupby(["Item Detail", "Period"], as_index=False)["Amount"]
                .sum()
                .sort_values("Period")
            )
    
            # Last 24 months
            df_revenue = df_revenue[df_revenue["Period"] >= (df_revenue["Period"].max() - pd.DateOffset(months=23))]
    
            # Pivot table: rows=Amount/Diff, columns=Period
            months = df_revenue["Period"].dt.strftime("%b-%Y").unique().tolist()
            data_rows = []
            for item in selected_items:
                item_data = df_revenue[df_revenue["Item Detail"] == item]
                amounts = [(a / 1000) for a in item_data["Amount"]]
                diffs_raw = item_data["Amount"].diff().fillna(0).tolist()
                diffs = [(d / 1000) for d in diffs_raw]
                diffs[0] = None
    
                # Amount row
                data_rows.append({"Item": item, "Type": "Amount", **dict(zip(months, amounts))})
                # Diff row
                data_rows.append({"Item": item, "Type": "Diff", **dict(zip(months, ["" if d is None else d for d in diffs]))})
    
            df_pivot = pd.DataFrame(data_rows)
    
            # Convert to HTML with colored formatting and comma formatting
            html = "<table style='font-size:10px; border-collapse: collapse;'>"
            # Header
            html += "<tr><th style='padding:4px 4px;text-align:left;'>Item / Type</th>"
            for m in months:
                html += f"<td style='padding:4px 4px;text-align:right;'>{m}</td>"
            html += "</tr>"
    
            # Rows
            for _, row in df_pivot.iterrows():
                row_label = (
                    re.sub(r'^\[\d+\]-', '', row['Item']) + " (KB)"
                    if row['Type'] == "Amount"
                    else f"{row['Type']} (KB)"
                )
                
                html += f"<tr><td style='padding:4px 4px; margin:0; text-align:left;'><b>{row_label}</b></td>"
                for m in months:
                    val = row.get(m, "")
                    if val == "":
                        html += "<td></td>"
                    else:
                        formatted_val = f"{int(abs(val)):,}"  # <-- add comma formatting
                        if row['Type'] == "Diff":
                            color = "green" if val > 0 else "red"
                            sign = "+" if val > 0 else "-"
                            bold = "font-weight:bold;"
                        else:
                            color = "black"
                            sign = ""
                            bold = ""
                        html += f"<td style='padding:0px 4px; margin:0; text-align:right; {bold} color:{color}'>{sign}{formatted_val}</td>"
                html += "</tr>"
    
            html += "</table>"
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.info("No revenue data available for the selected items at this site.")
