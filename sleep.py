import streamlit as st
import openai
import random
import requests
from sleeper.api import (
    get_matchups_for_week,
    get_rosters,
    get_users_in_league,
)

# Access the OpenAI API key from secrets.toml
api_key = st.secrets["openai"]["api_key"]
openai.api_key = api_key

# Set your Sleeper league ID
LEAGUE_ID = "1125204823692955648"

# Giphy API Key (replace with your own if available, or use a similar GIF service)
GIPHY_API_KEY = st.secrets.get("giphy", {}).get("api_key", None)

# Function to fetch GIFs from Giphy
def fetch_random_gif(query):
    if not GIPHY_API_KEY:
        return "https://via.placeholder.com/300x200.png?text=No+GIF+Available"  # Placeholder image if no Giphy key
    try:
        url = f"https://api.giphy.com/v1/gifs/search?api_key={GIPHY_API_KEY}&q={query}&limit=10&offset=0&rating=g&lang=en"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            gifs = [gif["images"]["original"]["url"] for gif in data.get("data", [])]
            return random.choice(gifs) if gifs else "https://via.placeholder.com/300x200.png?text=No+GIFs"
        else:
            return "https://via.placeholder.com/300x200.png?text=GIF+Fetch+Error"
    except Exception:
        return "https://via.placeholder.com/300x200.png?text=GIF+Error"

# Function to fetch team mapping
def get_team_mapping():
    try:
        league_users = get_users_in_league(league_id=LEAGUE_ID)
        league_rosters = get_rosters(league_id=LEAGUE_ID)
        
        # Map user_id to display names
        user_mapping = {
            user["user_id"]: user.get("display_name", f"User {user['user_id']}")
            for user in league_users
        }
        
        # Map roster_id to user names (or team names if set)
        return {
            roster["roster_id"]: roster.get("metadata", {}).get("team_name", user_mapping.get(roster["owner_id"], f"Team {roster['roster_id']}"))
            for roster in league_rosters
        }
    except Exception as e:
        st.error(f"Error fetching league rosters or users: {e}")
        return {}

# Function to fetch matchups for a given week and map team names
def get_matchups_with_teams(week, team_mapping):
    try:
        matchups = get_matchups_for_week(league_id=LEAGUE_ID, week=week)
        matchups_with_teams = {}
        for matchup in matchups:
            matchup_id = matchup['matchup_id']
            team_name = team_mapping.get(matchup['roster_id'], f"Team {matchup['roster_id']}")

            if matchup_id not in matchups_with_teams:
                matchups_with_teams[matchup_id] = []

            matchups_with_teams[matchup_id].append({
                'team_name': team_name,
                'points': matchup['points']
            })
        return matchups_with_teams
    except Exception as e:
        st.error(f"Error fetching matchups for week {week}: {e}")
        return {}

# Function to generate roasts with final responses
def generate_roasts(matchups):
    roasts = []
    for matchup_id, teams in matchups.items():
        if len(teams) == 2:
            team1, team2 = teams[0], teams[1]
            prompt = (f"Team {team1['team_name']} scored {team1['points']} points against "
                      f"Team {team2['team_name']} who scored {team2['points']}. "
                      "Write a funny roast for this matchup.")
        else:
            prompt = f"Team {teams[0]['team_name']} played alone this week. Write a funny roast."

        try:
            # Generate the final roast response
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a witty and funny sports commentator."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.8
            )
            roast_text = response["choices"][0]["message"]["content"].strip()
            roasts.append({'matchup_id': matchup_id, 'roast': roast_text})

        except Exception as e:  # General exception handling
            roasts.append({'matchup_id': matchup_id, 'roast': f"Error generating roast: {str(e)}"})

    return roasts

# Streamlit app interface
st.title("Fantasy Football Matchup Roaster 🏈🔥")

week = st.number_input("Enter Week Number:", min_value=1, max_value=17, step=1)
if st.button("Generate Roasts"):
    with st.spinner("Fetching data and generating roasts..."):
        # Fetch team mapping
        team_mapping = get_team_mapping()

        if not team_mapping:
            st.error("No team mapping available. Check your league ID or try again later.")
        else:
            # Fetch matchups and align with team names
            matchups = get_matchups_with_teams(week, team_mapping)

            if not matchups:
                st.error(f"No matchups found for week {week}.")
            else:
                # Generate roasts
                roasts = generate_roasts(matchups)

                # Display roasts
                for roast in roasts:
                    st.subheader(f"Matchup {roast['matchup_id']}")
                    st.write(roast['roast'])

                    # Generate a random GIF query based on context
                    gif_query = random.choice(["crowd cheering", "football celebration", "epic fail"])
                    gif_url = fetch_random_gif(gif_query)

                    # Display the GIF
                    st.image(gif_url, use_column_width=True)