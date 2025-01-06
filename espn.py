import streamlit as st
from espn_api.football import League
import openai

# Fetch settings from secrets.toml
LEAGUE_ID = st.secrets["espn"]["league_id"]
YEAR = st.secrets["espn"]["year"]
ESPN_S2 = st.secrets["espn"]["espn_s2"]
SWID = st.secrets["espn"]["swid"]

# OpenAI API Key
openai.api_key = st.secrets["openai"]["api_key"]

# Function to fetch matchups
def fetch_matchups(league_id, year, espn_s2, swid, week):
    try:
        league = League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)
        matchups = league.scoreboard(week=week)
        return matchups
    except Exception as e:
        st.error(f"Error fetching matchups: {e}")
        return None

# Function to generate roasts using OpenAI
def generate_roast(home_team, home_score, away_team, away_score, is_playoff=False):
    try:
        playoff_text = " in the playoffs" if is_playoff else ""
        prompt = f"""Write a funny and sarcastic roast for a fantasy football matchup{playoff_text}:
Home Team: {home_team} (Score: {home_score})
Away Team: {away_team} (Score: {away_score})
Make it witty and fun!"""
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a witty sports commentator."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message["content"]
    except Exception as e:
        st.error(f"Error generating roast: {e}")
        return "Error generating roast."

# Streamlit interface
st.title("Fantasy Football Matchup Roaster 🏈🔥")

# Week selection dropdown
weeks = [f"NFL Week {i}" for i in range(1, 15)] + [
    "Playoff Round 1 (NFL Week 15 - NFL Week 16)",
    "Playoff Round 2 (NFL Week 17 - NFL Week 18)"
]
selected_week = st.selectbox("Select Week", weeks)

if st.button("Generate Roasts"):
    with st.spinner("Fetching matchups and generating roasts..."):
        # Determine if this is a playoff round
        if "Playoff Round" in selected_week:
            week = int(selected_week.split("NFL Week ")[-1][:2])
            is_playoff = True
        else:
            week = int(selected_week.split("NFL Week ")[-1])
            is_playoff = False

        matchups = fetch_matchups(LEAGUE_ID, YEAR, ESPN_S2, SWID, week)

        if matchups:
            st.subheader(f"Matchups for {selected_week}")
            for matchup in matchups:
                # Extract team details
                home_team = matchup.home_team.team_name if matchup.home_team else "N/A"
                away_team = matchup.away_team.team_name if matchup.away_team else "N/A"
                home_score = matchup.home_score
                away_score = matchup.away_score
                home_logo = matchup.home_team.logo_url if matchup.home_team and matchup.home_team.logo_url else None
                away_logo = matchup.away_team.logo_url if matchup.away_team and matchup.away_team.logo_url else None
                is_playoff_matchup = getattr(matchup, "is_playoff", False)

                # Generate roast
                roast = generate_roast(home_team, home_score, away_team, away_score, is_playoff=is_playoff_matchup)

                # Display matchup details with logos
                st.markdown(f"### {home_team} ({home_score}) vs {away_team} ({away_score})")
                cols = st.columns(2)
                with cols[0]:
                    if home_logo:
                        st.image(home_logo, width=100, caption=home_team)
                with cols[1]:
                    if away_logo:
                        st.image(away_logo, width=100, caption=away_team)

                # Display the roast
                st.write(roast)