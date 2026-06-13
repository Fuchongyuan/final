import json
import traceback
from datetime import datetime, timedelta
import urllib.request

def fetch_mlb_dashboard_data():
    print("🚀 [MLB 乾淨精簡版 V13] 移除打擊數據，回歸純粹先發投手對決面板...")

    result_data = {
        "meta": {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "engine": "mlb-official-clean-v13"
        },
        "dates": {}
    }

    today = datetime.now()
    # 產出未來 8 天的日期清單
    date_list = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(0, 8)]

    team_name_map = {
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

    for target_date in date_list:
        print(f"📅 正在同步日期：{target_date} ...")
        result_data["dates"][target_date] = []

        try:
            # 使用官方簡潔的 schedule 搭配 probablePitcher 水合查詢
            url = f"https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1&date={target_date}&hydrate=probablePitcher,linescore"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            
            with urllib.request.urlopen(req, timeout=10) as response:
                api_data = json.loads(response.read().decode('utf-8'))
                
            dates_list = api_data.get("dates", [])
            if not dates_list:
                continue
                
            games = dates_list[0].get("games", [])
            for game in games:
                away_full = game.get("teams", {}).get("away", {}).get("team", {}).get("name", "")
                home_full = game.get("teams", {}).get("home", {}).get("team", {}).get("name", "")
                away_slug = team_name_map.get(away_full, "TBD")
                home_slug = team_name_map.get(home_full, "TBD")

                abstract_status = game.get("status", {}).get("abstractGameState", "Upcoming")
                detailed_status = game.get("status", {}).get("detailedState", "Upcoming")
                
                if abstract_status in ["Final", "Game Over"] or detailed_status == "賽事結束":
                    game_status = "Final"
                elif abstract_status == "Live" or detailed_status in ["In Progress", "Warm-up"]:
                    game_status = "Live"
                else:
                    game_status = "Upcoming"

                # 提取比分資訊
                linescore = game.get("linescore", {})
                away_runs = game.get("teams", {}).get("away", {}).get("score", 0)
                home_runs = game.get("teams", {}).get("home", {}).get("score", 0)
                away_hits = linescore.get("teams", {}).get("away", {}).get("hits", 0)
                home_hits = linescore.get("teams", {}).get("home", {}).get("hits", 0)
                away_errors = linescore.get("teams", {}).get("away", {}).get("errors", 0)
                home_errors = linescore.get("teams", {}).get("home", {}).get("errors", 0)

                # 💡 投手數據：只抓最純粹的預計先發投手名字與左右投
                prob_away_obj = game.get("teams", {}).get("away", {}).get("probablePitcher", {})
                prob_home_obj = game.get("teams", {}).get("home", {}).get("probablePitcher", {})

                away_pitcher_name = prob_away_obj.get("fullName", "未定 (TBD)")
                home_pitcher_name = prob_home_obj.get("fullName", "未定 (TBD)")

                # 時間格式化（轉換為台灣時間顯示）
                game_time_str = game.get("gameDate", "")
                display_time = "--:--"
                if game_time_str:
                    try:
                        dt_obj = datetime.strptime(game_time_str, "%Y-%m-%dT%H:%M:%SZ") + timedelta(hours=8)
                        display_time = dt_obj.strftime("%H:%M") + " (台灣)"
                    except Exception: pass

                game_entry = {
                    "home_team": home_slug, "away_team": away_slug,
                    "status": game_status, "time": display_time,
                    "rhe": {
                        "away": {"R": away_runs, "H": away_hits, "E": int(away_errors if isinstance(away_errors, int) else 0)},
                        "home": {"R": home_runs, "H": home_hits, "E": int(home_errors if isinstance(home_errors, int) else 0)}
                    },
                    "pitchers": { 
                        "away_starter": away_pitcher_name,
                        "home_starter": home_pitcher_name
                    }
                }
                result_data["dates"][target_date].append(game_entry)

        except Exception as e:
            print(f"⚠️ 解析日期 {target_date} 錯誤: {str(e)}")
            traceback.print_exc()

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=4)
    print("🏁 [還原完畢] 已切換回最精簡結構，僅保留比分與先發投手名字！")

if __name__ == "__main__":
    fetch_mlb_dashboard_data()