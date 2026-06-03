import json
import requests
from datetime import datetime, timedelta

def get_mlb_weeks_games():
    tw_now = datetime.utcnow() + timedelta(hours=8)
    all_days_data = {}
    
    # 迴圈連續抓取 7 天
    for i in range(7):
        target_date = tw_now + timedelta(days=i)
        date_str = target_date.strftime('%Y-%m-%d')
        
        weekdays = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
        day_label = "今天" if i == 0 else ("明天" if i == 1 else target_date.strftime('%m/%d'))
        weekday_label = weekdays[target_date.weekday()]
        
        # ⚡ 關鍵修改：加上 &hydrate=team,probablePitcher 參數，強制 MLB 官方釋出戰績與先發投手欄位
        url = f"https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1&date={date_str}&hydrate=team,probablePitcher"
        print(f"正在深度抓取 {date_str} ({weekday_label}) 的完整賽事、戰績與先發...")
        
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
                            tw_time_str = tw_dt.strftime("%H:%M")
                            
                            teams = game.get("teams", {})
                            away_data = teams.get("away", {})
                            home_data = teams.get("home", {})
                            
                            # 抓取隊名
                            away_team = away_data.get("team", {}).get("name", "Unknown")
                            home_team = home_data.get("team", {}).get("name", "Unknown")
                            
                            # 抓取解鎖後的球隊即時勝敗戰績
                            away_wins = away_data.get("leagueRecord", {}).get("wins", 0)
                            away_losses = away_data.get("leagueRecord", {}).get("losses", 0)
                            home_wins = home_data.get("leagueRecord", {}).get("wins", 0)
                            home_losses = home_data.get("leagueRecord", {}).get("losses", 0)
                            
                            # 抓取解鎖後的真實預計先發投手姓名
                            away_pitcher = away_data.get("probablePitcher", {}).get("fullName", "TBD")
                            home_pitcher = home_data.get("probablePitcher", {}).get("fullName", "TBD")
                            
                            games_list.append({
                                "game_time": tw_time_str,
                                "away_team": away_team,
                                "away_record": f"{away_wins}-{away_losses}",
                                "home_team": home_team,
                                "home_record": f"{home_wins}-{home_losses}",
                                "away_pitcher": {"name": away_pitcher},
                                "home_pitcher": {"name": home_pitcher}
                            })
                        except Exception:
                            continue
        except Exception as e:
            print(f"抓取 {date_str} 失敗: {e}")
            
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
        
    print(f"【深度抓取完畢】已成功解鎖一週賽事詳細數據！")

if __name__ == "__main__":
    main()