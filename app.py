import streamlit as st
import pandas as pd
import re
from io import StringIO
from datetime import datetime, timedelta
import unicodedata

def normalize_date_string(date_str):
    if isinstance(date_str, str):
        return unicodedata.normalize("NFKD", date_str.replace("\u202f", " ").replace("\xa0", " ")).strip()
    return date_str

def convert_date(date_str):
    try:
        cleaned = normalize_date_string(date_str)
        return pd.to_datetime(cleaned, format="%b %d, %Y, %I:%M:%S %p").strftime("%m/%d/%Y")
    except Exception:
        return None

def is_valid_date(date_str):
    try:
        cleaned = normalize_date_string(date_str)
        pd.to_datetime(cleaned, format="%b %d, %Y, %I:%M:%S %p")
        return True
    except:
        return False

def week_of_date(date_str):
    try:
        date_obj = pd.to_datetime(date_str, format="%m/%d/%Y")
        monday = date_obj - timedelta(days=date_obj.weekday())
        return monday.strftime("%m/%d/%Y")
    except:
        return None

def extract_action(text):
    if "added" in text.lower():
        return "Added"
    elif "enabled" in text.lower():
        return "Enabled"
    return None

def extract_match_type(line):
    line = line.lower()
    if "exact match" in line:
        return "Exact"
    elif "phrase match" in line:
        return "Phrase"
    elif "broad match" in line:
        return "Broad"
    return None

def extract_keywords_by_group(text):
    lines = text.split("\n")
    groupings = []
    current_action = None
    current_match_type = None

    for line in lines:
        line = line.strip()

        match_type = extract_match_type(line)
        action = extract_action(line)
        if match_type and action:
            if "keyword" not in line.lower():
                continue  # skip changes unrelated to keywords
            current_match_type = match_type
            current_action = action
            continue

        # Skip negative keyword lines
        if "negative" in line.lower() or line.startswith("-[") or line.startswith("-"):
            continue

        if current_match_type and current_action:
            keyword = re.sub(r":.*", "", line).strip("[]\" ").strip()
            if keyword:
                if "keyword status" in keyword.lower() or "status change" in keyword.lower():
                    continue  # skip group header mistakenly parsed as keyword
                groupings.append((keyword, current_match_type, current_action))

    return groupings

st.set_page_config(page_title="Keyword Insights Extractor", layout="centered")

st.image("logo.svg", width=256)

st.title("Google Ads Keyword Change History Processor")
st.markdown("""
Upload your **Google Ads Change History CSV file** below. This tool will extract all **Added** and **Enabled** keywords, organized by match type, and output them in a clean, flat format.

**Important:**
- When running the Change history report from Google Ads, filter for **Item changed = Keyword**
- Download the file as **plain CSV**, not Excel CSV format
- Do not edit or clean the CSV after downloading it — the tool is designed to handle the raw export as-is

**Required columns in the input CSV** (can be in any order):
- `Date & time`
- `User`
- `Campaign`
- `Ad group`
- `Changes`

The output will include:
- `Date added`, `Week of`, `User`, `Campaign`, `Ad group`, `Match type`, `Keyword`, `Action`
""")

uploaded_file = st.file_uploader("Choose a plain CSV file", type="csv")

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, encoding="utf-8", skiprows=2)

        required_cols = {"Date & time", "User", "Campaign", "Ad group", "Changes"}
        if not required_cols.issubset(df.columns):
            st.error("The uploaded CSV is missing one or more required columns.")
        else:
            df["Date & time"] = df["Date & time"].apply(normalize_date_string)
            df_cleaned = df[df["Date & time"].apply(is_valid_date)].copy()
            processed_data = []

            for _, row in df_cleaned.iterrows():
                date_added = convert_date(row["Date & time"])
                week_of = week_of_date(date_added)
                user = row["User"]
                campaign = row["Campaign"]
                ad_group = row["Ad group"]
                changes = row["Changes"]

                keyword_groups = extract_keywords_by_group(changes)
                for keyword, match_type, action in keyword_groups:
                    processed_data.append([
                        date_added, week_of, user, campaign, ad_group, match_type, keyword, action
                    ])

            if processed_data:
                result_df = pd.DataFrame(processed_data, columns=[
                    "Date added", "Week of", "User", "Campaign", "Ad group", "Match type", "Keyword", "Action"])

                st.success(f"Successfully extracted {len(result_df)} keywords.")
                st.dataframe(result_df, use_container_width=True)

                csv = result_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Processed CSV",
                    data=csv,
                    file_name="processed_keywords.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No valid keywords were found in the file.")

    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")
