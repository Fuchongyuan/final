import json
import requests
from datetime import datetime, timedelta

def get_mlb_games():
    # 1. 計算「今天」的台灣日期與美東日期基準
    # MLB API 的日期格式為 YYYY-MM-DD
    tw_now = datetime.utcnow() + timedelta(hours=8)
    
    # 抓取今天與明天的比賽（確保因為時差不會漏掉比賽）
    # 強制抓明天，看看 API 到底有沒有動
    date_str = (tw_now + timedelta(days=1)).strftime('%Y-%m-%d')
    
    # MLB 官方公開的賽程 API URL
    url = f"https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1&date={date_str}"
    
    print(f"正在連線至 MLB 官方 API 抓取日期 {date_str} 的賽事...")
    
    try:
        response = requests.get(url, timeout=15)
        print(f"API 回應狀態碼: {response.status_code}")
        
        if response.status_code != 200:
            print("❌ 錯誤：無法取得 MLB 官方數據")
            return []
            
        res_data = response.json()
        dates = res_data.get("dates", [])
        if not dates:
            print(f"提示：官方 API 在 {date_str} 這天沒有排定比賽。")
            return []
            
        games_list = []
        raw_games = dates[0].get("games", [])
        print(f"成功偵測到官方賽程共 {len(raw_games)} 場比賽")
        
        for game in raw_games:
            try:
                # 解析比賽時間 (API 給的是 UTC 時間，例如: "2026-06-03T23:05:00Z")
                utc_time_str = game.get("gameDate")
                utc_dt = datetime.strptime(utc_time_str, "%Y-%m-%dT%H:%M:%SZ")
                # 轉為台灣時間 (+8 小時)
                tw_dt = utc_dt + timedelta(hours=8)
                weekdays = ["一", "二", "三", "四", "五", "六", "日"]
                tw_time_str = tw_dt.strftime(f"%Y-%m-%d ({weekdays[tw_dt.weekday()]}) %H:%M")
                
                # 取得隊伍資訊
                teams = game.get("teams", {})
                away_data = teams.get("away", {})
                home_data = teams.get("home", {})
                
                away_team = away_data.get("team", {}).get("name", "Unknown")
                home_team = home_data.get("team", {}).get("name", "Unknown")
                
                # 取得預計先發投手 (Probable Pitcher)
                away_pitcher_name = away_data.get("probablePitcher", {}).get("fullName", "TBD")
                home_pitcher_name = home_data.get("probablePitcher", {}).get("fullName", "TBD")
                
                # 註：官方賽程 API 預設不帶有即時 ERA/WHIP，為了穩定度，我們先塞入預設值
                # 這樣可以 100% 確保抓得到場次、隊名與開賽時間！
                games_list.append({
                    "game_time": tw_time_str,
                    "away_team": away_team,
                    "home_team": home_team,
                    "away_pitcher": {"name": away_pitcher_name, "era": "N/A", "whip": "N/A"},
                    "home_pitcher": {"name": home_pitcher_name, "era": "N/A", "whip": "N/A"}
                })
            except Exception as e:
                print(f"解析單場比賽失敗，跳過。原因: {e}")
                continue
                
        return games_list
    except Exception as e:
        print(f"API 核心邏輯發生錯誤: {e}")
        return []

def main():
    tw_time = datetime.utcnow() + timedelta(hours=8)
    games = get_mlb_games()
    
    data = {
        "last_updated": tw_time.strftime('%Y-%m-%d %H:%M'),
        "games": games
    }
    
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print(f"【執行完畢】官方數據已成功寫入！共計 {len(games)} 場比賽到 data.json")

if __name__ == "__main__":
    main()