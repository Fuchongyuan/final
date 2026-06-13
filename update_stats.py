import json
import requests
from datetime import datetime, timedelta

def get_mlb_weeks_games():
    """
    終極強化版：抓取未來 7 天賽程
    包含：台灣時間(+8)、比賽狀態、即時比分、投手詳細慣用手
    新增：球隊勝率、分區排名、勝差、連勝/連敗狀態、團隊賽季總得分/總失分
    """
    # 抓取範圍拉寬，確保涵蓋到所有跨日與補賽賽程
    start_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = (datetime.utcnow() + timedelta(days=8)).strftime("%Y-%m-%d")
    
    # 【核心優化】擴充 hydrate 參數，加入 record 以獲取分區排名、勝率、連勝敗及團隊數據
    hydrate_params = "team(record),probablePitcher,linescore,status"
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate={start_date}&endDate={end_date}&hydrate={hydrate_params}"
    
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
                    # 1. 時區與日期位移處理 (+8 時區)
                    utc_dt = datetime.strptime(game.get("gameDate"), "%Y-%m-%dT%H:%M:%SZ")
                    tw_dt = utc_dt + timedelta(hours=8)
                    
                    target_dt = tw_dt
                    target_date_key = target_dt.strftime("%Y-%m-%d")
                    
                    # 2. 擷取比賽狀態與比分
                    status_detailed = game.get("status", {}).get("detailedState", "Unknown")
                    status_abstract = game.get("status", {}).get("abstractGameState", "Preview")
                    
                    linescore = game.get("linescore", {})
                    away_runs = linescore.get("teams", {}).get("away", {}).get("runs", "-")
                    home_runs = linescore.get("teams", {}).get("home", {}).get("runs", "-")
                    
                    # 3. 擷取球隊基本與【深度戰績數據】
                    teams = game.get("teams", {})
                    away_team_node = teams.get("away", {})
                    home_team_node = teams.get("home", {})
                    
                    # 球隊名稱
                    away_team = away_team_node.get("team", {}).get("name", "Unknown")
                    home_team = home_team_node.get("team", {}).get("name", "Unknown")
                    
                    # 基本勝敗
                    away_wins = away_team_node.get('leagueRecord', {}).get('wins', 0)
                    away_losses = away_team_node.get('leagueRecord', {}).get('losses', 0)
                    home_wins = home_team_node.get('leagueRecord', {}).get('wins', 0)
                    home_losses = home_team_node.get('leagueRecord', {}).get('losses', 0)
                    
                    away_record = f"{away_wins}-{away_losses}"
                    home_record = f"{home_wins}-{home_losses}"
                    
                    # --- 【新功能】挖掘深度球隊數據 (從 team.record 節點擷取) ---
                    away_team_detail = away_team_node.get("team", {})
                    home_team_detail = home_team_node.get("team", {})
                    
                    # 這裡處理 API 回傳的智慧防錯，有時 record 會放在陣列或單一物件中
                    away_rec_data = away_team_detail.get("record", {})
                    home_rec_data = home_team_detail.get("record", {})
                    
                    # 數據提取：勝率、分區排名、勝差、連勝/連敗、賽季總得失分
                    away_pct = away_rec_data.get("winningPercentage", "-")
                    away_div_rank = away_rec_data.get("divisionRank", "-")
                    away_gb = away_rec_data.get("gamesBack", "-")
                    away_streak = away_rec_data.get("streak", {}).get("streakCode", "-") # e.g., "W3" or "L1"
                    away_season_runs = away_rec_data.get("runsScored", "-")
                    away_season_allowed = away_rec_data.get("runsAgainst", "-")
                    
                    home_pct = home_rec_data.get("winningPercentage", "-")
                    home_div_rank = home_rec_data.get("divisionRank", "-")
                    home_gb = home_rec_data.get("gamesBack", "-")
                    home_streak = home_rec_data.get("streak", {}).get("streakCode", "-")
                    home_season_runs = home_rec_data.get("runsScored", "-")
                    home_season_allowed = home_rec_data.get("runsAgainst", "-")
                    
                    # 4. 擷取先發投手資料 (左右投)
                    away_pitcher_node = away_team_node.get("probablePitcher", {})
                    home_pitcher_node = home_team_node.get("probablePitcher", {})
                    
                    away_pitcher_name = away_pitcher_node.get("fullName", "TBD")
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
                    
                    # 6. 組裝擴充後的完整 JSON 結構
                    all_days_data[target_date_key]["games"].append({
                        "game_time": tw_dt.strftime("%H:%M"),
                        "game_status": status_detailed,       # 比賽狀態 (e.g., Final, In Progress, Postponed)
                        "is_live_or_final": status_abstract,  # 用於前端判斷 (Live/Final/Preview)
                        
                        # 客隊完整數據
                        "away_team": away_team,
                        "away_record": away_record,
                        "away_runs": away_runs,               # 當場比賽得分
                        "away_stats": {
                            "win_percentage": away_pct,       # 勝率 (e.g., .550)
                            "division_rank": away_div_rank,   # 分區排名
                            "games_back": away_gb,            # 勝差
                            "streak": away_streak,            # 連勝/連敗狀態
                            "season_runs_scored": away_season_runs,   # 賽季總得分
                            "season_runs_allowed": away_season_allowed # 賽季總失分
                        },
                        "away_pitcher": {"name": f"{away_pitcher_name} {away_pitcher_hand}".strip()},
                        
                        # 主隊完整數據
                        "home_team": home_team,
                        "home_record": home_record,
                        "home_runs": home_runs,               # 當場比賽得分
                        "home_stats": {
                            "win_percentage": home_pct,
                            "division_rank": home_div_rank,
                            "games_back": home_gb,
                            "streak": home_streak,
                            "season_runs_scored": home_season_runs,
                            "season_runs_allowed": home_season_allowed
                        },
                        "home_pitcher": {"name": f"{home_pitcher_name} {home_pitcher_hand}".strip()}
                    })
                except Exception as game_error:
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
        
    print(f"【數據超級強化版】已成功產出包含戰績排名、連勝敗、賽季得失分與投手細節的 data.json！")

if __name__ == "__main__":
    main()