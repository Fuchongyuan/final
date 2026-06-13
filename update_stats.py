import json
import traceback
from datetime import datetime, timedelta
import urllib.request

def fetch_mlb_dashboard_data():
    print("🚀 [MLB 全能終極版 V8] 啟動『三向狀態完整保留 + 賽前打線/賽中 R-H-E 動態分流』...")

    result_data = {
        "meta": {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "engine": "mlb-official-api-v8-all-in-one"
        },
        "dates": {}
    }

    today = datetime.now()
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
        print(f"📅 正在同步日期數據：{target_date} ...")
        result_data["dates"][target_date] = []

        try:
            # 深度注入所有必要的水元數據，確保 pre-game / live / final 數據一次到位
            url = f"https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1&date={target_date}&hydrate=decisions,linescore,liveData,probablePitcher"
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

                # 精準狀態三向分流
                abstract_status = game.get("status", {}).get("abstractGameState", "Upcoming")
                detailed_status = game.get("status", {}).get("detailedState", "Upcoming")
                
                if abstract_status in ["Final", "Game Over"] or detailed_status == "賽事結束":
                    game_status = "Final"
                elif abstract_status == "Live" or detailed_status in ["In Progress", "Warm-up", "正在進行"]:
                    game_status = "Live"
                else:
                    game_status = "Upcoming"

                # 📊 1. 提取球隊即時 R-H-E 數據（給 Live / Final 使用）
                linescore = game.get("linescore", {})
                away_runs = game.get("teams", {}).get("away", {}).get("score", 0)
                home_runs = game.get("teams", {}).get("home", {}).get("score", 0)
                away_hits = linescore.get("teams", {}).get("away", {}).get("hits", 0)
                home_hits = linescore.get("teams", {}).get("home", {}).get("hits", 0)
                
                away_errors = linescore.get("teams", {}).get("away", {}).get("errors", 0)
                if not isinstance(away_errors, int): away_errors = 0
                home_errors = linescore.get("teams", {}).get("home", {}).get("errors", 0)
                if not isinstance(home_errors, int): home_errors = 0

                # 🧢 2. 深度提取投手大結構 (不論哪種狀態都支援)
                live_data = game.get("liveData", {})
                boxscore_teams = live_data.get("boxscore", {}).get("teams", {})
                
                def get_pitcher_game_line(team_type, player_id_target):
                    # 抓取單場即時表現數據
                    players = boxscore_teams.get(team_type, {}).get("players", {})
                    p_key = f"ID{player_id_target}"
                    if p_key in players:
                        p_stats = players[p_key].get("stats", {}).get("pitching", {})
                        return f" (H:{p_stats.get('hits',0)} ER:{p_stats.get('earnedRuns',0)} BB:{p_stats.get('baseOnBalls',0)} SO:{p_stats.get('strikeOuts',0)})"
                    return ""

                away_p_detail = {"name": "未定 (TBD)", "meta": "", "stats": ""}
                home_p_detail = {"name": "未定 (TBD)", "meta": "", "stats": ""}

                # 賽前預計先發基礎數據
                prob_away = game.get("teams", {}).get("away", {}).get("probablePitcher", {})
                prob_home = game.get("teams", {}).get("home", {}).get("probablePitcher", {})

                def fill_probable_p(team_type, prob_obj):
                    p_id = prob_obj.get("id")
                    res = {"name": prob_obj.get("fullName", "未定 (TBD)"), "meta": "LHP/RHP", "stats": "0-0 | -.-- ERA"}
                    if p_id:
                        p_data = boxscore_teams.get(team_type, {}).get("players", {}).get(f"ID{p_id}", {})
                        if p_data:
                            jersey = p_data.get("jerseyNumber", "#")
                            throws = p_data.get("person", {}).get("pitchHand", {}).get("code", "R")
                            res["meta"] = f"{throws}HP | #{jersey}"
                            s_stats = p_data.get("seasonStats", {}).get("pitching", {})
                            if s_stats:
                                res["stats"] = f"{s_stats.get('wins',0)}-{s_stats.get('losses',0)} | {s_stats.get('era','-.--')} ERA | {s_stats.get('strikeOuts',0)} K"
                    return res

                if game_status == "Upcoming":
                    away_p_detail = fill_probable_p("away", prob_away)
                    home_p_detail = fill_probable_p("home", prob_home)
                elif game_status == "Live":
                    # 比賽中抓當前場上投手
                    current_p_id = linescore.get("defense", {}).get("pitcher", {}).get("id")
                    current_p_name = linescore.get("defense", {}).get("pitcher", {}).get("fullName")
                    is_away_hitting = linescore.get("teams", {}).get("away", {}).get("isHitting", False)
                    
                    # 預填先發名
                    away_p_detail["name"] = f"先發: {prob_away.get('fullName','未定')}"
                    home_p_detail["name"] = f"先發: {prob_home.get('fullName','未定')}"
                    
                    if current_p_name:
                        if is_away_hitting: # 客隊在打擊 -> 主隊在防守投球
                            home_p_detail["name"] = f"場上: {current_p_name}"
                            home_p_detail["stats"] = "單場:" + get_pitcher_game_line("home", current_p_id)
                        else:
                            away_p_detail["name"] = f"場上: {current_p_name}"
                            away_p_detail["stats"] = "單場:" + get_pitcher_game_line("away", current_p_id)
                else: # Final 已結束
                    decisions = game.get("decisions", {})
                    win_p_name = decisions.get("winner", {}).get("fullName", "-")
                    win_p_id = decisions.get("winner", {}).get("id")
                    lose_p_name = decisions.get("loser", {}).get("fullName", "-")
                    lose_p_id = decisions.get("loser", {}).get("id")
                    if away_runs > home_runs:
                        away_p_detail["name"] = f"勝投: {win_p_name}"
                        away_p_detail["stats"] = "表現:" + (get_pitcher_game_line("away", win_p_id) if win_p_id else "")
                        home_p_detail["name"] = f"敗投: {lose_p_name}"
                        home_p_detail["stats"] = "表現:" + (get_pitcher_game_line("home", lose_p_id) if lose_p_id else "")
                    else:
                        away_p_detail["name"] = f"敗投: {lose_p_name}"
                        away_p_detail["stats"] = "表現:" + (get_pitcher_game_line("away", lose_p_id) if lose_p_id else "")
                        home_p_detail["name"] = f"勝投: {win_p_name}"
                        home_p_detail["stats"] = "表現:" + (get_pitcher_game_line("home", win_p_id) if win_p_id else "")

                # 📋 3. 提取先發九棒打線 (Lineups) 與打擊三圍
                def parse_lineup_list(team_type):
                    lineup_data = []
                    team_box = boxscore_teams.get(team_type, {})
                    batting_order = team_box.get("battingOrder", [])
                    players_dict = team_box.get("players", {})
                    if not batting_order: return []
                    for p_id in batting_order:
                        p_key = f"ID{p_id}"
                        if p_key in players_dict:
                            p_obj = players_dict[p_key]
                            s_batting = p_obj.get("seasonStats", {}).get("batting", {})
                            lineup_data.append({
                                "name": p_obj.get("person", {}).get("fullName", "Unknown"),
                                "pos": p_obj.get("position", {}).get("abbreviation", "DH"),
                                "bats": p_obj.get("person", {}).get("batSide", {}).get("code", "R"),
                                "hr": s_batting.get("homeRuns", 0),
                                "rbi": s_batting.get("runsBattedIn", 0),
                                "sb": s_batting.get("stolenBases", 0),
                                "avg": s_batting.get("avg", ".000"),
                                "ops": s_batting.get("ops", ".000")
                            })
                    return lineup_data[:9]

                away_lineup = parse_lineup_list("away")
                home_lineup = parse_lineup_list("home")

                # 台灣時間轉換
                game_time_str = game.get("gameDate", "")
                display_time = "10:10 AM"
                if game_time_str:
                    try:
                        dt_obj = datetime.strptime(game_time_str, "%Y-%m-%dT%H:%M:%SZ") + timedelta(hours=8)
                        display_time = dt_obj.strftime("%H:%M") + " (台灣)"
                    except Exception: pass

                game_entry = {
                    "home_team": home_slug, "away_team": away_slug,
                    "status": game_status, "time": display_time,
                    "rhe": {
                        "away": {"R": away_runs, "H": away_hits, "E": away_errors},
                        "home": {"R": home_runs, "H": home_hits, "E": home_errors}
                    },
                    "pitchers": { "away": away_p_detail, "home": home_p_detail },
                    "lineups": { "away": away_lineup, "home": home_lineup }
                }
                result_data["dates"][target_date].append(game_entry)

        except Exception as e:
            print(f"⚠️ 解析日期 {target_date} 發生錯誤: {str(e)}")
            traceback.print_exc()

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=4)
    print("🏁 [資料完全同步] 成功合併所有賽事狀態與雙軌數據！")

if __name__ == "__main__":
    fetch_mlb_dashboard_data()