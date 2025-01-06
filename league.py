import streamlit as st
from espn_api.football import League

# Fetch settings from secrets.toml
LEAGUE_ID = st.secrets["espn"]["league_id"]
YEAR = st.secrets["espn"]["year"]
ESPN_S2 = st.secrets["espn"]["espn_s2"]
SWID = st.secrets["espn"]["swid"]

# Test NFL Public League (if applicable, with public league settings)
try:
    league = League(league_id=LEAGUE_ID, year=YEAR)
    print(f"Public League Name: {league.settings.name}")
except Exception as e:
    print(f"Error with public NFL league: {e}")

# Test Private League with Cookies
try:
    league = League(
        league_id=LEAGUE_ID,
        year=YEAR,
        espn_s2=ESPN_S2,
        swid=SWID
    )
    print(f"Private League Name: {league.settings.name}")
except Exception as e:
    print(f"Error with private NFL league: {e}")

# Test Debug Mode (Explicitly Pass Cookies)
try:
    league = League(
        league_id=LEAGUE_ID,
        year=YEAR,
        espn_s2=ESPN_S2,
        swid=SWID,
        debug=True
    )
    print(f"Debug League Name: {league.settings.name}")
except Exception as e:
    print(f"Error in debug mode: {e}")

# Test Fetch Mode (Explicitly Pass Cookies)
try:
    league = League(
        league_id=LEAGUE_ID,
        year=YEAR,
        espn_s2=ESPN_S2,
        swid=SWID,
        fetch_league=False
    )
    league.fetch_league()  # Manually fetch league data
    print(f"Fetched League Name: {league.settings.name}")
except Exception as e:
    print(f"Error with fetch_league: {e}")