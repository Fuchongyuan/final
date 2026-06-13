import json
import requests
from datetime import datetime, timedelta

def get_mlb_weeks_games():
    """
    深度優化版：抓取未來 7 天賽程
    包含：台灣時間(+8)、日期+1天、比賽狀態、即時比分、投手詳細慣用手
    """
    # 抓取範圍拉寬，確保涵蓋到所有跨日與補賽賽程
    start_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = (datetime.utcnow() + timedelta(days=8)).strftime("%Y-%m-%d")
    
    # 擴充 hydrate 參數，一併抓取比賽狀態(linescore)與投球慣用手
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
                    # 1. 時區與日期位移處理 (+8 時區，且日期強制 +1)
                    utc_dt = datetime.strptime(game.get("gameDate"), "%Y-%m-%dT%H:%M:%SZ")
                    tw_dt = utc_dt + timedelta(hours=8)
                    
                    target_dt = tw_dt
                    target_date_key = target_dt.strftime("%Y-%m-%d")
                    
                    # 2. 擷取更詳細的比賽狀態與比分
                    status_detailed = game.get("status", {}).get("detailedState", "Unknown")
                    status_abstract = game.get("status", {}).get("abstractGameState", "Preview")
                    
                    linescore = game.get("linescore", {})
                    away_runs = linescore.get("teams", {}).get("away", {}).get("runs", "-")
                    home_runs = linescore.get("teams", {}).get("home", {}).get("runs", "-")
                    
                    # 3. 擷取球隊基本資料
                    teams = game.get("teams", {})
                    away_team_node = teams.get("away", {})
                    home_team_node = teams.get("home", {})
                    
                    away_team = away_team_node.get("team", {}).get("name", "Unknown")
                    home_team = home_team_node.get("team", {}).get("name", "Unknown")
                    
                    away_record = f"{away_team_node.get('leagueRecord', {}).get('wins', 0)}-{away_team_node.get('leagueRecord', {}).get('losses', 0)}"
                    home_record = f"{home_team_node.get('leagueRecord', {}).get('wins', 0)}-{home_team_node.get('leagueRecord', {}).get('losses', 0)}"
                    
                    # 4. 擷取先發投手更詳細的資料 (加入左右投)
                    away_pitcher_node = away_team_node.get("probablePitcher", {})
                    home_pitcher_node = home_team_node.get("probablePitcher", {})
                    
                    away_pitcher_name = away_pitcher_node.get("fullName", "TBD")
                    # MLB API 的左右手通常在格式化名單中，若拿不到就給空字串
                    away_pitcher_hand = f"({away_pitcher_node.get('pitchHand', {}).get('code', '')})" if away_pitcher_node.get("pitchHand") else ""
                    
                    home_pitcher_name = home_pitcher_node.get("fullName", "TBD")
                    home_pitcher_hand = f"({home_pitcher_node.get('pitchHand', {}).get('code', '')})" if home_pitcher_node.get("pitchHand") else ""
                    
                    # 5. 初始化該日期結構
                    if target_date_key not in all_days_data:
                        all_days_data[target_date_key] = {
                            "day_label": target_dt.strftime("%m/%d"),
                            "weekday_label": ["週一", "週二", "週三", "週四", "週五", "週六", "週日"][target_dt.weekday()],
                            "games": []
                        }
                    
                    # 6. 組裝更詳細的 JSON 結構
                    all_days_data[target_date_key]["games"].append({
                        "game_time": tw_dt.strftime("%H:%M"),
                        "game_status": status_detailed,       # 比賽狀態 (e.g., Final, In Progress, Postponed)
                        "is_live_or_final": status_abstract,  # 用於前端判斷是否要顯示比分 (Live/Final/Preview)
                        "away_team": away_team,
                        "away_record": away_record,
                        "away_runs": away_runs,               # 客隊得分
                        "home_team": home_team,
                        "home_record": home_record,
                        "home_runs": home_runs,               # 主隊得分
                        "away_pitcher": {"name": f"{away_pitcher_name} {away_pitcher_hand}".strip()},
                        "home_pitcher": {"name": f"{home_pitcher_name} {home_pitcher_hand}".strip()}
                    })
                except Exception as game_error:
                    # 單場比賽解析出錯不影響其他比賽
                    print(f"解析單場比賽出錯: {game_error}")
                    continue
                    
    except Exception as e:
        print(f"全球員資料深度抓取失敗: {e}")
            
    return all_days_data

def main():
    tw_time = datetime.utcnow() + timedelta(hours=8)
    weekly_games = get_mlb_weeks_games()
    
    data = {
        "last_updated": tw_time.strftime('%Y-%m-%d %H:%M'),
        "weekly_data": weekly_games
    }
    
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print(f"【深度詳細抓取完畢】已成功產出包含狀態、比分與投手細節的 data.json！")

if __name__ == "__main__":
    main()