import json
import urllib.request
from datetime import datetime, timedelta, timezone

def get_json(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"抓取失敗 {url}: {e}")
        return {}

def fetch_mlb_dashboard_data():
    print("🚀 [V16 終極版] 強制解析 gamePk、抓取分區排名，並修正台灣時區...")
    
    # 【關鍵修正】：強制鎖定台灣時間 (UTC+8)，避免 Actions 伺服器在早上 8 點前抓到昨天
    tz_tw = timezone(timedelta(hours=8))
    today = datetime.now(tz_tw)
    
    result_data = {
        "meta": {"last_updated": today.strftime("%Y-%m-%d %H:%M:%S")}, 
        "dates": {},
        "standings": {}
    }
    
    # ==========================================
    # 1. 抓取賽事與即時比分 (保留你的 gamePk 解析法)
    # ==========================================
    for i in range(0, 3):
        target_dt = today + timedelta(days=i)
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
                
                teams = game_info.get("teams", {})
                players = game_info.get("players", {})
                
                # 投手資訊
                matchup = game_info.get("probablePitchers", {})
                away_p_id = matchup.get("away", {}).get("id")
                home_p_id = matchup.get("home", {}).get("id")
                
                away_p_name = players.get(f"ID{away_p_id}", {}).get("fullName", "未定 (TBD)") if away_p_id else "未定 (TBD)"
                home_p_name = players.get(f"ID{home_p_id}", {}).get("fullName", "未定 (TBD)") if home_p_id else "未定 (TBD)"
                
                # 隊伍縮寫
                away_slug = game_info.get("teams", {}).get("away", {}).get("abbreviation", "TBD")
                home_slug = game_info.get("teams", {}).get("home", {}).get("abbreviation", "TBD")
                
                # 狀態判定
                status_str = game_info.get("status", {}).get("detailedState", "Scheduled")
                if status_str in ["In Progress", "Warm-up"]:
                    status = "Live"
                elif status_str in ["Final", "Completed Early", "Game Over"]:
                    status = "Final"
                else:
                    status = "Upcoming"
                    
                # 抓取 RHE 比分 (Runs, Hits, Errors)
                linescore = live_info.get("linescore", {}).get("teams", {})
                rhe = {
                    "away": {
                        "R": linescore.get("away", {}).get("runs", "-"),
                        "H": linescore.get("away", {}).get("hits", "-"),
                        "E": linescore.get("away", {}).get("errors", "-")
                    },
                    "home": {
                        "R": linescore.get("home", {}).get("runs", "-"),
                        "H": linescore.get("home", {}).get("hits", "-"),
                        "E": linescore.get("home", {}).get("errors", "-")
                    }
                }
                
                result_data["dates"][date_str].append({
                    "home_team": home_slug, "away_team": away_slug,
                    "status": status,
                    "time": game_info.get("datetime", {}).get("time", "--:--"),
                    "rhe": rhe,
                    "pitchers": {
                        "away_starter": away_p_name,
                        "home_starter": home_p_name
                    }
                })

    # ==========================================
    # 2. 抓取分區排名數據 (Standings)
    # ==========================================
    standings_url = "https://statsapi.mlb.com/api/v1/standings?standingsTypes=regularSeason&sportId=1"
    s_res = get_json(standings_url)
    
    for record in s_res.get("records", []):
        div_name = record.get("division", {}).get("name", "未知分區")
        if "American League East" in div_name: div_name = "美聯東區 (AL East)"
        elif "American League Central" in div_name: div_name = "美聯中區 (AL Central)"
        elif "American League West" in div_name: div_name = "美聯西區 (AL West)"
        elif "National League East" in div_name: div_name = "國聯東區 (NL East)"
        elif "National League Central" in div_name: div_name = "國聯中區 (NL Central)"
        elif "National League West" in div_name: div_name = "國聯西區 (NL West)"

        teams_list = []
        for team_rec in record.get("teamRecords", []):
            t_code = team_rec.get("team", {}).get("teamCode", "TEAM").upper()
            split_recs = team_rec.get("records", {}).get("splitRecords", [])
            
            l10, home_rec, away_rec = "0-0", "0-0", "0-0"
            for sr in split_recs:
                if sr.get("type") == "lastTen": l10 = f"{sr.get('wins',0)}-{sr.get('losses',0)}"
                elif sr.get("type") == "home": home_rec = f"{sr.get('wins',0)}-{sr.get('losses',0)}"
                elif sr.get("type") == "away": away_rec = f"{sr.get('wins',0)}-{sr.get('losses',0)}"
            
            teams_list.append({
                "name": team_rec.get("team", {}).get("name", ""),
                "code": t_code,
                "w": team_rec.get("wins", 0),
                "l": team_rec.get("losses", 0),
                "gb": team_rec.get("divisionGamesBack", "—"),
                "l10": l10,
                "home": home_rec,
                "away": away_rec
            })
        result_data["standings"][div_name] = teams_list

    # ==========================================
    # 3. 匯出 data.json
    # ==========================================
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=4)
    print("🏁 [V16 完成] 賽事與排名已同步更新，TBD 與時區問題排除。")

if __name__ == "__main__":
    fetch_mlb_dashboard_data()