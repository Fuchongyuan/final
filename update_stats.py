import json
import traceback
from datetime import datetime, timedelta
import urllib.request

def fetch_player_season_stats(player_id):
    """
    【打者數據保底核心】當場次 API 內無球員賽季數據時，直接單獨調用大聯盟球員個人數據 API 撈取今年賽季累積數據
    """
    current_year = datetime.now().year
    url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=season&group=batting&season={current_year}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            stats_splits = data.get("stats", [])
            if stats_splits:
                splits = stats_splits[0].get("splits", [])
                if splits:
                    return splits[0].get("stat", {})
    except Exception:
        pass
    return {}

def fetch_mlb_dashboard_data():
    print("🚀 [MLB 全能完全體 V11] 啟動『預計先發+場上投手雙全』與『打者數據深度修復機制』...")

    result_data = {
        "meta": {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "engine": "mlb-official-api-v11-batting-fix"
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
        print(f"📅 正在同步日期：{target_date} ...")
        result_data["dates"][target_date] = []

        try:
            # 深度 hydration 注入所有打線數據與 live 數據
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

                abstract_status = game.get("status", {}).get("abstractGameState", "Upcoming")
                detailed_status = game.get("status", {}).get("detailedState", "Upcoming")
                
                if abstract_status in ["Final", "Game Over"] or detailed_status == "賽事結束":
                    game_status = "Final"
                elif abstract_status == "Live" or detailed_status in ["In Progress", "Warm-up", "正在進行"]:
                    game_status = "Live"
                else:
                    game_status = "Upcoming"

                linescore = game.get("linescore", {})
                away_runs = game.get("teams", {}).get("away", {}).get("score", 0)
                home_runs = game.get("teams", {}).get("home", {}).get("score", 0)
                away_hits = linescore.get("teams", {}).get("away", {}).get("hits", 0)
                home_hits = linescore.get("teams", {}).get("home", {}).get("hits", 0)
                away_errors = linescore.get("teams", {}).get("away", {}).get("errors", 0)
                home_errors = linescore.get("teams", {}).get("home", {}).get("errors", 0)

                live_data = game.get("liveData", {})
                boxscore_teams = live_data.get("boxscore", {}).get("teams", {})
                
                # ------------------- 🧢 投手大融合數據處理 -------------------
                def get_season_pitcher_stats(team_type, pitcher_id):
                    if not pitcher_id: return {"name": "未定 (TBD)", "meta": "", "stats": "0-0 | -.-- ERA"}
                    players = boxscore_teams.get(team_type, {}).get("players", {})
                    p_data = players.get(f"ID{pitcher_id}") or players.get(str(pitcher_id))
                    
                    name = "未定"
                    meta = "LHP/RHP"
                    stats = "0-0 | -.-- ERA"
                    
                    if p_data:
                        name = p_data.get("person", {}).get("fullName", "未定")
                        jersey = p_data.get("jerseyNumber", "#")
                        throws = p_data.get("person", {}).get("pitchHand", {}).get("code", "R")
                        meta = f"{throws}HP | #{jersey}"
                        s_stats = p_data.get("seasonStats", {}).get("pitching", {})
                        if s_stats:
                            stats = f"{s_stats.get('wins',0)}-{s_stats.get('losses',0)} | {s_stats.get('era','-.--')} ERA | {s_stats.get('strikeOuts',0)} K"
                    return {"name": name, "meta": meta, "stats": stats}

                def get_live_pitcher_line(team_type, pitcher_id):
                    if not pitcher_id: return "單場: 未上場"
                    players = boxscore_teams.get(team_type, {}).get("players", {})
                    p_data = players.get(f"ID{pitcher_id}") or players.get(str(pitcher_id))
                    if p_data:
                        p_stats = p_data.get("stats", {}).get("pitching", {})
                        if p_stats:
                            return f"單場: H:{p_stats.get('hits',0)} ER:{p_stats.get('earnedRuns',0)} BB:{p_stats.get('baseOnBalls',0)} SO:{p_stats.get('strikeOuts',0)}"
                    return "單場: 0 H | 0 ER"

                # 1. 預計先發投手數據 (不論任何狀態都保底顯示賽前賽季數據)
                prob_away_id = game.get("teams", {}).get("away", {}).get("probablePitcher", {}).get("id")
                prob_home_id = game.get("teams", {}).get("home", {}).get("probablePitcher", {}).get("id")
                
                prob_away_obj = get_season_pitcher_stats("away", prob_away_id) if prob_away_id else {"name": game.get("teams", {}).get("away", {}).get("probablePitcher", {}).get("fullName", "未定 (TBD)"), "meta": "RHP", "stats": "0-0 | -.-- ERA"}
                prob_home_obj = get_season_pitcher_stats("home", prob_home_id) if prob_home_id else {"name": game.get("teams", {}).get("home", {}).get("probablePitcher", {}).get("fullName", "未定 (TBD)"), "meta": "RHP", "stats": "0-0 | -.-- ERA"}

                # 2. 目前場上投手 / 賽後決策投手數據
                current_away_p = {"name": "尚未登板", "stats": "單場: -"}
                current_home_p = {"name": "尚未登板", "stats": "單場: -"}

                if game_status == "Live":
                    curr_p_id = linescore.get("defense", {}).get("pitcher", {}).get("id")
                    curr_p_name = linescore.get("defense", {}).get("pitcher", {}).get("fullName", "場上投手")
                    is_away_hitting = linescore.get("teams", {}).get("away", {}).get("isHitting", False)
                    if is_away_hitting: # 主隊在投球
                        current_home_p = {"name": f"🔥 {curr_p_name}", "stats": get_live_pitcher_line("home", curr_p_id)}
                    else: # 客隊在投球
                        current_away_p = {"name": f"🔥 {curr_p_name}", "stats": get_live_pitcher_line("away", curr_p_id)}
                elif game_status == "Final":
                    decisions = game.get("decisions", {})
                    win_id = decisions.get("winner", {}).get("id")
                    win_name = decisions.get("winner", {}).get("fullName", "勝投")
                    lose_id = decisions.get("loser", {}).get("id")
                    lose_name = decisions.get("loser", {}).get("fullName", "敗投")
                    if away_runs > home_runs:
                        current_away_p = {"name": f"🏆 勝投: {win_name}", "stats": get_live_pitcher_line("away", win_id)}
                        current_home_p = {"name": f"❌ 敗投: {lose_name}", "stats": get_live_pitcher_line("home", lose_id)}
                    else:
                        current_away_p = {"name": f"❌ 敗投: {lose_name}", "stats": get_live_pitcher_line("away", lose_id)}
                        current_home_p = {"name": f"🏆 勝投: {win_name}", "stats": get_live_pitcher_line("home", win_id)}

                # ------------------- 📋 打線名單與數據深度修復 -------------------
                def parse_lineup_list(team_type):
                    lineup_data = []
                    team_box = boxscore_teams.get(team_type, {})
                    batting_order = team_box.get("battingOrder", [])
                    players_dict = team_box.get("players", {})
                    
                    # 判斷是否需要智慧兜底選人
                    if len(batting_order) >= 9:
                        target_list = batting_order
                    else:
                        all_players = []
                        for p_id, p_obj in players_dict.items():
                            if p_obj.get("position", {}).get("code") != "1": # 排除投手
                                s_batting = p_obj.get("seasonStats", {}).get("batting", {})
                                ab = s_batting.get("atBats", 0)
                                all_players.append((ab, p_id, p_obj))
                        all_players.sort(key=lambda x: x[0], reverse=True)
                        target_list = [x[1] for x in all_players[:9]] if all_players else []

                    for p_key in target_list:
                        # 格式化 ID 確保符合字典鍵值
                        raw_id = str(p_key).replace("ID", "")
                        p_dict_key = f"ID{raw_id}"
                        
                        if p_dict_key in players_dict:
                            p_obj = players_dict[p_dict_key]
                            
                            # 【核心修正點】嘗試取得賽季打擊數據
                            s_batting = p_obj.get("seasonStats", {}).get("batting", {})
                            
                            # 【雙重防禦】如果發現當前 API 裡面的賽季數據是空的，直接向個人 API 索取累積數據
                            if not s_batting or s_batting.get("atBats", 0) == 0:
                                print(f"🔍 偵測到球員 {p_obj.get('person',{}).get('fullName')} 缺乏當日賽季欄位，啟動保底 API...")
                                s_batting = fetch_player_season_stats(raw_id)
                                
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
                        "away": {"R": away_runs, "H": away_hits, "E": int(away_errors if isinstance(away_errors, int) else 0)},
                        "home": {"R": home_runs, "H": home_hits, "E": int(home_errors if isinstance(home_errors, int) else 0)}
                    },
                    "pitchers": { 
                        "probable_away": prob_away_obj, "probable_home": prob_home_obj,
                        "current_away": current_away_p, "current_home": current_home_p
                    },
                    "lineups": { "away": away_lineup, "home": home_lineup }
                }
                result_data["dates"][target_date].append(game_entry)

        except Exception as e:
            print(f"⚠️ 解析日期 {target_date} 錯誤: {str(e)}")
            traceback.print_exc()

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=4)
    print("🏁 [修復完畢] 投手數據雙倂 + 打者個人賽季數據強制拉取成功！")

if __name__ == "__main__":
    fetch_mlb_dashboard_data()