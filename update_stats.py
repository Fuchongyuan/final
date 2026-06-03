import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json

current_date = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d")
scrape_url = "https://2030.tw/5g_taiwan/"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

web_scraped_metrics = {}
try:
    web_res = requests.get(scrape_url, headers=headers, timeout=10)
    if web_res.status_code == 200:
        soup = BeautifulSoup(web_res.text, 'html.parser')
        article = soup.find(class_="entry-content") or soup.find("article")
        if article:
            for row in article.find_all("tr"):
                cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                if len(cells) >= 3:
                    label = cells[0].upper()
                    metric_key = None
                    if "打擊率" in label or "AVG" in label: metric_key = "avg"
                    elif "進攻" in label or "OPS" in label: metric_key = "ops"
                    elif "上壘" in label or "OBP" in label: metric_key = "obp"
                    elif "長打" in label or "SLG" in label: metric_key = "slg"
                    elif "全壘打" in label or "HR" in label: metric_key = "hr"
                    elif "打點" in label or "RBI" in label: metric_key = "rbi"
                    elif "得分" in label or label == "R": metric_key = "r"
                    elif "防禦率" in label or "ERA" in label: metric_key = "era"
                    elif "WHIP" in label: metric_key = "whip"
                    elif "三振" in label or "SO" in label: metric_key = "so"
                    if metric_key:
                        web_scraped_metrics[metric_key] = (cells[1], cells[2])
except Exception as e:
    print(f"網頁跳過: {e}")

api_url = f"https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1&date={current_date}&hydrate=team(stats(type=season))"
formatted_matches = []

try:
    api_res = requests.get(api_url, timeout=15).json()
    games = api_res.get("dates", [{}])[0].get("games", [])
    for index, game in enumerate(games):
        away_data = game["teams"]["away"]
        home_data = game["teams"]["home"]
        
        try:
            utc_dt = datetime.strptime(game["gameDate"], "%Y-%m-%dT%H:%M:%SZ")
            display_time = (utc_dt + timedelta(hours=8)).strftime("%m/%d %H:%M")
        except:
            display_time = "進行中"

        def extract_team_stats(team_node, side_index):
            stats_dict = {"avg": ".000", "ops": ".000", "obp": ".000", "slg": ".000", "hr": "0", "rbi": "0", "r": "0", "era": "0.00", "whip": "0.00", "so": "0"}
            if "stats" in team_node:
                for sg in team_node["stats"]:
                    if sg.get("type", {}).get("displayName") == "season":
                        splits = sg.get("splits", [])
                        if splits:
                            s = splits[0].get("stat", {})
                            stats_dict.update({
                                "avg": f"{s.get('avg', 0):.3f}" if isinstance(s.get('avg'), (int,float)) else ".000",
                                "ops": f"{s.get('ops', 0):.3f}" if isinstance(s.get('ops'), (int,float)) else ".000",
                                "obp": f"{s.get('obp', 0):.3f}" if isinstance(s.get('obp'), (int,float)) else ".000",
                                "slg": f"{s.get('slg', 0):.3f}" if isinstance(s.get('slg'), (int,float)) else ".000",
                                "hr": str(s.get("homeRuns", 0)), "rbi": str(s.get("rbi", 0)), "r": str(s.get("runs", 0)),
                                "era": f"{s.get('era', 0.00):.2f}" if isinstance(s.get('era'), (int,float)) else "0.00",
                                "whip": f"{s.get('whip', 0.00):.2f}" if isinstance(s.get('whip'), (int,float)) else "0.00",
                                "so": str(s.get("strikeOuts", 0))
                            })
            for k in stats_dict.keys():
                if k in web_scraped_metrics:
                    stats_dict[k] = web_scraped_metrics[k][side_index]
            return stats_dict

        formatted_matches.append({
            "id": game.get("gamePk", index),
            "time": display_time,
            "status": game["status"]["detailedState"],
            "awayTeam": {"name": away_data["team"].get("teamName", "客隊"), "code": away_data["team"].get("fileCode", "mlb").upper(), "stats": extract_team_stats(away_data["team"], 0)},
            "homeTeam": {"name": home_data["team"].get("teamName", "主隊"), "code": home_data["team"].get("fileCode", "mlb").upper(), "stats": extract_team_stats(home_data["team"], 1)}
        })
except Exception as e:
    print(f"API 錯誤: {e}")

with open("data.json", "w", encoding="utf-8") as f:
    json.dump({"target_date": current_date, "matches": formatted_matches}, f, ensure_ascii=False, indent=2)