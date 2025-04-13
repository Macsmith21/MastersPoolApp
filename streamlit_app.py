import streamlit as st  # Streamlit is used for building the web app
import pandas as pd  # Pandas is imported in case it's needed for future tabular data manipulation
import requests  # Used to make HTTP requests to the Masters leaderboard API
from collections import defaultdict  # Allows easy dictionary creation for tier counts
from streamlit_autorefresh import st_autorefresh  # Enables automatic app rerun every interval

from masters_teams_hardcoded import teams_data  # Load the pool teams from a separate hardcoded file

# Set up theme colors for Masters branding (updated with official values)
MASTERS_GREEN = "#006747"  # Official Masters green
MASTERS_YELLOW = "#fce300"  # Official Masters yellow
CUT_RED = "#ba0c2f"  # Official Masters red

# Configure the Streamlit app page layout
st_autorefresh(interval=5 * 60 * 1000, key="auto-refresh")



# Inject custom CSS styling for leaderboard tables and layout
st.markdown(f"""
    <style>
    @media screen and (max-width: 768px) {{
        .leaderboard-table {{ font-size: 10px; }}
        .leaderboard-table img {{ width: 24px !important; }}
        .leaderboard-table td, .leaderboard-table th {{ padding: 0.3em; }}
    }}
    .leaderboard-table {{ width: 100%; border-collapse: collapse; font-family: 'Arial Narrow', Arial, sans-serif; font-size: 16px; }}
    .leaderboard-table th, .leaderboard-table td {{ border: 1px solid #ccc; text-align: center; padding: 0.5em; }}
    .leaderboard-table th {{ background-color: {MASTERS_GREEN}; color: white; text-transform: uppercase; font-weight: bold; }}
    .leaderboard-table td.name {{ font-weight: bold; text-align: left; background-color: #e7f2eb; color: #000; }}
    .cut-score {{ background-color: {CUT_RED}; color: white; padding: 2px 6px; border-radius: 4px; font-weight: bold; }}
    .team-total {{ font-weight: bold; background-color: {MASTERS_GREEN}; color: white; }}
    tr:nth-child(even) td:not(.team-total):not(.name) {{ background-color: #f2f2f2; color: #000; }}
    tr:nth-child(odd) td:not(.team-total):not(.name) {{ background-color: #ffffff; color: #000; }}
    .logo {{ display: block; margin: 0 auto 10px auto; width: 180px; }}
    </style>
""", unsafe_allow_html=True)

# Masters logo at the top
st.markdown("<img src='https://www.masters.com/assets/images/nav/masters_logo_2023.png' class='logo'>", unsafe_allow_html=True)

# Title header displayed below logo
st.markdown("<h1 style='color:#006747; font-family:Georgia;'>🏌️ Masters Fantasy Pool</h1>", unsafe_allow_html=True)

# Fetch JSON live scores from the Masters website with 5-minute caching
@st.cache_data(ttl=300)
def fetch_live_scores():
    url = "https://www.masters.com/en_US/scores/feeds/2025/scores.json"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    data = res.json()
    if "data" in data and "player" in data["data"]:
        player_data = data["data"]["player"]
    elif "player" in data:
        player_data = data["player"]
    else:
        return {}
    return {p["full_name"].strip().lower(): p for p in player_data}

# Normalize "E" and convert topar string to int
def normalize_topar(val):
    if val == "E": return 0
    try: return int(val)
    except: return None

# Get player's normalized topar and status
def get_player_score(name, data):
    key = name.strip().lower()
    p = data.get(key)
    if not p:
        return None, "NOT FOUND"
    status = p.get("status", "OK")
    topar = p.get("topar")
    return normalize_topar(topar), status, p.get("id")  # Also return player ID

# Fetch leaderboard data
live_data = fetch_live_scores()
if not live_data:
    st.error("Could not fetch live Masters data.")
    st.stop()

# Calculate worst to-par across all players
worst_score = max([
    normalize_topar(p.get("topar"))
    for p in live_data.values()
    if normalize_topar(p.get("topar")) is not None
])

leaderboard = []
all_player_scores = []

# Loop through teams to construct leaderboard rows
for team in teams_data:
    row = {"Team": team["Person"], "Players": [], "AdjustedScores": []}
    for i in range(1, 7):
        name = team[f"Tier {i}"].strip()
        score, status, pid = get_player_score(name, live_data)

        # Build player image link if ID exists
        player_img = f"<img src='https://images.masters.com/players/2025/240x240/{pid}.jpg' width='40' style='border-radius:50%;'><br>" if pid else ""

        if score is None or status.upper() == "C":  # C = CUT
            adjusted = worst_score
            display_score = f"<span class='cut-score'>{adjusted}</span>"
        else:
            adjusted = score
            display_score = str(score)

        row["AdjustedScores"].append(adjusted)
        row["Players"].append(f"{player_img}<strong>{name}</strong><br>{display_score}")
        all_player_scores.append((name, adjusted))

    row["Total"] = sum(sorted(row["AdjustedScores"])[:5])
    leaderboard.append(row)

# Sort teams by score
leaderboard.sort(key=lambda x: x["Total"])

# Build leaderboard table
headers = ["Team"] + [f"Player {i}" for i in range(1, 7)] + ["Total"]
table_html = "<table class='leaderboard-table'>"
table_html += "<tr>" + "".join([f"<th>{h}</th>" for h in headers]) + "</tr>"
for row in leaderboard:
    table_html += f"<tr><td class='name'>{row['Team']}</td>"
    for p in row["Players"]:
        table_html += f"<td>{p}</td>"
    table_html += f"<td class='team-total'>{row['Total']}</td></tr>"
table_html += "</table>"

# Render leaderboard table
st.markdown(table_html, unsafe_allow_html=True)

# Sidebar: summary stats
with st.sidebar:
    st.markdown(f"<h3 style='color:{MASTERS_GREEN}'>🏆 Leader: {leaderboard[0]['Team']}</h3>", unsafe_allow_html=True)
    best_player = min(all_player_scores, key=lambda x: x[1])
    st.markdown(f"<h4 style='color:{MASTERS_GREEN}'>🌟 Best Player: {best_player[0]} ({best_player[1]} to-par)</h4>", unsafe_allow_html=True)
    st.markdown("<h4>📈 Player Picks by Tier</h4>", unsafe_allow_html=True)
    tier_counts = defaultdict(lambda: defaultdict(int))
    for team in teams_data:
        for i in range(1, 7):
            player = team[f"Tier {i}"].strip()
            tier_counts[f"Tier {i}"][player] += 1
    for tier in sorted(tier_counts.keys()):
        st.markdown(f"**{tier}**")
        sorted_counts = sorted(tier_counts[tier].items(), key=lambda x: -x[1])
        for name, count in sorted_counts:
            st.markdown(f"- {name}: {count} picks")
