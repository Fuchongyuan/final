import json
import urllib.request
import os
import ssl
from datetime import datetime, timedelta, timezone

# 強制略過雲端環境可能遇到的 SSL 憑證阻擋
ssl_context = ssl._create_unverified_context()

# 🌟 球隊 ID 對照表
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
    print("🚀 [終極事實數據版啟動] 正在同步大聯盟數據...")
    tz_tw = timezone(timedelta(hours=8)) # 台灣時區
    today = datetime.now(tz_tw)
    
    result_data = {
        "meta": {"last_updated": today.strftime("%Y-%m-%d %H:%M:%S")},
        "dates": {},
        "standings": {
            "AL": {"East": [], "Central": [], "West": []},
            "NL": {"East": [], "Central": [], "West": []}
        }
    }
    
    # 預先建立台灣時間未來 7 天的賽程容器
    for i in range(0, 7):
        d_str = (today + timedelta(days=i)).strftime("%Y-%m-%d")
        result_data["dates"][d_str] = []
    
    # ----------------------------------------------------
    # 1. 抓取分區戰績排名 (Standings)
    # ----------------------------------------------------
    print("📊 正在同步最新聯盟戰績表...")
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
        print("✅ 戰績表同步完成！")

    # ----------------------------------------------------
    # 2. 抓取賽程 (多抓前後各一天，以防時區轉換跨日掉賽事)
    # ----------------------------------------------------
    print("📅 正在同步賽事、精準開賽時間與 RHE 即時比分...")
    start_fetch_date = today - timedelta(days=1)
    
    for i in range(0, 9):
        us_target = start_fetch_date + timedelta(days=i)
        us_date_str = us_target.strftime("%Y-%m-%d")
        
        # 透過水合機制把 linescore(比分) 和 probablePitcher(先發) 一次打包，拒絕被封鎖 IP
        sched_url = f"https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1&date={us_date_str}&hydrate=linescore,probablePitcher"
        sched_data = get_json(sched_url)
        
        for date_entry in sched_data.get("dates", []):
            for game in date_entry.get("games", []):
                
                # 處理比賽開打時間 (將大聯盟標準 UTC 轉為台灣當地時間)
                game_date_raw = game.get("gameDate", "")
                if not game_date_raw: continue
                
                try:
                    utc_dt = datetime.strptime(game_date_raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                    tw_dt = utc_dt.astimezone(tz_tw)
                    tw_date_str = tw_dt.strftime("%Y-%m-%d") # 這是台灣當地的開賽日期
                    tw_time_str = tw_dt.strftime("%H:%M")    # 這是台灣當地的開賽時間
                except Exception:
                    continue
                
                # 如果這場比賽的台灣日期不在我們前端要顯示的 7 天內，就跳過
                if tw_date_str not in result_data["dates"]:
                    continue
                
                # 檢查防重機制
                if any(g["game_pk"] == game.get("gamePk") for g in result_data["dates"][tw_date_str]):
                    continue

                sched_away = game.get("teams", {}).get("away", {})
                sched_home = game.get("teams", {}).get("home", {})
                
                away_slug = TEAM_ID_MAP.get(sched_away.get("team", {}).get("id")) or "TBD"
                home_slug = TEAM_ID_MAP.get(sched_home.get("team", {}).get("id")) or "TBD"
                
                away_p_name = sched_away.get("probablePitcher", {}).get("fullName", "未定 (TBD)")
                home_p_name = sched_home.get("probablePitcher", {}).get("fullName", "未定 (TBD)")
                
                # 狀態分流解析
                status_str = game.get("status", {}).get("detailedState", "Scheduled")
                if status_str in ["In Progress", "Warm-up", "Delayed Start", "Delayed"]:
                    status = "Live"
                elif status_str in ["Final", "Completed Early", "Game Over"]:
                    status = "Final"
                else:
                    status = "Upcoming"
                    
                # 提取 R, H, E
                linescore = game.get("linescore", {}).get("teams", {})
                def safe_get(team_node, key):
                    val = team_node.get(key)
                    return "-" if val is None else val

                away_line = linescore.get("away", {})
                home_line = linescore.get("home", {})
                
                rhe = {
                    "away": {"R": safe_get(away_line, "runs"), "H": safe_get(away_line, "hits"), "E": safe_get(away_line, "errors")},
                    "home": {"R": safe_get(home_line, "runs"), "H": safe_get(home_line, "hits"), "E": safe_get(home_line, "errors")}
                }
                
                result_data["dates"][tw_date_str].append({
                    "game_pk": game.get("gamePk"),
                    "home_team": home_slug, 
                    "away_team": away_slug,
                    "status": status, 
                    "time": tw_time_str, # 完美的台灣時間 24H 制 (例: 07:10, 10:15)
                    "rhe": rhe, 
                    "pitchers": {"away_starter": away_p_name, "home_starter": home_p_name}
                })
                
    # 寫入檔案
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=4)
    print("🏁 [大功告成] 資料庫成功重組，數據皆為台灣時間！")

if __name__ == "__main__":
    fetch_all_mlb_data()