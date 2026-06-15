import json
import urllib.request
import os
import ssl
from datetime import datetime, timedelta, timezone

# 強制略過雲端環境可能遇到的 SSL 憑證阻擋
ssl_context = ssl._create_unverified_context()

# 🌟 球隊 ID 對照表（防錯對應）
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
        with urllib.request.urlopen(req, context=ssl_context, timeout=12) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"❌ 抓取失敗 {url}: {e}")
        return {}

def fetch_all_mlb_data():
    print("🚀 [純數據版啟動] 正在同步：未來一週賽事 + 聯盟分區戰績表...")
    tz_tw = timezone(timedelta(hours=8))
    today = datetime.now(tz_tw)
    
    # 建立純數據的 JSON 結構
    result_data = {
        "meta": {"last_updated": today.strftime("%Y-%m-%d %H:%M:%S")},
        "dates": {},
        "standings": {
            "AL": {"East": [], "Central": [], "West": []},
            "NL": {"East": [], "Central": [], "West": []}
        }
    }
    
    # ----------------------------------------------------
    # 1. 抓取分區戰績排名 (Standings)
    # ----------------------------------------------------
    print("📊 正在向大聯盟 API 索取最新聯盟戰績表...")
    standings_url = "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104"
    st_data = get_json(standings_url)
    
    if st_data:
        for record in st_data.get("records", []):
            div_name = record.get("division", {}).get("name", "")
            league = "AL" if "American" in div_name else "NL"
            
            if "East" in div_name: div_key = "East"
            elif "Central" in div_name: div_key = "Central"
            elif "West" in div_name: div_key = "West"
            else: continue
            
            for tr in record.get("teamRecords", []):
                t_id = tr.get("team", {}).get("id")
                t_slug = TEAM_ID_MAP.get(t_id) or tr.get("team", {}).get("name", "TBD")
                
                result_data["standings"][league][div_key].append({
                    "team": t_slug,
                    "W": tr.get("wins", 0),
                    "L": tr.get("losses", 0),
                    "PCT": tr.get("winningPercentage", ".000"),
                    "GB": tr.get("gamesBack", "-")
                })
        print("✅ 戰績表解析完成！")

    # ----------------------------------------------------
    # 2. 抓取未來 7 天賽程 (包含今天與即時比分 RHE)
    # ----------------------------------------------------
    for i in range(0, 7):
        target_dt = today + timedelta(days=i)
        date_str = target_dt.strftime("%Y-%m-%d")
        result_data["dates"][date_str] = []
        print(f"📅 正在同步賽程與 RHE 比分：{date_str} ...")
        
        sched_url = f"https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1&date={date_str}"
        sched_data = get_json(sched_url)
        
        for date_entry in sched_data.get("dates", []):
            for game in date_entry.get("games", []):
                sched_away = game.get("teams", {}).get("away", {})
                sched_home = game.get("teams", {}).get("home", {})
                
                away_slug = TEAM_ID_MAP.get(sched_away.get("team", {}).get("id")) or "TBD"
                home_slug = TEAM_ID_MAP.get(sched_home.get("team", {}).get("id")) or "TBD"
                
                away_p_name = sched_away.get("probablePitcher", {}).get("fullName", "未定 (TBD)")
                home_p_name = sched_home.get("probablePitcher", {}).get("fullName", "未定 (TBD)")
                
                # 抓取 Live 細節 (拿即時比分 R, H, E 與比賽狀態)
                game_pk = game.get("gamePk")
                detail_url = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/feed/live"
                game_data = get_json(detail_url)
                
                game_info = game_data.get("gameData", {})
                live_info = game_data.get("liveData", {})
                
                status_str = game_info.get("status", {}).get("detailedState") or game.get("status", {}).get("detailedState", "Scheduled")
                if status_str in ["In Progress", "Warm-up"]:
                    status = "Live"
                elif status_str in ["Final", "Completed Early", "Game Over"]:
                    status = "Final"
                else:
                    status = "Upcoming"
                    
                linescore = live_info.get("linescore", {}).get("teams", {})
                rhe = {
                    "away": {"R": linescore.get("away", {}).get("runs", "-"), "H": linescore.get("away", {}).get("hits", "-"), "E": linescore.get("away", {}).get("errors", "-")},
                    "home": {"R": linescore.get("home", {}).get("runs", "-"), "H": linescore.get("home", {}).get("hits", "-"), "E": linescore.get("home", {}).get("errors", "-")}
                }
                
                result_data["dates"][date_str].append({
                    "home_team": home_slug, 
                    "away_team": away_slug,
                    "status": status, 
                    "time": game_info.get("datetime", {}).get("time", "--:--"),
                    "rhe": rhe, 
                    "pitchers": {"away_starter": away_p_name, "home_starter": home_p_name}
                })
                
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=4)
    print("🏁 [大功告成] 所有實體數據已成功寫入 data.json！")

if __name__ == "__main__":
    fetch_all_mlb_data()