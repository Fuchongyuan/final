import json
import requests
from datetime import datetime, timedelta

def get_mlb_weeks_games():
    # 取得台灣當前時間
    tw_now = datetime.utcnow() + timedelta(hours=8)
    
    # 建立一個可以用日期當 Key 的字典 (例如: {"2026-06-03": [...], "2026-06-04": [...]})
    all_days_data = {}
    
    # 迴圈連續抓取 7 天（從今天開始往後推 6 天）
    for i in range(7):
        target_date = tw_now + timedelta(days=i)
        date_str = target_date.strftime('%Y-%m-%d')
        
        # 產生星期幾的標籤 (例如: 週三)
        weekdays = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
        day_label = "今天" if i == 0 else ("明天" if i == 1 else target_date.strftime('%m/%d'))
        weekday_label = weekdays[target_date.weekday()]
        
        url = f"https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1&date={date_str}"
        print(f"正在抓取 {date_str} ({weekday_label}) 的賽事...")
        
        games_list = []
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                res_data = response.json()
                dates = res_data.get("dates", [])
                
                if dates:
                    raw_games = dates[0].get("games", [])
                    for game in raw_games:
                        try:
                            # 解析時間並轉為台灣時間
                            utc_time_str = game.get("gameDate")
                            utc_dt = datetime.strptime(utc_time_str, "%Y-%m-%dT%H:%M:%SZ")
                            tw_dt = utc_dt + timedelta(hours=8)
                            tw_time_str = tw_dt.strftime("%H:%M") # 網頁上只需要顯示幾點幾分
                            
                            teams = game.get("teams", {})
                            away_team = teams.get("away", {}).get("team", {}).get("name", "Unknown")
                            home_team = teams.get("home", {}).get("team", {}).get("name", "Unknown")
                            
                            away_pitcher = teams.get("away", {}).get("probablePitcher", {}).get("fullName", "TBD")
                            home_pitcher = teams.get("home", {}).get("probablePitcher", {}).get("fullName", "TBD")
                            
                            games_list.append({
                                "game_time": tw_time_str,
                                "away_team": away_team,
                                "home_team": home_team,
                                "away_pitcher": {"name": away_pitcher, "era": "N/A", "whip": "N/A"},
                                "home_pitcher": {"name": home_pitcher, "era": "N/A", "whip": "N/A"}
                            })
                        except Exception:
                            continue
        except Exception as e:
            print(f"抓取 {date_str} 失敗: {e}")
            
        # 即使當天沒比賽，也留個空陣列，方便前端畫出按鈕
        all_days_data[date_str] = {
            "day_label": day_label,
            "weekday_label": weekday_label,
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
    
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print("【執行完畢】已成功抓取未來一週賽事並分類寫入 data.json！")

if __name__ == "__main__":
    main()