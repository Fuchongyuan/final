import json
import requests
from datetime import datetime, timedelta

def get_mlb_weeks_games():
    """
    全聯盟完整版：抓取未來 7 天內所有球隊的所有對戰賽程
    """
    # 抓取範圍：從今天開始往後算 7-8 天，確保涵蓋完整一週
    start_date = datetime.utcnow().strftime("%Y-%m-%d")
    end_date = (datetime.utcnow() + timedelta(days=8)).strftime("%Y-%m-%d")
    
    # 核心修正：sportId=1 代表 MLB，此 API 會回傳該區間內全聯盟所有比賽
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate={start_date}&endDate={end_date}&hydrate=team,probablePitcher,linescore,status"
    
    all_days_data = {}
    
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            print(f"API 請求失敗: {response.status_code}")
            return all_days_data
            
        res_data = response.json()
        
        # 遍歷回傳的所有日期
        for date_node in res_data.get("dates", []):
            date_key = date_node.get("date")
            
            # 初始化該日期的資料容器
            if date_key not in all_days_data:
                all_days_data[date_key] = {
                    "day_label": datetime.strptime(date_key, "%Y-%m-%d").strftime("%m/%d"),
                    "weekday_label": ["週一", "週二", "週三", "週四", "週五", "週六", "週日"][datetime.strptime(date_key, "%Y-%m-%d").weekday()],
                    "games": []
                }
            
            # 遍歷該日期下的所有比賽
            for game in date_node.get("games", []):
                try:
                    # 處理時間與隊伍名稱
                    utc_dt = datetime.strptime(game.get("gameDate"), "%Y-%m-%dT%H:%M:%SZ")
                    tw_dt = utc_dt + timedelta(hours=8)
                    
                    teams = game.get("teams", {})
                    away = teams.get("away", {})
                    home = teams.get("home", {})
                    
                    game_info = {
                        "game_time": tw_dt.strftime("%H:%M"),
                        "away_team": away.get("team", {}).get("name", "Unknown"),
                        "home_team": home.get("team", {}).get("name", "Unknown"),
                        "away_pitcher": away.get("probablePitcher", {}).get("fullName", "TBD"),
                        "home_pitcher": home.get("probablePitcher", {}).get("fullName", "TBD"),
                        "status": game.get("status", {}).get("detailedState", "Scheduled")
                    }
                    
                    all_days_data[date_key]["games"].append(game_info)
                    
                except Exception as e:
                    continue
                    
    except Exception as e:
        print(f"抓取失敗: {e}")
            
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
        
    print(f"【成功】已更新 data.json，包含未來一週所有對戰組合！")

if __name__ == "__main__":
    main()