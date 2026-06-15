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
    print("🚀 [高效純數據版啟動] 正在同步：未來一週賽事 + 聯盟分區戰績表...")
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
    # 2. 抓取未來 7 天賽程 (利用 hydrate 參數，一次拿齊所有數據)
    # ----------------------------------------------------
    for i in range(0, 7):
        target_dt = today + timedelta(days=i)
        date_str = target_dt.strftime("%Y-%m-%d")
        result_data["dates"][date_str] = []
        print(f"📅 正在同步賽程與 RHE 比分：{date_str} ...")
        
        # 🌟 關鍵修正：加上 &hydrate=linescore,probablePitcher 參數，免去進 Live Feed 的必要
        sched_url = f"https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1&date={date_str}&hydrate=linescore,probablePitcher"
        sched_data = get_json(sched_url)
        
        for date_entry in sched_data.get("dates", []):
            for game in date_entry.get("games", []):
                sched_away = game.get("teams", {}).get("away", {})
                sched_home = game.get("teams", {}).get("home", {})
                
                away_slug = TEAM_ID_MAP.get(sched_away.get("team", {}).get("id")) or "TBD"
                home_slug = TEAM_ID_MAP.get(sched_home.get("team", {}).get("id")) or "TBD"
                
                # 投手資訊已經透過水合機制注入進來了
                away_p_name = sched_away.get("probablePitcher", {}).get("fullName", "未定 (TBD)")
                home_p_name = sched_home.get("probablePitcher", {}).get("fullName", "未定 (TBD)")
                
                # 比賽詳細狀態
                status_str = game.get("status", {}).get("detailedState", "Scheduled")
                if status_str in ["In Progress", "Warm-up"]:
                    status = "Live"
                elif status_str in ["Final", "Completed Early", "Game Over"]:
                    status = "Final"
                else:
                    status = "Upcoming"
                    
                # 🌟 關鍵優化：直接從 hydrated 賽程中提取 linescore 資料，不用重新戳 API
                linescore = game.get("linescore", {}).get("teams", {})
                
                # 建立安全讀取工具，防止 None 值打碎前端畫面
                def safe_get(linescore_team, key):
                    val = linescore_team.get(key)
                    return "-" if val is None else val

                away_line = linescore.get("away", {})
                home_line = linescore.get("home", {})
                
                rhe = {
                    "away": {"R": safe_get(away_line, "runs"), "H": safe_get(away_line, "hits"), "E": safe_get(away_line, "errors")},
                    "home": {"R": safe_get(home_line, "runs"), "H": safe_get(home_line, "hits"), "E": safe_get(home_line, "errors")}
                }
                
                # 處理比賽開打時間 (格式為 2026-06-15T22:10:00Z，取出時間部分)
                game_date_raw = game.get("gameDate", "")
                game_time = "--:--"
                if "T" in game_date_raw:
                    # 取出 '22:10' 這一段 UTC 時間
                    game_time = game_date_raw.split("T")[-1][:5]
                
                result_data["dates"][date_str].append({
                    "home_team": home_slug, 
                    "away_team": away_slug,
                    "status": status, 
                    "time": game_time,
                    "rhe": rhe, 
                    "pitchers": {"away_starter": away_p_name, "home_starter": home_p_name}
                })
                
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=4)
    print("🏁 [大功告成] 所有實體數據已安全、高效地寫入 data.json！")

if __name__ == "__main__":
    fetch_all_mlb_data()