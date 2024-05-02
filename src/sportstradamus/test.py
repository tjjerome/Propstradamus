from sportstradamus.stats import StatsNBA, StatsMLB, StatsNFL, StatsNHL
from sportstradamus.helpers import scraper, archive, stat_cv
from urllib.parse import urlencode
from datetime import datetime, timedelta
import importlib.resources as pkg_resources
from sportstradamus import data
import pickle
import json
from scipy.stats import norm, poisson
import pandas as pd
import numpy as np
from tqdm import tqdm
from time import time
import requests

NBA = StatsNBA()
# NBA.load()
NBA.season = "2021-22"
NBA.season_start = datetime(2021, 10, 1).date()
NBA.update()
NBA.season = "2022-23"
NBA.season_start = datetime(2022, 10, 1).date()
NBA.update()
NBA.season = "2023-24"
NBA.season_start = datetime(2023, 10, 1).date()
NBA.update()
NBA.update_player_comps()
NBA.load()

markets = ["fantasy points prizepicks", "PTS", "REB", "AST", "TOV", "BLK", "STL", "MIN"]

gamelog = NBA.gamelog.loc[pd.to_datetime(NBA.gamelog["GAME_DATE"]).dt.date > (datetime.today().date() - timedelta(days=300))]

gameRecords = []
gameRecords1 = []
gameRecords2 = []
for i, game in tqdm(gamelog.iterrows(), desc="Checking Player Comps", total=len(gamelog)):
    gameDate = pd.to_datetime(game["GAME_DATE"]).date()
    dateMask = (pd.to_datetime(NBA.gamelog["GAME_DATE"]).dt.date > (gameDate - timedelta(days=300))) & (pd.to_datetime(NBA.gamelog["GAME_DATE"]).dt.date < gameDate)

    defenseGames = NBA.gamelog.loc[dateMask & (NBA.gamelog["OPP"]==game["OPP"])]
    defenseAvg = defenseGames[markets].mean()
    defenseStd = defenseGames[markets].std()
    compGames = defenseGames.loc[defenseGames["PLAYER_NAME"].isin(NBA.comps[game["POS"]].get(game["PLAYER_NAME"], []))]

    compResult = ((compGames[markets].mean()-defenseAvg)/defenseStd).to_dict()
    gameResult = ((game[markets]-defenseAvg)/defenseStd).to_dict()
    gameResult.update({"comp_"+k:v for k, v in compResult.items()})
    gameRecords.append(gameResult)
    
    playerGames = NBA.gamelog.loc[dateMask & NBA.gamelog["PLAYER_NAME"].isin(NBA.comps[game["POS"]].get(game["PLAYER_NAME"], []))]
    playerAvg = playerGames[markets].mean()
    playerStd = playerGames[markets].std().replace(0,0.5)
    compResult = ((compGames[markets].mean()-playerAvg)/playerStd).to_dict()
    playerGames = NBA.gamelog.loc[dateMask & (NBA.gamelog["PLAYER_NAME"]==game["PLAYER_NAME"])]
    playerAvg = playerGames[markets].mean()
    playerStd = playerGames[markets].std().replace(0,0.5)
    gameResult = ((game[markets]-playerAvg)/playerStd).to_dict()
    gameResult.update({"comp_"+k:v for k, v in compResult.items()})
    gameRecords1.append(gameResult)
    
    compResult = compGames[markets].mean().to_dict()
    gameResult = game[markets].to_dict()
    gameResult.update({"comp_"+k:v for k, v in compResult.items()})
    gameRecords2.append(gameResult)

game_df = pd.DataFrame(gameRecords)
C1 = game_df.corr()
game_df = pd.DataFrame(gameRecords1)
C2 = game_df.corr()
game_df = pd.DataFrame(gameRecords2)
C3 = game_df.corr()
C = pd.DataFrame([{market: C1.loc[market, "comp_"+market] for market in markets},
                  {market: C2.loc[market, "comp_"+market] for market in markets},
                  {market: C3.loc[market, "comp_"+market] for market in markets}])
print(C)

# filepath = pkg_resources.files(data) / "banned_combos.json"
# with open(filepath, "r") as infile:
#     banned = json.load(infile)

# platform = "Underdog"
# league = "NHL" 
# for market in list(banned[platform][league]["modified"].keys()):
#     for submarket in list(banned[platform][league]["modified"][market].keys()):
#         a = submarket.split(".")
#         if a[0] == "C":
#             banned[platform][league]["modified"][market][".".join(["R", a[1]])] = banned[platform][league]["modified"][market][submarket]
#             banned[platform][league]["modified"][market][".".join(["L", a[1]])] = banned[platform][league]["modified"][market][submarket]
#         elif a[0] == "_OPP_C":
#             banned[platform][league]["modified"][market][".".join(["_OPP_R", a[1]])] = banned[platform][league]["modified"][market][submarket]
#             banned[platform][league]["modified"][market][".".join(["_OPP_L", a[1]])] = banned[platform][league]["modified"][market][submarket]
    
#     a = market.split(".")
#     if a[0] == "C":
#         banned[platform][league]["modified"][".".join(["R", a[1]])] = banned[platform][league]["modified"][market]
#         banned[platform][league]["modified"][".".join(["L", a[1]])] = banned[platform][league]["modified"][market]

# for platform in banned.keys():
#     for league in list(banned[platform].keys()):
#         if "modified" in list(banned[platform][league].keys()):
#             for market in list(banned[platform][league]["modified"].keys()):
#                 for submarket in list(banned[platform][league]["modified"][market].keys()):
#                     market2 = market
#                     submarket2 = submarket
#                     if "_OPP_" in submarket:
#                         market2 = "_OPP_"+market2
#                         submarket2 = submarket2.replace("_OPP_", "")
#                     banned[platform][league]["modified"].setdefault(submarket2, {})
#                     banned[platform][league]["modified"][submarket2][market2] = banned[platform][league]["modified"][market][submarket]

# with open(filepath, "w") as outfile:
#     json.dump(banned, outfile, indent=4)

# NFL = StatsNFL()
# NFL.season_start = datetime(2018, 9, 1).date()
# NFL.update()
# NFL.season_start = datetime(2019, 9, 1).date()
# NFL.update()
# NFL.season_start = datetime(2020, 9, 1).date()
# NFL.update()
# NFL.season_start = datetime(2021, 9, 1).date()
# NFL.update()
# NFL.season_start = datetime(2022, 9, 1).date()
# NFL.update()
# NFL.season_start = datetime(2023, 9, 1).date()
# NFL.update()

# NBA = StatsNBA()
# NBA.load()
# NBA.update()
# NBA.profile_market("BLST")
# stat=NBA.get_stats({
#     "Player": "Tim Hardaway",
#     "Market": "BLST",
#     "Line": 0.5,
#     "Date": datetime(2024, 3, 19).date(),
#     "Team": "DAL",
#     "Opponent": "SAS",
#     "League": "NBA"
# })
# pass
# NBA.season = "2021-22"
# NBA.season_start = datetime(2021, 10, 1).date()
# NBA.update()
# NBA.season = "2022-23"
# NBA.season_start = datetime(2022, 10, 1).date()
# NBA.update()
# NBA.season = "2023-24"
# NBA.season_start = datetime(2023, 10, 1).date()
# NBA.update()

# NHL = StatsNHL()
# NHL.season_start = datetime(2021, 10, 12).date()
# NHL.update()
# NHL.season_start = datetime(2022, 10, 7).date()
# NHL.update()
# NHL.season_start = datetime(2023, 10, 10).date()
# NHL.update()

# MLB = StatsMLB()
# MLB.load()
# MLB.gamelog = pd.DataFrame()
# MLB.teamlog = pd.DataFrame()
# MLB.season_start = datetime(2021, 3, 1).date()
# MLB.update()
# MLB.update()
# MLB.update()
# MLB.update()
# MLB.season_start = datetime(2022, 3, 1).date()
# MLB.update()
# MLB.update()
# MLB.update()
# MLB.update()
# MLB.season_start = datetime(2023, 3, 30).date()
# MLB.update()
# MLB.update()
# MLB.update()
# MLB.update()
