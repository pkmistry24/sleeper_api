import streamlit as st
import openai
import random
import requests
import os
import json
from sleeper.api import (
    get_matchups_for_week,
    get_rosters,
    get_users_in_league,
)

# Access the OpenAI API key from secrets.toml
api_key = st.secrets["openai"]["api_key"]
openai.api_key = api_key

# Giphy API Key
GIPHY_API_KEY = st.secrets.get("giphy", {}).get("api_key", None)

# Set your Sleeper league ID
LEAGUE_ID = "1125204823692955648"

# Path to the player cache file
PLAYER_CACHE_FILE = "players_cache.json"

# Function to fetch and cache player data
def fetch_and_cache_players():
    if os.path.exists(PLAYER_CACHE_FILE):
        try:
            with open(PLAYER_CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"Cache file corrupted. Re-fetching player data. Error: {e}")

    # Fetch data from Sleeper API
    response = requests.get("https://api.sleeper.app/v1/players/nfl")
    if response.status_code == 200:
        player_data = response.json()
        with open(PLAYER_CACHE_FILE, "w") as f:
            json.dump(player_data, f)
        return player_data
    else:
        st.error(f"Error fetching player data: {response.status_code}")
        return {}

# Function to fetch avatars for users
def fetch_avatar(avatar_id):
    if avatar_id:
        return f"https://sleepercdn.com/avatars/{avatar_id}"  # Sleeper avatar URL
    return "https://via.placeholder.com/150.png?text=No+Avatar"

# Function to fetch random Giphy
def fetch_random_gif(query="nfl celebration"):
    if not GIPHY_API_KEY:
        return "https://via.placeholder.com/300x200.png?text=No+GIF+Available"
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

# Function to fetch team mapping with player details
def get_team_mapping_with_players(player_data):
    try:
        league_users = get_users_in_league(league_id=LEAGUE_ID)
        league_rosters = get_rosters(league_id=LEAGUE_ID)

        user_mapping = {
            user["user_id"]: {
                "name": user.get("display_name", f"User {user['user_id']}"),
                "avatar": fetch_avatar(user.get("avatar"))
            }
            for user in league_users
        }

        team_mapping = {}
        for roster in league_rosters:
            players = [
                {
                    "player_id": player_id,
                    "details": player_data.get(player_id, {"name": "Unknown Player"})
                }
                for player_id in roster.get("players", [])
            ]
            team_mapping[roster["roster_id"]] = {
                "team_name": roster.get("metadata", {}).get(
                    "team_name",
                    user_mapping.get(roster["owner_id"], {}).get("name", f"Team {roster['roster_id']}")
                ),
                "avatar": user_mapping.get(roster["owner_id"], {}).get("avatar"),
                "players": players,
            }
        return team_mapping
    except Exception as e:
        st.error(f"Error fetching league rosters or users: {e}")
        return {}

# Function to fetch matchups for a given week
def get_matchups_with_teams(week, team_mapping):
    try:
        matchups = get_matchups_for_week(league_id=LEAGUE_ID, week=week)
        if not matchups or not isinstance(matchups, list):
            st.error(f"No valid matchups returned for week {week}.")
            return {}

        matchups_with_teams = {}
        for matchup in matchups:
            matchup_id = matchup.get('matchup_id')
            roster_id = matchup.get('roster_id')
            points = matchup.get('points', 0)

            if matchup_id is None or roster_id is None:
                continue

            team_data = team_mapping.get(roster_id, {"team_name": f"Team {roster_id}", "avatar": None})

            if matchup_id not in matchups_with_teams:
                matchups_with_teams[matchup_id] = []

            matchups_with_teams[matchup_id].append({
                'team_name': team_data["team_name"],
                'avatar': team_data["avatar"],
                'points': points
            })

        return dict(sorted(matchups_with_teams.items()))
    except Exception as e:
        st.error(f"Error fetching matchups for week {week}: {e}")
        return {}

def generate_roasts_with_players(matchups, team_mapping, is_championship=False):
    roasts = []
    for matchup_id, teams in matchups.items():
        if len(teams) == 2:
            team1, team2 = teams[0], teams[1]
            team1_roster_id = team1.get('roster_id', None)
            team2_roster_id = team2.get('roster_id', None)

            # Ensure roster IDs are valid
            team1_roster_id = team1_roster_id if isinstance(team1_roster_id, (str, int)) else None
            team2_roster_id = team2_roster_id if isinstance(team2_roster_id, (str, int)) else None

            # Extract players
            team1_players = [f"{p['details'].get('first_name', '')} {p['details'].get('last_name', '')} ({p['details'].get('position', '')})"
                             for p in team_mapping.get(team1_roster_id, {}).get("players", [])]
            team2_players = [f"{p['details'].get('first_name', '')} {p['details'].get('last_name', '')} ({p['details'].get('position', '')})"
                             for p in team_mapping.get(team2_roster_id, {}).get("players", [])]

            # Construct the prompt with player details
            prompt = (
                f"In the {'championship' if is_championship else 'regular season'} fantasy football matchup, "
                f"Team {team1['team_name']} scored {team1['points']} points, led by players: {', '.join(team1_players)}. "
                f"Team {team2['team_name']} scored {team2['points']} points, led by players: {', '.join(team2_players)}. "
                "Provide a funny and sarcastic sports commentary roast in the style of Chris Berman from ESPN."
            )
        else:
            # Handle matchups with only one team
            prompt = (
                f"Team {teams[0]['team_name']} played alone this week, scoring {teams[0]['points']} points. "
                "Write a funny roast in Chris Berman's style."
            )

        # Print the prompt for debugging purposes
        print(f"Generated prompt for matchup {matchup_id}:\n{prompt}\n")

        try:
            # Call OpenAI API to generate the roast
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are Chris Berman, a witty and funny sports commentator."},
                    {"role": "user", "content": prompt}
                ]
            )
            roast_text = response["choices"][0]["message"]["content"].strip()
            roasts.append({'matchup_id': matchup_id, 'roast': roast_text})
        except Exception as e:
            # Fallback for API errors
            roasts.append({'matchup_id': matchup_id, 'roast': f"Error generating roast: {str(e)}"})

    return roasts

# Function to display matchups with logos and scores
def display_matchup_with_logos(matchups, roasts):
    for roast in roasts:
        matchup_id = roast['matchup_id']
        roast_text = roast['roast']
        teams = matchups.get(matchup_id, [])

        if len(teams) == 2:
            home_team = teams[0]['team_name']
            away_team = teams[1]['team_name']
            home_score = teams[0]['points']
            away_score = teams[1]['points']
            home_logo = teams[0]['avatar']
            away_logo = teams[1]['avatar']

            st.markdown(f"### {home_team} ({home_score}) vs {away_team} ({away_score})")
            cols = st.columns(2)
            with cols[0]:
                if home_logo:
                    st.image(home_logo, width=100, caption=home_team)
            with cols[1]:
                if away_logo:
                    st.image(away_logo, width=100, caption=away_team)

            st.markdown(f"**Roast:** {roast_text}")
            gif_url = fetch_random_gif(query=f"nfl celebration")
            st.image(gif_url, use_column_width=True)
        else:
            st.markdown(f"### {teams[0]['team_name']} played alone")
            st.image(teams[0]['avatar'], width=100, caption=teams[0]['team_name'])
            st.markdown(f"**Roast:** {roast_text}")
            gif_url = fetch_random_gif(query=f"epic fail")
            st.image(gif_url, use_column_width=True)

# Main function to run the app
def main():
    st.title("Fantasy Football Matchup Roaster 🏈🔥")

    # Load cached player data or fetch if not present
    st.write("Checking for player data...")  # Notify in the app
    player_data = fetch_and_cache_players()

    if player_data:
        st.success("Player data loaded successfully.")  # Indicate success in the app
        print("Player data loaded successfully.")  # Log to console
    else:
        st.error("Failed to load player data. Please try again later.")
        print("Failed to load player data.")  # Log to console
        return

    # Dropdown for selecting the week
    selected_week = st.selectbox(
        "Select Week:",
        options=["Regular Season"] + [f"Week {i}" for i in range(1, 16)] + ["Championship"] + [f"Week {i}" for i in range(16, 18)]
    )

    if selected_week != "Regular Season" and selected_week != "Championship":
        week = int(selected_week.split(" ")[1])
        is_championship = week >= 16

        with st.spinner(f"Fetching data and generating roasts for {selected_week}..."):
            team_mapping = get_team_mapping_with_players(player_data)
            if team_mapping:
                matchups = get_matchups_with_teams(week, team_mapping)
                if matchups:
                    roasts = generate_roasts_with_players(matchups, team_mapping, is_championship=is_championship)
                    display_matchup_with_logos(matchups, roasts)

# Run the app
if __name__ == "__main__":
    main()