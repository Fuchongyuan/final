import json
import urllib.request
import ssl
from datetime import datetime, timedelta
import traceback

# 💡 強制略過 SSL 憑證驗證，避免 Python 在某些伺服器/本機環境下默默抓不到數據
ssl_context = ssl._create_unverified_context()

# 💡 這是你專屬設計的 mlbmap (縮寫對照表)
mlbmap = {
    "Arizona Diamondbacks": "AZ", "Atlanta Braves": "ATL", "Baltimore Orioles": "BAL",
    "Boston Red Sox": "BOS", "Chicago Cubs": "CHC", "Chicago White Sox": "CWS",
    "Cincinnati Reds": "CIN", "Cleveland Guardians": "CLE", "Colorado Rockies": "COL",
    "Detroit Tigers": "DET", "Houston Astros": "HOU", "Kansas City Royals": "KC",
    "Los Angeles Angels": "LAA", "Los Angeles Dodgers": "LAD", "Miami Marlins": "MIA",
    "Milwaukee Brewers": "MIL", "Minnesota Twins": "MIN", "New York Mets": "NYM",
    "New York Yankees": "NYY", "Oakland Athletics": "OAK", "Philadelphia Phillies": "PHI",
    "Pittsburgh Pirates": "PIT", "San Diego Padres": "SD", "San Francisco Giants": "SF",
    "Seattle Mariners": "SEA", "St. Louis Cardinals": "STL", "Tampa Bay Rays": "TB",
    "Texas Rangers": "TEX", "Toronto Blue Jays": "TOR", "Washington Nationals": "WSH"
}

def get_json(url):
    """ 強健版的 JSON 抓取器，帶有詳細錯誤報告 """
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ssl_context, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"❌ API 抓取失敗: {url}\n⚠️ 錯誤原因: {str(e)}")
        return {}

def fetch_mlb_dashboard_data():
    print("🚀 [啟動] 正在執行 MLB 數據抓取引擎 (帶有 mlbmap 與強力除錯機制)...")
    
    result_data = {
        "meta": {"last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
        "dates": {},
        "standings": {"AL": {"East": [], "Central": [], "West": []}, "NL": {"East": [], "Central": [], "West": []}}
    }
    
    # ==========================================
    # 1. 抓取分區戰績排名 (Standings)
    # ==========================================
    print("📊 正在同步最新分區戰績表...")
    standings_url = "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104"
    st_data = get_json(standings_url)
    
    if st_data:
        for record in st_data.get("records", []):
            div_name = record.get("division", {}).get("name", "")
            league = "AL" if "American" in div_name else "NL"
            if "East" in div_name: div = "East"
            elif "Central" in div_name: div = "Central"
            elif "West" in div_name: div = "West"
            else: continue
            
            for tr in record.get("teamRecords", []):
                t_name = tr.get("team", {}).get("name", "")
                # 💡 使用你的 mlbmap 來轉換名字，如果找不到就用原名
                t_abbr = mlbmap.get(t_name, t_name) 
                
                result_data["standings"][league][div].append({
                    "team": t_abbr,
                    "W": tr.get("wins", 0),
                    "L": tr.get("losses", 0),
                    "PCT": tr.get("winningPercentage", ".000"),
                    "GB": tr.get("gamesBack", "-")
                })
        print("✅ 戰績表解析成功！")
    else:
        print("⚠️ 戰績表抓取為空，跳過此步驟。")

    # ==========================================
    # 2. 抓取未來 8 天賽程與比分
    # ==========================================
    today = datetime.now()
    for i in range(0, 8):
        target_dt = today + timedelta(days=i)
        date_str = target_dt.strftime("%Y-%m-%d")
        result_data["dates"][date_str] = []
        print(f"📅 正在同步賽程：{date_str} ...")
        
        # 加上 hydrate 確保能抓到比分與基礎先發
        sched_url = f"https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1&date={date_str}&hydrate=probablePitcher,linescore"
        sched_data = get_json(sched_url)
        
        for date_entry in sched_data.get("dates", []):
            for game in date_entry.get("games", []):
                try:
                    # 💡 取得隊伍全名後，透過 mlbmap 轉為縮寫
                    away_name = game.get("teams", {}).get("away", {}).get("team", {}).get("name", "")
                    home_name = game.get("teams", {}).get("home", {}).get("team", {}).get("name", "")
                    away_abbr = mlbmap.get(away_name, "TBD")
                    home_abbr = mlbmap.get(home_name, "TBD")
                    
                    # 狀態解析
                    status_state = game.get("status", {}).get("abstractGameState", "Upcoming")
                    det_state = game.get("status", {}).get("detailedState", "Scheduled")
                    if status_state in ["Final", "Game Over"] or det_state == "Final": status = "Final"
                    elif status_state == "Live" or det_state in ["In Progress", "Warm-up"]: status = "Live"
                    else: status = "Upcoming"
                    
                    # 時間轉換
                    time_str = game.get("gameDate", "")
                    display_time = "--:--"
                    if time_str:
                        try:
                            dt_obj = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ") + timedelta(hours=8)
                            display_time = dt_obj.strftime("%H:%M") + " (台灣)"
                        except: pass
                    
                    # R-H-E 解析
                    linescore = game.get("linescore", {})
                    r_away = game.get("teams", {}).get("away", {}).get("score", "-")
                    r_home = game.get("teams", {}).get("home", {}).get("score", "-")
                    h_away = linescore.get("teams", {}).get("away", {}).get("hits", "-")
                    h_home = linescore.get("teams", {}).get("home", {}).get("hits", "-")
                    e_away = linescore.get("teams", {}).get("away", {}).get("errors", "-")
                    e_home = linescore.get("teams", {}).get("home", {}).get("errors", "-")
                    
                    # 投手解析
                    away_p = game.get("teams", {}).get("away", {}).get("probablePitcher", {}).get("fullName", "")
                    home_p = game.get("teams", {}).get("home", {}).get("probablePitcher", {}).get("fullName", "")
                    
                    # 💡 如果進行中/已結束的比賽抓不到名字，啟動 gamePk 深度挖掘
                    if (not away_p or not home_p) and status != "Upcoming":
                        game_pk = game.get("gamePk")
                        live_data = get_json(f"https://statsapi.mlb.com/api/v1/game/{game_pk}/feed/live")
                        matchup = live_data.get("gameData", {}).get("probablePitchers", {})
                        players = live_data.get("gameData", {}).get("players", {})
                        
                        if not away_p:
                            a_id = matchup.get("away", {}).get("id")
                            away_p = players.get(f"ID{a_id}", {}).get("fullName", "未定 (TBD)") if a_id else "未定 (TBD)"
                        if not home_p:
                            h_id = matchup.get("home", {}).get("id")
                            home_p = players.get(f"ID{h_id}", {}).get("fullName", "未定 (TBD)") if h_id else "未定 (TBD)"
                    
                    if not away_p: away_p = "未定 (TBD)"
                    if not home_p: home_p = "未定 (TBD)"
                    
                    result_data["dates"][date_str].append({
                        "home_team": home_abbr, "away_team": away_abbr,
                        "status": status, "time": display_time,
                        "rhe": {
                            "away": {"R": r_away, "H": h_away, "E": e_away},
                            "home": {"R": r_home, "H": h_home, "E": e_home}
                        },
                        "pitchers": {"away_starter": away_p, "home_starter": home_p}
                    })
                except Exception as inner_e:
                    print(f"⚠️ 單場賽事解析錯誤，跳過該場: {inner_e}")

    # 輸出檔案
    try:
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=4)
        print("🏁 [大功告成] data.json 成功寫入！")
    except Exception as write_e:
        print(f"❌ 寫入 JSON 失敗: {write_e}")

if __name__ == "__main__":
    fetch_mlb_dashboard_data()