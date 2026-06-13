import json
import traceback
from datetime import datetime, timedelta
import urllib.request

def fetch_mlb_dashboard_data():
    print("🚀 [MLB 官方賽前對對碰 V7] 啟動『賽前預計先發 + 兩隊先發打線數據』完全體...")

    result_data = {
        "meta": {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "engine": "mlb-official-api-v7-pregame-matchup"
        },
        "dates": {}
    }

    today = datetime.now()
    # 依然抓取接下來一週的賽事預報
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
        print(f"📅 正在分析日期：{target_date} ...")
        result_data["dates"][target_date] = []

        try:
            # 串接 liveData 結構來抓取 pre-game 的 lineup 預告與球員單季基本面
            url = f"https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1&date={target_date}&hydrate=liveData,probablePitcher"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            
            with urllib.request.urlopen(req, timeout=10) as response:
                api_data = json.loads(response.read().decode('utf-8'))
                
            dates_list = api_data.get("dates", [])
            if not dates_list:
                continue
                
            games = dates_list[0].get("games", [])
            for game in games:
                # 🎯 篩選過濾：我們只要還沒開始打的比賽 (Upcoming / Preview)
                abstract_status = game.get("status", {}).get("abstractGameState", "Upcoming")
                if abstract_status == "Final":
                    continue # 略過已結束比賽

                away_full = game.get("teams", {}).get("away", {}).get("team", {}).get("name", "")
                home_full = game.get("teams", {}).get("home", {}).get("team", {}).get("name", "")
                away_slug = team_name_map.get(away_full, "TBD")
                home_slug = team_name_map.get(home_full, "TBD")

                # 1. 🪓 解析先發投手數據 (對齊官網：W-L, ERA, K, 背號, 投打手)
                live_data = game.get("liveData", {})
                boxscore_teams = live_data.get("boxscore", {}).get("teams", {})
                
                def parse_pitcher_details(team_type):
                    p_info = game.get("teams", {}).get(team_type, {}).get("probablePitcher", {})
                    p_id = p_info.get("id")
                    p_name = p_info.get("fullName", "未定 (TBD)")
                    
                    details = {"name": p_name, "meta": "", "stats": "0-0 | -.-- ERA | - K"}
                    if not p_id:
                        return details
                    
                    # 從 boxscore 裡面抓該球員的詳細資料與 season 累積數據
                    player_data = boxscore_teams.get(team_type, {}).get("players", {}).get(f"ID{p_id}", {})
                    if player_data:
                        jersey = player_data.get("jerseyNumber", "#")
                        throws = player_data.get("person", {}).get("pitchHand", {}).get("code", "R")
                        details["meta"] = f"{throws}HP | #{jersey}"
                        
                        s_stats = player_data.get("seasonStats", {}).get("pitching", {})
                        if s_stats:
                            wins = s_stats.get("wins", 0)
                            losses = s_stats.get("losses", 0)
                            era = s_stats.get("era", "-.--")
                            strikeouts = s_stats.get("strikeOuts", 0)
                            details["stats"] = f"{wins}-{losses} | {era} ERA | {strikeouts} K"
                    return details

                away_p_obj = parse_pitcher_details("away")
                home_p_obj = parse_pitcher_details("home")

                # 2. 🪓 解析先發九棒打線 (Lineups) 與打擊數據 (B, HR, RBI, SB, AVG, OPS)
                def parse_lineup_list(team_type):
                    lineup_data = []
                    team_box = boxscore_teams.get(team_type, {})
                    # 大聯盟公布打線時，會放在 battingOrder 陣列裡
                    batting_order = team_box.get("battingOrder", [])
                    players_dict = team_box.get("players", {})
                    
                    if not batting_order:
                        return [] # 還沒排出來
                        
                    for p_id in batting_order:
                        p_key = f"ID{p_id}"
                        if p_key in players_dict:
                            p_obj = players_dict[p_key]
                            p_name = p_obj.get("person", {}).get("fullName", "Unknown")
                            pos = p_obj.get("position", {}).get("abbreviation", "DH")
                            bats = p_obj.get("person", {}).get("batSide", {}).get("code", "R")
                            
                            s_batting = p_obj.get("seasonStats", {}).get("batting", {})
                            hr = s_batting.get("homeRuns", 0)
                            rbi = s_batting.get("runsBattedIn", 0)
                            sb = s_batting.get("stolenBases", 0)
                            avg = s_batting.get("avg", ".000")
                            ops = s_batting.get("ops", ".000")
                            
                            lineup_data.append({
                                "name": p_name, "pos": pos, "bats": bats,
                                "hr": hr, "rbi": rbi, "sb": sb, "avg": avg, "ops": ops
                            })
                    return lineup_data[:9] # 只要前九棒

                away_lineup = parse_lineup_list("away")
                home_lineup = parse_lineup_list("home")

                # 處理台灣時間
                game_time_str = game.get("gameDate", "")
                display_time = "10:10 AM"
                if game_time_str:
                    try:
                        dt_obj = datetime.strptime(game_time_str, "%Y-%m-%dT%H:%M:%SZ") + timedelta(hours=8)
                        display_time = dt_obj.strftime("%H:%M") + " (台灣)"
                    except Exception: pass

                # 打包進 JSON
                game_entry = {
                    "home_team": home_slug, "away_team": away_slug,
                    "time": display_time,
                    "status": "Upcoming",
                    "pitchers": { "away": away_p_obj, "home": home_p_obj },
                    "lineups": { "away": away_lineup, "home": home_lineup }
                }
                result_data["dates"][target_date].append(game_entry)

        except Exception as e:
            print(f"⚠️ 解析日期 {target_date} 發生錯誤: {str(e)}")
            traceback.print_exc()

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=4)
    print("🏁 [賽前大面板資料同步完畢] 投手數據與先發打線已成功打包！")

if __name__ == "__main__":
    fetch_mlb_dashboard_data()