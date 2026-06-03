import json
import requests
from datetime import datetime, timedelta

def get_mlb_weeks_games():
    # 直接抓取未來 7 天，不做任何時區偏移
    start_date = datetime.utcnow().strftime("%Y-%m-%d")
    end_date = (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate={start_date}&endDate={end_date}&hydrate=team,probablePitcher"
    
    all_days_data = {}
    response = requests.get(url).json()
    
    # 直接以 API 的 officialDate 作為唯一歸類基準
    for date_node in response.get("dates", []):
        official_date = date_node.get("date") # 這是 MLB 官方定義的「比賽日」
        
        games_list = []
        for game in date_node.get("games", []):
            # 直接使用 API 給的 gameDate 時間字串，不做任何加減
            raw_time = game.get("gameDate").split('T')[1].replace('Z', '') 
            
            games_list.append({
                "game_time": raw_time, # 顯示原始 UTC 時間
                "away_team": game["teams"]["away"]["team"]["name"],
                "home_team": game["teams"]["home"]["team"]["name"],
                "away_record": f"{game['teams']['away']['leagueRecord']['wins']}-{game['teams']['away']['leagueRecord']['losses']}",
                "home_record": f"{game['teams']['home']['leagueRecord']['wins']}-{game['teams']['home']['leagueRecord']['losses']}",
                "away_pitcher": {"name": game["teams"]["away"].get("probablePitcher", {}).get("fullName", "TBD")},
                "home_pitcher": {"name": game["teams"]["home"].get("probablePitcher", {}).get("fullName", "TBD")}
            })
            
        all_days_data[official_date] = {
            "day_label": official_date,
            "weekday_label": "MLB Date",
            "games": games_list
        }
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