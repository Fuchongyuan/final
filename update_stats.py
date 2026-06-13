import json
import traceback
from datetime import datetime, timedelta
import urllib.request
import pybaseball as pyb

def fetch_mlb_dashboard_data():
    print("🚀 [MLB 官方核心] 開始執行即時賽程抓取與多維度指標降級快取...")

    # 初始化標準 JSON 資料結構
    result_data = {
        "meta": {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "engine": "mlb-official-api-v3"
        },
        "dates": {}
    }

    # 抓取前後一整週（共 15 天）擴展大面板，讓你的選單更豐富
    today = datetime.now()
    date_list = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(-7, 8)]

    # 建立一個球隊縮寫對照表，將官方的 Full Name 轉換成你前端 Logo 用的雙字元三字元簡稱
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

    # 預先抓取本賽季全聯盟的團隊防禦率（ERA）大表做備用
    team_p_stats = None
    try:
        print("📈 正在讀取 pybaseball 賽季進階防禦率指標...")
        team_p_stats = pyb.team_pitching(today.year)
    except Exception:
        print("⚠️ pybaseball 賽季防禦率超時，本輪將自動啟用降級橫線顯示。")

    for target_date in date_list:
        print(f"📅 正在連線官方 API 讀取日期：{target_date} ...")
        result_data["dates"][target_date] = []

        try:
            # 呼叫大聯盟官方最穩定的 Stats API
            url = f"https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1&date={target_date}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            
            with urllib.request.urlopen(req, timeout=7) as response:
                api_data = json.loads(response.read().decode('utf-8'))
                
            dates_list = api_data.get("dates", [])
            if not dates_list:
                continue
                
            games = dates_list[0].get("games", [])
            for game in games:
                # 提取球隊全名並轉換縮寫
                away_full = game.get("teams", {}).get("away", {}).get("team", {}).get("name", "")
                home_full = game.get("teams", {}).get("home", {}).get("team", {}).get("name", "")
                
                away_slug = team_name_map.get(away_full, "TBD")
                home_slug = team_name_map.get(home_full, "TBD")

                # 解析比賽狀態
                abstract_status = game.get("status", {}).get("abstractGameState", "Upcoming")
                detailed_status = game.get("status", {}).get("detailedState", "Upcoming")
                
                # 安全獲取比分
                away_score = game.get("teams", {}).get("away", {}).get("score", None)
                home_score = game.get("teams", {}).get("home", {}).get("score", None)

                # 格式化美東比賽時間字串
                game_time_str = game.get("gameDate", "")
                display_time = "10:10 AM"
                if game_time_str:
                    try:
                        # 轉為可讀的簡單時間字串
                        dt_obj = datetime.strptime(game_time_str, "%Y-%m-%dT%H:%M:%SZ") + timedelta(hours=8)
                        display_time = dt_obj.strftime("%H:%M") + " (台灣)"
                    except Exception:
                        pass

                # 建立標準防呆預設字典
                game_entry = {
                    "home_team": home_slug,
                    "away_team": away_slug,
                    "home_score": home_score,
                    "away_score": away_score,
                    "status": "Final" if abstract_status == "Final" or detailed_status == "賽事結束" else "Upcoming",
                    "time": display_time,
                    "pitchers": {
                        "away": game.get("teams", {}).get("away", {}).get("probablePitcher", {}).get("fullName", "未定 (TBD)"),
                        "home": game.get("teams", {}).get("home", {}).get("probablePitcher", {}).get("fullName", "未定 (TBD)")
                    },
                    "metrics": {
                        "h_era": "-", "a_era": "-"
                    }
                }

                # 整合進階防禦率指標
                if team_p_stats is not None and not team_p_stats.empty:
                    try:
                        h_p_row = team_p_stats[team_p_stats['Team'] == home_slug]
                        a_p_row = team_p_stats[team_p_stats['Team'] == away_slug]
                        if not h_p_row.empty:
                            game_entry["metrics"]["h_era"] = f"{float(h_p_row.iloc[0].get('ERA', 0)):.2f}"
                        if not a_p_row.empty:
                            game_entry["metrics"]["a_era"] = f"{float(a_p_row.iloc[0].get('ERA', 0)):.2f}"
                    except Exception:
                        pass

                result_data["dates"][target_date].append(game_entry)

        except Exception as e:
            print(f"⚠️ 解析日期 {target_date} 發生錯誤，自動跳過該日: {str(e)}")

    # 寫入本地 data.json 
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=4)

    print("🏁 [資料同步完畢] data.json 已經完美更新，內含 15 天大聯盟核心數據！")

if __name__ == "__main__":
    fetch_mlb_dashboard_data()