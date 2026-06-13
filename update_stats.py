import json
import traceback
from datetime import datetime, timedelta
import urllib.request
import pybaseball as pyb

def fetch_mlb_dashboard_data():
    print("🚀 [MLB 官方核心 V5] 啟動『進行中賽事狀態與投手動態追蹤』優化版...")

    result_data = {
        "meta": {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "engine": "mlb-official-api-v5-live-fixed"
        },
        "dates": {}
    }

    # 抓取今天到接下來 7 天
    today = datetime.now()
    date_list = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(0, 8)]

    team_name_map = {
        "Arizona Diamondbacks": "AZ", "Atlanta Braves": "ATL", "Baltimore Orioles": "BAL",
        "Boston Red Sox": "BOS", "Chicago Cubs": "CHC", "Chicago White Sox": "CWS",
        "Cincinnati Reds": "CIN", "Cleveland Guardians": "CLE", "Colorado Rockies": "COL",
        "Detroit Tigers": "DET", "Houston Astros": "HOU", "Kansas City Royals": "KC",
        "Los Angeles Angels": "LAA", "Los Angeles Dodgers": "LAD", "Miami Marlins": "MIA",
        "Milwaukee Brewers": "MIL", "Minnesota Twins": "MIN", "New York Mets": "NYM",
        "New York Yankees": "NYY", "Oakland Athletics": "OAK", "Philadelphia Phillies": "PHI",
        "Pittsburgh Pirates": "PIT", "San Diego Padres": "SD", "San Francisco Giants": "SF",
        "Seattle Mariners": "SEA", "St. Louis Cardinals": "STL", "Tampa Bay Rays": "TB",
        "Texas Rangers": "TEX", "Toronto Blue Jays": "TOR", "Washington Nationals": "WSH"
    }

    # 加載整季防禦率
    team_p_stats = None
    try:
        print("📈 正在加載 pybaseball 賽季防禦率指標...")
        team_p_stats = pyb.team_pitching(today.year)
    except Exception:
        print("⚠️ pybaseball 賽季防禦率超時，啟用降級橫線顯示。")

    for target_date in date_list:
        print(f"📅 正在從 MLB API 讀取日期：{target_date} ...")
        result_data["dates"][target_date] = []

        try:
            # 詳盡模式：加入 decisions(勝敗投) 與 linescore(即時投打) 數據水分
            url = f"https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1&date={target_date}&hydrate=decisions,linescore"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            
            with urllib.request.urlopen(req, timeout=7) as response:
                api_data = json.loads(response.read().decode('utf-8'))
                
            dates_list = api_data.get("dates", [])
            if not dates_list:
                continue
                
            games = dates_list[0].get("games", [])
            for game in games:
                away_full = game.get("teams", {}).get("away", {}).get("team", {}).get("name", "")
                home_full = game.get("teams", {}).get("home", {}).get("team", {}).get("name", "")
                
                away_slug = team_name_map.get(away_full, "TBD")
                home_slug = team_name_map.get(home_full, "TBD")

                # 🎯 狀態精確三向分流
                abstract_status = game.get("status", {}).get("abstractGameState", "Upcoming") # Upcoming, Live, Final
                detailed_status = game.get("status", {}).get("detailedState", "Upcoming")
                
                final_keywords = ["Final", "Game Over", "Completed", "賽事結束"]
                live_keywords = ["Live", "In Progress", "Manager Challenge", "Delayed", "Warm-up", "正在進行", "熱身中"]
                
                if abstract_status in final_keywords or detailed_status in final_keywords:
                    game_status = "Final"
                elif abstract_status in live_keywords or detailed_status in live_keywords:
                    game_status = "Live"
                else:
                    game_status = "Upcoming"

                # 🎯 投手數據動態深挖
                away_pitcher = "未定 (TBD)"
                home_pitcher = "未定 (TBD)"

                if game_status == "Final":
                    # 已結束：抓勝敗投
                    decisions = game.get("decisions", {})
                    win_p = decisions.get("winner", {}).get("fullName", "-")
                    lose_p = decisions.get("loser", {}).get("fullName", "-")
                    
                    away_score = game.get("teams", {}).get("away", {}).get("score", 0)
                    home_score = game.get("teams", {}).get("home", {}).get("score", 0)
                    if away_score > home_score:
                        away_pitcher = f"勝投: {win_p}"
                        home_pitcher = f"敗投: {lose_p}"
                    else:
                        away_pitcher = f"敗投: {lose_p}"
                        home_pitcher = f"勝投: {win_p}"
                        
                elif game_status == "Live":
                    # 進行中：大聯盟會把先發投手放到 linescore 的 defense（防守方）中
                    linescore = game.get("linescore", {})
                    # 嘗試抓當前場上投手
                    current_pitcher = linescore.get("defense", {}).get("pitcher", {}).get("fullName")
                    
                    # 備用方案：如果進行中還能拿到 probablePitcher 就拿，拿不到就顯示「比賽進行中」或當前投手
                    p_away = game.get("teams", {}).get("away", {}).get("probablePitcher", {}).get("fullName")
                    p_home = game.get("teams", {}).get("home", {}).get("probablePitcher", {}).get("fullName")
                    
                    away_pitcher = p_away if p_away else (f"場上投手: {current_pitcher}" if current_pitcher and linescore.get("teams", {}).get("home", {}).get("isHitting") else "先發投手已登板")
                    home_pitcher = p_home if p_home else (f"場上投手: {current_pitcher}" if current_pitcher and linescore.get("teams", {}).get("away", {}).get("isHitting") else "先發投手已登板")
                
                else:
                    # 未開始：穩穩抓預計先發
                    away_pitcher = game.get("teams", {}).get("away", {}).get("probablePitcher", {}).get("fullName", "未定 (TBD)")
                    home_pitcher = game.get("teams", {}).get("home", {}).get("probablePitcher", {}).get("fullName", "未定 (TBD)")

                # 處理時間
                game_time_str = game.get("gameDate", "")
                display_time = "10:10 AM"
                if game_time_str:
                    try:
                        dt_obj = datetime.strptime(game_time_str, "%Y-%m-%dT%H:%M:%SZ") + timedelta(hours=8)
                        display_time = dt_obj.strftime("%H:%M") + " (台灣)"
                    except Exception:
                        pass

                game_entry = {
                    "home_team": home_slug,
                    "away_team": away_slug,
                    "home_score": game.get("teams", {}).get("home", {}).get("score", None),
                    "away_score": game.get("teams", {}).get("away", {}).get("score", None),
                    "status": game_status, # "Upcoming" | "Live" | "Final"
                    "time": display_time,
                    "pitchers": {
                        "away": away_pitcher,
                        "home": home_pitcher
                    },
                    "metrics": {
                        "h_era": "-", "a_era": "-"
                    }
                }

                if team_p_stats is not None and not team_p_stats.empty:
                    try:
                        h_p_row = team_p_stats[team_p_stats['Team'] == home_slug]
                        a_p_row = team_p_stats[team_p_stats['Team'] == away_slug]
                        if not h_p_row.empty: game_entry["metrics"]["h_era"] = f"{float(h_p_row.iloc[0].get('ERA', 0)):.2f}"
                        if not a_p_row.empty: game_entry["metrics"]["a_era"] = f"{float(a_p_row.iloc[0].get('ERA', 0)):.2f}"
                    except Exception: pass

                result_data["dates"][target_date].append(game_entry)

        except Exception as e:
            print(f"⚠️ 解析日期 {target_date} 發生錯誤: {str(e)}")

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=4)

    print("🏁 [資料同步完畢] 進行中狀態與投手動態追蹤已完美部署！")

if __name__ == "__main__":
    fetch_mlb_dashboard_data()