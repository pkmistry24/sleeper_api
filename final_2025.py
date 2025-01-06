import streamlit as st
import openai
import requests
import os
import json
import random
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

def fetch_and_cache_players():
    if os.path.exists(PLAYER_CACHE_FILE):
        try:
            with open(PLAYER_CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"Cache file corrupted. Re-fetching player data. Error: {e}")

    response = requests.get("https://api.sleeper.app/v1/players/nfl")
    if response.status_code == 200:
        player_data = response.json()
        with open(PLAYER_CACHE_FILE, "w") as f:
            json.dump(player_data, f)
        return player_data
    else:
        st.error(f"Error fetching player data: {response.status_code}")
        return {}

def fetch_avatar(avatar_id):
    if avatar_id:
        return f"https://sleepercdn.com/avatars/{avatar_id}"
    return "https://via.placeholder.com/150.png?text=No+Avatar"

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

def get_team_mapping_with_players(player_data):
    try:
        league_users = get_users_in_league(league_id=LEAGUE_ID)
        league_rosters = get_rosters(league_id=LEAGUE_ID)

        user_mapping = {
            user["user_id"]: {
                "name": user.get("display_name", f"User {user['user_id']}"),
                "avatar": fetch_avatar(user.get("avatar")),
            }
            for user in league_users
        }

        team_mapping = {}
        for roster in league_rosters:
            players = {
                player_id: {
                    "details": player_data.get(player_id, {"name": "Unknown Player"}),
                    "points": 0  # Initialize points for this player
                }
                for player_id in roster.get("players", [])
            }
            team_mapping[roster["roster_id"]] = {
                "team_name": roster.get("metadata", {}).get(
                    "team_name",
                    user_mapping.get(roster["owner_id"], {}).get("name", f"Team {roster['roster_id']}")
                ),
                "avatar": user_mapping.get(roster["owner_id"], {}).get("avatar"),
                "owner": user_mapping.get(roster["owner_id"], {}).get("name"),
                "total_points": 0,
                "players": players,
            }
        return team_mapping
    except Exception as e:
        st.error(f"Error fetching league rosters or users: {e}")
        return {}

def get_matchups_with_teams(week, team_mapping):
    try:
        matchups = get_matchups_for_week(league_id=LEAGUE_ID, week=week)
        if not matchups or not isinstance(matchups, list):
            st.error(f"No valid matchups returned for week {week}.")
            return {}

        for matchup in matchups:
            roster_id = matchup.get('roster_id')
            points = matchup.get('points', 0)
            starters = matchup.get('starters', [])

            if roster_id is None:
                continue

            team_data = team_mapping.get(roster_id)
            if team_data:
                team_data["total_points"] += points

                for player_id in starters:
                    if player_id in team_data["players"]:
                        team_data["players"][player_id]["points"] += points  # Accumulate points per player

        return team_mapping
    except Exception as e:
        st.error(f"Error fetching matchups for week {week}: {e}")
        return {}

def generate_user_recaps(team_mapping):
    recaps = []
    for roster_id, team_data in team_mapping.items():
        top_players = sorted(
            team_data["players"].items(),
            key=lambda item: item[1]["points"],
            reverse=True
        )[:3]  # Get top 3 players

        top_players_text = ", ".join(
            f"{player['details'].get('full_name', player_id)} ({player['points']} pts)"
            for player_id, player in top_players
        )

        prompt = (
            f"Fantasy Football Season Recap for {team_data['owner']}:\n"
            f"The team, {team_data['team_name']}, scored a total of {team_data['total_points']} points.\n"
            f"Top players were: {top_players_text}.\n"
            "Highlight this team's best performances and any embarrassing failures, "
            "providing a humorous season commentary in Chris Berman's style."
        )

        print(f"Generated recap prompt for {team_data['owner']}:\n{prompt}\n")

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are Chris Berman, a witty and humorous sports commentator."},
                    {"role": "user", "content": prompt}
                ]
            )
            recap_text = response["choices"][0]["message"]["content"].strip()
            recaps.append({'owner': team_data['owner'], 'recap': recap_text, 'avatar': team_data["avatar"]})
        except Exception as e:
            recaps.append({'owner': team_data['owner'], 'recap': f"Error generating recap: {str(e)}", 'avatar': team_data["avatar"]})

    return recaps

def display_user_recaps(recaps):
    for recap in recaps:
        st.markdown(f"### Season Recap for {recap['owner']}")
        if recap['avatar']:
            st.image(recap['avatar'], width=100)
        st.markdown(recap['recap'])
        gif_url = fetch_random_gif(query=f"nfl celebration")
        st.image(gif_url, use_column_width=True)

def main():
    st.title("Fantasy Football User Season Recaps 🏈🔥")

    st.write("Checking for player data...")
    player_data = fetch_and_cache_players()

    if player_data:
        st.success("Player data loaded successfully.")
        print("Player data loaded successfully.")

        team_mapping = get_team_mapping_with_players(player_data)
        for week in range(1, 18):
            get_matchups_with_teams(week, team_mapping)

        with st.spinner("Generating recaps for all users..."):
            user_recaps = generate_user_recaps(team_mapping)
            display_user_recaps(user_recaps)
    else:
        st.error("Failed to load player data. Please try again later.")
        print("Failed to load player data.")
        
if __name__ == "__main__":
    main()