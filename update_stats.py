import json
import requests
from datetime import datetime, timedelta

def get_mlb_weeks_games():
    # 抓取範圍拉寬，確保涵蓋到跨日賽程
    start_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = (datetime.utcnow() + timedelta(days=8)).strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate={start_date}&endDate={end_date}&hydrate=team,probablePitcher"
    
    all_days_data = {}
    response = requests.get(url).json()
    
    for date_node in response.get("dates", []):
        for game in date_node.get("games", []):
            # 1. 解析 UTC 時間轉為台灣時間 (+8)
            utc_dt = datetime.strptime(game.get("gameDate"), "%Y-%m-%dT%H:%M:%SZ")
            tw_dt = utc_dt + timedelta(hours=8)
            
            # 2. 【關鍵修改】：日期往後推 1 天作為 Key
            target_dt = tw_dt + timedelta(days=1)
            target_date_key = target_dt.strftime("%Y-%m-%d")
            
            # 初始化該日期結構
            if target_date_key not in all_days_data:
                all_days_data[target_date_key] = {
                    "day_label": target_dt.strftime("%m/%d"),
                    "weekday_label": ["週一", "週二", "週三", "週四", "週五", "週六", "週日"][target_dt.weekday()],
                    "games": []
                }
            
            # 3. 填入賽事 (game_time 顯示轉換後的台灣時間)
            all_days_data[target_date_key]["games"].append({
                "game_time": tw_dt.strftime("%H:%M"),
                "away_team": game["teams"]["away"]["team"]["name"],
                "home_team": game["teams"]["home"]["team"]["name"],
                "away_record": f"{game['teams']['away']['leagueRecord']['wins']}-{game['teams']['away']['leagueRecord']['losses']}",
                "home_record": f"{game['teams']['home']['leagueRecord']['wins']}-{game['teams']['home']['leagueRecord']['losses']}",
                "away_pitcher": {"name": game["teams"]["away"].get("probablePitcher", {}).get("fullName", "TBD")},
                "home_pitcher": {"name": game["teams"]["home"].get("probablePitcher", {}).get("fullName", "TBD")}
            })
            
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