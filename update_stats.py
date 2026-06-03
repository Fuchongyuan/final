import json
import requests
from datetime import datetime, timedelta

def get_mlb_weeks_games():
    """
    修正版：由比賽時間決定日期，確保 +8 時區正確歸類
    """
    # 抓取範圍拉寬一點，確保涵蓋到跨日賽程
    start_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = (datetime.utcnow() + timedelta(days=8)).strftime("%Y-%m-%d")
    
    # 抓取 API
    url = f"https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1&startDate={start_date}&endDate={end_date}&hydrate=team,probablePitcher"
    
    all_days_data = {}
    
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            res_data = response.json()
            # 遍歷 API 給的所有日期節點
            for date_node in res_data.get("dates", []):
                for game in date_node.get("games", []):
                    # 1. 解析 UTC 時間並轉為台灣時間 (+8)
                    utc_dt = datetime.strptime(game.get("gameDate"), "%Y-%m-%dT%H:%M:%SZ")
                    tw_dt = utc_dt + timedelta(hours=8)
                    
                    # 2. 【關鍵修正】：以台灣時間作為 Key
                    tw_date_key = tw_dt.strftime("%Y-%m-%d")
                    
                    # 如果這天還沒建立過，先初始化
                    if tw_date_key not in all_days_data:
                        all_days_data[tw_date_key] = {
                            "day_label": tw_dt.strftime("%m/%d"),
                            "weekday_label": ["週一", "週二", "週三", "週四", "週五", "週六", "週日"][tw_dt.weekday()],
                            "games": []
                        }
                    
                    # 3. 填入比賽資訊
                    all_days_data[tw_date_key]["games"].append({
                        "game_time": tw_dt.strftime("%H:%M"),
                        "away_team": game["teams"]["away"]["team"]["name"],
                        "home_team": game["teams"]["home"]["team"]["name"],
                        "away_record": f"{game['teams']['away']['leagueRecord']['wins']}-{game['teams']['away']['leagueRecord']['losses']}",
                        "home_record": f"{game['teams']['home']['leagueRecord']['wins']}-{game['teams']['home']['leagueRecord']['losses']}",
                        "away_pitcher": {"name": game["teams"]["away"].get("probablePitcher", {}).get("fullName", "TBD")},
                        "home_pitcher": {"name": game["teams"]["home"].get("probablePitcher", {}).get("fullName", "TBD")}
                    })
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
    
    # 寫入 json 檔案
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print(f"【深度抓取完畢】已成功解鎖一週賽事詳細數據並存入 data.json！")

if __name__ == "__main__":
    main()