import json
import urllib.request
import os
from datetime import datetime, timedelta, timezone

# 備用球隊字典
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
    
    # 安全讀取
    if os.path.exists("data.json"):
        try:
            with open("data.json", "r", encoding="utf-8") as f:
                result_data = json.load(f)
        except:
            result_data = {"meta": {}, "dates": {}, "standings": {}}
    else:
        result_data = {"meta": {}, "dates": {}, "standings": {}}
        
    result_data["meta"]["last_updated"] = today.strftime("%Y-%m-%d %H:%M:%S")
    result_data["dates"] = {} 
    
    for i in range(0, 7):
        target_dt = today + timedelta(days=i+1)
        date_str = target_dt.strftime("%Y-%m-%d")
        result_data["dates"][date_str] = []
        
        sched_url = f"https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1&date={date_str}"
        sched_data = get_json(sched_url)
        
        for date_entry in sched_data.get("dates", []):
            for game in date_entry.get("games", []):
                
                # --- 🌟 終極修正：直接從 Schedule 層面攔截資料，絕不依賴 Live 空白節點 ---
                sched_away = game.get("teams", {}).get("away", {})
                sched_home = game.get("teams", {}).get("home", {})
                
                away_team_id = sched_away.get("team", {}).get("id")
                home_team_id = sched_home.get("team", {}).get("id")
                
                # 1. 解析球隊：自訂 Map 優先 -> API 全名 -> TBD
                away_slug = TEAM_ID_MAP.get(away_team_id) or sched_away.get("team", {}).get("name", "TBD")
                home_slug = TEAM_ID_MAP.get(home_team_id) or sched_home.get("team", {}).get("name", "TBD")
                
                # 2. 解析投手：從 Schedule 直接拿，這是大聯盟官方最準確的預告
                away_p_name = sched_away.get("probablePitcher", {}).get("fullName", "TBD")
                home_p_name = sched_home.get("probablePitcher", {}).get("fullName", "TBD")
                
                # 3. 抓取 Live 資料（只為了拿即時比分 RHE 和狀態）
                game_pk = game.get("gamePk")
                detail_url = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/feed/live"
                game_data = get_json(detail_url)
                
                game_info = game_data.get("gameData", {})
                live_info = game_data.get("liveData", {})
                
                status_str = game_info.get("status", {}).get("detailedState") or game.get("status", {}).get("detailedState", "Scheduled")
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
    print("🏁 賽事數據同步完成！(終極無敵防 TBD 版)")

if __name__ == "__main__":
    fetch_games_only()