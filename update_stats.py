import json
import urllib.request
import os
from datetime import datetime, timedelta, timezone

TEAM_ID_MAP = {
    108: "LAA", 109: "AZ",  110: "BAL", 111: "BOS", 112: "CHC",
    113: "CIN", 114: "CLE", 115: "COL", 116: "DET", 117: "HOU",
    118: "KC",  119: "LAD", 120: "WSH", 121: "NYM", 133: "OAK",
    134: "PIT", 135: "SD",  136: "SEA", 137: "SF",  138: "STL",
    139: "TB",  140: "TEX", 141: "TOR", 142: "MIN", 143: "PHI",
    144: "ATL", 145: "CWS", 146: "MIA", 147: "NYY", 158: "MIL"
}

def get_json(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"抓取失敗 {url}: {e}")
        return {}

def fetch_games_only():
    print("🚀 正在單獨同步：未來一週賽事與即時比分...")
    tz_tw = timezone(timedelta(hours=8))
    today = datetime.now(tz_tw)
    
    # 安全讀取現有資料，避免覆蓋排名
    if os.path.exists("data.json"):
        try:
            with open("data.json", "r", encoding="utf-8") as f:
                result_data = json.load(f)
        except:
            result_data = {"meta": {}, "dates": {}, "standings": {}}
    else:
        result_data = {"meta": {}, "dates": {}, "standings": {}}
        
    result_data["meta"]["last_updated"] = today.strftime("%Y-%m-%d %H:%M:%S")
    result_data["dates"] = {} # 清空舊賽事，重新填入
    
    for i in range(0, 7):
        target_dt = today + timedelta(days=i+1)
        date_str = target_dt.strftime("%Y-%m-%d")
        result_data["dates"][date_str] = []
        
        sched_url = f"https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1&date={date_str}"
        sched_data = get_json(sched_url)
        
        for date_entry in sched_data.get("dates", []):
            for game in date_entry.get("games", []):
                game_pk = game.get("gamePk")
                detail_url = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/feed/live"
                game_data = get_json(detail_url)
                
                game_info = game_data.get("gameData", {})
                live_info = game_data.get("liveData", {})
                players = game_info.get("players", {})
                
                matchup = game_info.get("probablePitchers", {})
                away_p_id = matchup.get("away", {}).get("id")
                home_p_id = matchup.get("home", {}).get("id")
                
                away_p_name = players.get(f"ID{away_p_id}", {}).get("fullName", "未定 (TBD)") if away_p_id else "未定 (TBD)"
                home_p_name = players.get(f"ID{home_p_id}", {}).get("fullName", "未定 (TBD)") if home_p_id else "未定 (TBD)"
                
                away_team_id = game_info.get("teams", {}).get("away", {}).get("id")
                home_team_id = game_info.get("teams", {}).get("home", {}).get("id")
                away_slug = TEAM_ID_MAP.get(away_team_id, "TBD")
                home_slug = TEAM_ID_MAP.get(home_team_id, "TBD")
                
                status_str = game_info.get("status", {}).get("detailedState", "Scheduled")
                status = "Live" if status_str in ["In Progress", "Warm-up"] else ("Final" if status_str in ["Final", "Completed Early", "Game Over"] else "Upcoming")
                    
                linescore = live_info.get("linescore", {}).get("teams", {})
                rhe = {
                    "away": {"R": linescore.get("away", {}).get("runs", "-"), "H": linescore.get("away", {}).get("hits", "-"), "E": linescore.get("away", {}).get("errors", "-")},
                    "home": {"R": linescore.get("home", {}).get("runs", "-"), "H": linescore.get("home", {}).get("hits", "-"), "E": linescore.get("home", {}).get("errors", "-")}
                }
                
                result_data["dates"][date_str].append({
                    "home_team": home_slug, "away_team": away_slug,
                    "status": status, "time": game_info.get("datetime", {}).get("time", "--:--"),
                    "rhe": rhe, "pitchers": {"away_starter": away_p_name, "home_starter": home_p_name}
                })
                
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=4)
    print("🏁 賽事數據同步完成！")

if __name__ == "__main__":
    fetch_games_only()