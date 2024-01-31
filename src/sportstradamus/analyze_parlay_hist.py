import pandas as pd
import numpy as np
import os.path
import json
from datetime import datetime, timedelta
import importlib.resources as pkg_resources
from sportstradamus import data, creds
from sportstradamus.stats import StatsNBA, StatsMLB, StatsNHL, StatsNFL
from tqdm import tqdm
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import gspread

def reflect():
    # Authorize the gspread API
    SCOPES = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file",
    ]
    cred = None

    # Check if token.json file exists and load credentials
    if os.path.exists((pkg_resources.files(creds) / "token.json")):
        cred = Credentials.from_authorized_user_file(
            (pkg_resources.files(creds) / "token.json"), SCOPES
        )

    # If no valid credentials found, let the user log in
    if not cred or not cred.valid:
        if cred and cred.expired and cred.refresh_token:
            cred.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                (pkg_resources.files(creds) / "credentials.json"), SCOPES
            )
            cred = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open((pkg_resources.files(creds) / "token.json"), "w") as token:
            token.write(cred.to_json())

    gc = gspread.authorize(cred)

    tqdm.pandas()
    payout_table = {
        "Underdog": [(1, 1),
                    (1, 1),
                    (3, 0, 0),
                    (6, 0, 0, 0),
                    (6, 1.5, 0, 0, 0),
                    (10, 2.5, 0, 0, 0, 0)],
        "PrizePicks": [(1, 1),
                    (1, 1),
                    (3, 0, 0),
                    (2.25, 1.25, 0, 0),
                    (10, 0, 0, 0, 0),
                    (10, 2, 0.4, 0, 0, 0),
                    (25, 2, 0.4, 0, 0, 0, 0)]
    }

    nba = StatsNBA()
    nba.load()
    nba.update()
    mlb = StatsMLB()
    mlb.load()
    mlb.update()
    nhl = StatsNHL()
    nhl.load()
    nhl.update()
    nfl = StatsNFL()
    nfl.load()
    nfl.update()

    stats = {"NBA": nba, "MLB": mlb, "NHL": nhl, "NFL": nfl}

    nameStr = {"MLB": "playerName", "NBA": "PLAYER_NAME",
                "NFL": "player display name", "NHL": "playerName"}
    dateStr = {"MLB": "gameDate", "NBA": "GAME_DATE",
                "NFL": "gameday", "NHL": "gameDate"}
    teamStr = {"MLB": "team", "NBA": "TEAM_ABBREVIATION",
                "NFL": "recent team", "NHL": "team"}

    with open((pkg_resources.files(data) / "stat_map.json"), "r") as infile:
        stat_map = json.load(infile)

    filepath = pkg_resources.files(data) / "parlay_hist.dat"
    if os.path.isfile(filepath):
        parlays_clean = pd.read_pickle(filepath)

    parlays = parlays_clean.copy()

    def check_bet(bet):
        new_map = stat_map[bet.Platform]
        if bet.League == "NHL":
            new_map.update({
                "Points": "points",
                "Blocked Shots": "blocked",
                "Assists": "assists"
            })
        if bet.League == "NBA":
            new_map.update({
                "Fantasy Points": "fantasy points prizepicks",
                "Points": "PTS",
                "Blocked Shots": "BLK",
                "Assists": "AST"
            })
        gamelog = stats[bet.League].gamelog
        gamelog[dateStr[bet.League]] = gamelog[dateStr[bet.League]].str[:10]
        game = gamelog.loc[(gamelog[dateStr[bet.League]]==bet.Date) & (gamelog[teamStr[bet.League]].isin(bet.Game.split('/')))]
        if game.empty:
            return np.nan, np.nan
        else:
            legs = 0
            misses = 0
            for leg in bet:
                if isinstance(leg, str) and "%" in leg:
                    legs += 1
                    if " Under " in leg:
                        split_leg = leg.split(" Under ")
                        over = False
                    else:
                        split_leg = leg.split(" Over ")
                        over = True
                    player = split_leg[0]
                    rest = split_leg[1].split(" - ")[0]
                    line = rest.split(" ")[0]
                    market = rest[(len(line)+1):].replace("H2H ", "")
                    line = float(line)
                    market = new_map.get(market, market)

                    if " + " in player:
                        players = player.split(" + ")
                        result1 = game.loc[game[nameStr[bet.League]] == players[0], market]
                        result2 = game.loc[game[nameStr[bet.League]] == players[1], market]
                        if result1.empty or result2.empty:
                            result = result1
                        else:
                            result = pd.Series(result1.iat[0] + result2.iat[0])
                    elif " vs. " in player:
                        players = player.split(" vs. ")
                        result1 = game.loc[game[nameStr[bet.League]] == players[0], market]
                        result2 = game.loc[game[nameStr[bet.League]] == players[1], market]
                        if result1.empty or result2.empty:
                            result = result1
                        else:
                            result = pd.Series(result1.iat[0] + result2.iat[0])
                    else:
                        result = game.loc[game[nameStr[bet.League]] == player, market]

                    if result.empty:
                        legs -= 1
                    elif result.iat[0] == line:
                        legs -= 1
                    elif result.iat[0] < line and over:
                        misses += 1
                    elif result.iat[0] > line and not over:
                        misses += 1

            return legs, misses

    parlays.loc[parlays.Legs.isna(), ["Legs", "Misses"]] = parlays.loc[parlays.Legs.isna()].progress_apply(check_bet, axis=1).to_list()
    parlays.dropna(subset=['Legs'], inplace=True)
    parlays[["Legs", "Misses"]] = parlays[["Legs", "Misses"]].astype(int)
    parlays["Profit"] = parlays.apply(lambda x: np.clip(payout_table[x.Platform][x.Legs][x.Misses]*(x.Boost if x.Boost < 2 or x.Misses==0 else 1),None,100)-1, axis=1)
    parlays["Profit"] = parlays["Profit"]*parlays["Rec Bet"]

    pd.concat([parlays, parlays_clean]).drop_duplicates(subset=parlays.columns[:-3]).to_pickle(filepath)

    parlays.loc[parlays["Model EV"] >= 6, "Model EV"] = 5.99

    profits = {}
    masks = {}

    for platform in payout_table.keys():
        platform_df = parlays.loc[parlays["Platform"] == platform]
        for league in ["All", "NBA", "NFL", "NHL", "MLB"]:
            if league == "All":
                league_df = platform_df
            else:
                league_df = platform_df.loc[platform_df["League"] == league]

            if not league_df.empty:
                profits.setdefault(f"{platform}, {league}", {})

                if platform == "Underdog":
                    n = .01
                    # mean_profit = np.zeros([int(1/n), int(5/n)])
                    # for i, bt in enumerate(tqdm(np.arange(1, 2, n))):
                    #     for j, mt in enumerate(np.arange(1, 6, n)):
                    #         test_df = league_df.loc[(league_df["Books EV"] > bt) & (league_df["Model EV"] > mt)]
                    #         bets = test_df.sort_values("Model EV", ascending=False).groupby(["Game", "Date"]).apply(lambda x: x.Profit.head(5).mean())
                    #         if len(bets):
                    #             mean_profit[i, j] = bets.sum()
                            
                    # model_threshold = np.argmax((mean_profit-np.nanmean(mean_profit))/np.nanstd(mean_profit) >= 1, axis=1)*n+1
                    # book_threshold = np.arange(1,2,n)
                    # book_threshold = book_threshold[model_threshold > 1]
                    # model_threshold = model_threshold[model_threshold > 1]
                    # p = np.polyfit(np.log(6-model_threshold), book_threshold, 1)
                    # masks[league] = list(p)

            for tf, days in [("Last Week", 7), ("Last Month", 30), ("Three Months", 91), ("Six Months", 183), ("Last Year", 365)]:
                df = league_df.loc[pd.to_datetime(league_df.Date).dt.date > datetime.today().date() - timedelta(days=days)]

                if not df.empty:
                    profits[f"{platform}, {league}"][tf] = df.sort_values("Model EV", ascending=False).groupby(["Game", "Date"]).apply(lambda x: x.Profit.head(5).mean()).sum()

    # filepath = pkg_resources.files(data) / "parlay_masks.json"
    # with open(filepath, 'w') as of:
    #     json.dump(masks, of, indent=4)

    profits = pd.DataFrame(profits).T.reset_index(names='Split')
    wks = gc.open("Sportstradamus").worksheet("Parlay Profit")
    wks.clear()
    wks.update([profits.columns.values.tolist()] +
            profits.values.tolist())
    
if __name__ == "__main__":
    reflect()