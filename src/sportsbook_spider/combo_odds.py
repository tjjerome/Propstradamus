from sportsbook_spider.stats import statsNBA
from sportsbook_spider.helpers import archive, get_ev
from datetime import datetime, timedelta
import numpy as np
from scipy.stats import poisson

nba = statsNBA()
nba.load()
nba.update()

markets = ['BLK', 'STL']
new_market = 'BLST'
Date = datetime.strptime('2022-10-18T12:00:00Z', "%Y-%m-%dT%H:%M:%SZ")

while Date < datetime.strptime('2023-05-26', '%Y-%m-%d'):
    date = Date.strftime("%Y-%m-%d")
    print(date)
    Date = Date + timedelta(days=1)
    market = markets[0]
    # and (not archive['NBA'].get(new_market, {}).get(date)):
    if archive['NBA'][market].get(date):
        players = archive['NBA'][market][date]
        for player, offer in players.items():
            EV = []
            ev = []
            for line, stats in offer.items():
                over = np.mean(
                    [i for i in stats[-4:] if not i == -1000])
                ev.append(get_ev(line, 1-over))
            EV.append(np.mean(ev))
            for market in markets[1:]:
                offer1 = archive['NBA'][market][date].get(player)
                if offer1 is None:
                    EV.append(0)
                    continue
                ev = []
                for line, stats in offer1.items():
                    over = np.mean(
                        [i for i in stats[-4:] if not i == -1000])
                    ev.append(get_ev(line, 1-over))
                EV.append(np.mean(ev))
            if not np.prod(EV) == 0:
                EV = np.sum(EV)
                line = np.round(EV-0.5)+0.5
                over = poisson.sf(np.floor(line), EV)
                stats = np.append(np.zeros(5), [over]*4)
                if date not in archive.archive['NBA'][new_market]:
                    archive.archive['NBA'][new_market][date] = {}
                archive.archive['NBA'][new_market][date][player] = {
                    line: stats}

archive.write()
