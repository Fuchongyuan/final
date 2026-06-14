import json
import urllib.request
from datetime import datetime, timedelta

def get_json(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode('utf-8'))
    except:
        return {}

def fetch_mlb_dashboard_data():
    print("🚀 [V15 強化版] 強制解析 gamePk，解決進行中賽事投手顯示 TBD 問題...")
    
    result_data = {"meta": {"last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, "dates": {}}
    today = datetime.now()
    
    for i in range(0, 3):
        target_dt = today + timedelta(days=i)
        date_str = target_dt.strftime("%Y-%m-%d")
        result_data["dates"][date_str] = []
        
        # 1. 先抓當日所有比賽的清單
        sched_url = f"https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1&date={date_str}"
        sched_data = get_json(sched_url)
        
        for date_entry in sched_data.get("dates", []):
            for game in date_entry.get("games", []):
                game_pk = game.get("gamePk")
                
                # 2. 針對每一場比賽，直接去敲該場比賽的詳細 API (這保證能拿到投手資訊)
                detail_url = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/feed/live"
                game_data = get_json(detail_url)
                
                # 解析詳細數據
                game_info = game_data.get("gameData", {})
                teams = game_info.get("teams", {})
                players = game_info.get("players", {})
                
                # 投手資訊：從 matchUp 中取得
                matchup = game_info.get("probablePitchers", {})
                away_p_id = matchup.get("away", {}).get("id")
                home_p_id = matchup.get("home", {}).get("id")
                
                away_p_name = players.get(f"ID{away_p_id}", {}).get("fullName", "未定 (TBD)") if away_p_id else "未定 (TBD)"
                home_p_name = players.get(f"ID{home_p_id}", {}).get("fullName", "未定 (TBD)") if home_p_id else "未定 (TBD)"
                
                # 隊伍縮寫
                away_slug = game_info.get("teams", {}).get("away", {}).get("abbreviation", "TBD")
                home_slug = game_info.get("teams", {}).get("home", {}).get("abbreviation", "TBD")
                
                # 狀態
                status = game_info.get("status", {}).get("detailedState", "Scheduled")
                
                result_data["dates"][date_str].append({
                    "home_team": home_slug, "away_team": away_slug,
                    "status": "Live" if status in ["In Progress", "Warm-up"] else ("Final" if status == "Final" else "Upcoming"),
                    "time": game_info.get("datetime", {}).get("time", "--:--"),
                    "pitchers": {
                        "away_starter": away_p_name,
                        "home_starter": home_p_name
                    }
                })

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=4)
    print("🏁 [V15 完成] 已成功解析各場 gamePk，TBD 已排除。")

if __name__ == "__main__":
    fetch_mlb_dashboard_data()