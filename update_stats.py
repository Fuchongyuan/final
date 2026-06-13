import json
import requests
from datetime import datetime, timedelta

def get_pitcher_details(pitcher_id):
    """
    透過投手 ID 抓取他本賽季的基礎數據 (勝-敗, ERA, 三振數) 以及投球慣用手
    """
    if not pitcher_id:
        return {"hand": "", "stats": "暫無本季數據"}
    
    # 索取該球員的基礎資料與本季在常規賽 (currentSeason, gameType=R) 的投球數據 (pitching)
    url = f"https://statsapi.mlb.com/api/v1/people/{pitcher_id}?hydrate=stats(group=[pitching],type=[currentSeason],gameType=[R])"
    hand_text = ""
    stats_text = "暫無本季數據"
    
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            player_data = res.json()
            people = player_data.get("people", [])
            if people:
                player_info = people[0]
                
                # 1. 取得投球慣用手 (R: 右投, L: 左投)
                pitch_hand = player_info.get("pitchHand", {}).get("code", "")
                if pitch_hand == "R":
                    hand_text = "(右投)"
                elif pitch_hand == "L":
                    hand_text = "(左投)"
                
                # 2. 取得賽季數據
                stats_list = player_info.get("stats", [])
                if stats_list:
                    splits = stats_list[0].get("splits", [])
                    if splits:
                        stat = splits[0].get("stat", {})
                        wins = stat.get("wins", 0)
                        losses = stat.get("losses", 0)
                        era = stat.get("era", "-.--")
                        so = stat.get("strikeOuts", 0)
                        stats_text = f"{wins}勝{losses}敗 ERA {era} {so}SO"
    except Exception as e:
        print(f"抓取投手 ID {pitcher_id} 數據失敗: {e}")
        
    return {"hand": hand_text, "stats": stats_text}

def get_mlb_weeks_games():
    """
    深度優化版：抓取未來 7 天賽程
    包含：台灣時間(+8)、詳細比賽狀態、即時比分、球隊戰績、先發投手詳細資料與數據
    """
    start_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = (datetime.utcnow() + timedelta(days=8)).strftime("%Y-%m-%d")
    
    # 擴充 hydrate 參數，一併抓取比賽狀態與預計先發投手
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate={start_date}&endDate={end_date}&hydrate=team,probablePitcher,linescore,status"
    
    all_days_data = {}
    
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            print(f"API 請求失敗，狀態碼: {response.status_code}")
            return all_days_data
            
        res_data = response.json()
        
        for date_node in res_data.get("dates", []):
            for game in date_node.get("games", []):
                try:
                    # 1. 處理台灣時間與分類標籤
                    utc_time_str = game.get("gameDate")
                    utc_time = datetime.strptime(utc_time_str, "%Y-%m-%dT%H:%M:%SZ")
                    tw_time = utc_time + timedelta(hours=8)
                    
                    tw_date_key = tw_time.strftime("%Y-%m-%d")
                    day_label = tw_time.strftime("%m/%d")
                    
                    weekdays = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
                    weekday_label = weekdays[tw_time.weekday()]
                    
                    # 2. 解析比賽狀態與即時比分
                    status_node = game.get("status", {})
                    status_abstract = status_node.get("abstractGameState")  # Live, Final, Preview
                    status_detailed = status_node.get("detailedState")      # 詳細文字狀態
                    
                    linescore = game.get("linescore", {})
                    away_runs = linescore.get("teams", {}).get("away", {}).get("runs", "-")
                    home_runs = linescore.get("teams", {}).get("home", {}).get("runs", "-")
                    
                    # 3. 解析球隊與戰績
                    teams_node = game.get("teams", {})
                    away_node = teams_node.get("away", {})
                    home_node = teams_node.get("home", {})
                    
                    away_team = away_node.get("team", {}).get("name", "Unknown")
                    home_team = home_node.get("team", {}).get("name", "Unknown")
                    
                    away_record = f"{away_node.get('leagueRecord', {}).get('wins', 0)}-{away_node.get('leagueRecord', {}).get('losses', 0)}"
                    home_record = f"{home_node.get('leagueRecord', {}).get('wins', 0)}-{home_node.get('leagueRecord', {}).get('losses', 0)}"
                    
                    # 4. 解析投手姓名、慣用手與本季數據
                    away_p_node = away_node.get("probablePitcher", {})
                    home_p_node = home_node.get("probablePitcher", {})
                    
                    # 客隊投手詳細資料抓取
                    away_pitcher_name = away_p_node.get("fullName", "TBD")
                    away_pitcher_id = away_p_node.get("id")
                    away_pitcher_stats = "暫無本季數據"
                    if away_pitcher_name != "TBD":
                        print(f"正在抓取客隊先發 {away_pitcher_name} 的詳細數據...")
                        p_details = get_pitcher_details(away_pitcher_id)
                        if p_details["hand"]:
                            away_pitcher_name = f"{away_pitcher_name} {p_details['hand']}"
                        away_pitcher_stats = p_details["stats"]
                    
                    # 主隊投手詳細資料抓取
                    home_pitcher_name = home_p_node.get("fullName", "TBD")
                    home_pitcher_id = home_p_node.get("id")
                    home_pitcher_stats = "暫無本季數據"
                    if home_pitcher_name != "TBD":
                        print(f"正在抓取主隊先發 {home_pitcher_name} 的詳細數據...")
                        p_details = get_pitcher_details(home_pitcher_id)
                        if p_details["hand"]:
                            home_pitcher_name = f"{home_pitcher_name} {p_details['hand']}"
                        home_pitcher_stats = p_details["stats"]
                    
                    # 5. 初始化日期的 JSON 結構
                    if tw_date_key not in all_days_data:
                        all_days_data[tw_date_key] = {
                            "day_label": day_label,
                            "weekday_label": weekday_label,
                            "games": []
                        }
                    
                    # 6. 填入該場比賽的完整包裝
                    all_days_data[tw_date_key]["games"].append({
                        "game_time": tw_time.strftime("%H:%M"),
                        "game_status": status_detailed,
                        "is_live_or_final": status_abstract,
                        "away_team": away_team,
                        "away_record": away_record,
                        "away_runs": away_runs,
                        "home_team": home_team,
                        "home_record": home_record,
                        "home_runs": home_runs,
                        "away_pitcher": {
                            "name": away_pitcher_name,
                            "stats": away_pitcher_stats
                        },
                        "home_pitcher": {
                            "name": home_pitcher_name,
                            "stats": home_pitcher_stats
                        }
                    })
                except Exception as game_error:
                    print(f"解析單場比賽出錯: {game_error}")
                    continue
                    
    except Exception as e:
        print(f"全局賽程抓取失敗: {e}")
            
    return all_days_data

def main():
    tw_time = datetime.utcnow() + timedelta(hours=8)
    print("開始抓取 MLB 賽程與先發投手即時數據...")
    weekly_games = get_mlb_weeks_games()
    
    data = {
        "last_updated": tw_time.strftime('%Y-%m-%d %H:%M'),
        "weekly_data": weekly_games
    }
    
    # 寫入 json 檔案
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print("data.json 完整更新完成！")

if __name__ == "__main__":
    main()