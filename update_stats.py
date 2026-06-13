import json
import traceback
from datetime import datetime, timedelta
import urllib.request
import pybaseball as pyb


def fetch_mlb_dashboard_data():
    print("🚀 [MLB 官方核心 V4] 啟動接下來一週賽程抓取 + 投手機制完全修復版...")

    # 初始化標準 JSON 資料結構
    result_data = {
        "meta": {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "engine": "mlb-official-api-v4-pitcher-fixed",
        },
        "dates": {},
    }

    # 🎯 修正一：只抓今天到接下來 7 天（共 8 天的未來賽程大面板）
    today = datetime.now()
    date_list = [
        (today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(0, 8)
    ]

    # 球隊縮寫對照表
    team_name_map = {
        "Arizona Diamondbacks": "AZ",
        "Atlanta Braves": "ATL",
        "Baltimore Orioles": "BAL",
        "Boston Red Sox": "BOS",
        "Chicago Cubs": "CHC",
        "Chicago White Sox": "CWS",
        "Cincinnati Reds": "CIN",
        "Cleveland Guardians": "CLE",
        "Colorado Rockies": "COL",
        "Detroit Tigers": "DET",
        "Houston Astros": "HOU",
        "Kansas City Royals": "KC",
        "Los Angeles Angels": "LAA",
        "Los Angeles Dodgers": "LAD",
        "Miami Marlins": "MIA",
        "Milwaukee Brewers": "MIL",
        "Minnesota Twins": "MIN",
        "New York Mets": "NYM",
        "New York Yankees": "NYY",
        "Oakland Athletics": "OAK",
        "Philadelphia Phillies": "PHI",
        "Pittsburgh Pirates": "PIT",
        "San Diego Padres": "SD",
        "San Francisco Giants": "SF",
        "Seattle Mariners": "SEA",
        "St. Louis Cardinals": "STL",
        "Tampa Bay Rays": "TB",
        "Texas Rangers": "TEX",
        "Toronto Blue Jays": "TOR",
        "Washington Nationals": "WSH",
    }

    # 預先抓取本賽季全聯盟的團隊防禦率（ERA）大表
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
            # 串接大聯盟 Stats API 詳盡模式 (加入 &hydrate=decisions 確保拿到勝敗投資訊)
            url = f"https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1&date={target_date}&hydrate=decisions"
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0"}
            )

            with urllib.request.urlopen(req, timeout=7) as response:
                api_data = json.loads(response.read().decode("utf-8"))

            dates_list = api_data.get("dates", [])
            if not dates_list:
                continue

            games = dates_list[0].get("games", [])
            for game in games:
                away_full = (
                    game.get("teams", {})
                    .get("away", {})
                    .get("team", {})
                    .get("name", "")
                )
                home_full = (
                    game.get("teams", {})
                    .get("home", {})
                    .get("team", {})
                    .get("name", "")
                )

                away_slug = team_name_map.get(away_full, "TBD")
                home_slug = team_name_map.get(home_full, "TBD")

                abstract_status = (
                    game.get("status", {}).get("abstractGameState", "Upcoming")
                )
                detailed_status = (
                    game.get("status", {}).get("detailedState", "Upcoming")
                )
                is_final = (
                    abstract_status == "Final" or detailed_status == "賽事結束"
                )

                # 🎯 修正二：動態投手機制修復
                away_pitcher = "未定 (TBD)"
                home_pitcher = "未定 (TBD)"

                if is_final:
                    # 如果比賽已經打完，probablePitcher 欄位會消失，我們改抓 decisions 欄位的勝投與敗投
                    decisions = game.get("decisions", {})
                    win_p = decisions.get("winner", {}).get("fullName", "-")
                    lose_p = decisions.get("loser", {}).get("fullName", "-")

                    # 判斷這場比賽誰贏，把勝投分給贏的球隊，敗投分給輸的球隊
                    away_score = game.get("teams", {}).get("away", {}).get("score", 0)
                    home_score = game.get("teams", {}).get("home", {}).get("score", 0)
                    if away_score > home_score:
                        away_pitcher = f"勝投: {win_p}"
                        home_pitcher = f"敗投: {lose_p}"
                    else:
                        away_pitcher = f"敗投: {lose_p}"
                        home_pitcher = f"勝投: {win_p}"
                else:
                    # 如果比賽還沒開始，正常抓取官方的預計先發投手
                    away_pitcher = (
                        game.get("teams", {})
                        .get("away", {})
                        .get("probablePitcher", {})
                        .get("fullName", "未定 (TBD)")
                    )
                    home_pitcher = (
                        game.get("teams", {})
                        .get("home", {})
                        .get("probablePitcher", {})
                        .get("fullName", "未定 (TBD)")
                    )

                # 格式化台灣時間
                game_time_str = game.get("gameDate", "")
                display_time = "10:10 AM"
                if game_time_str:
                    try:
                        dt_obj = datetime.strptime(
                            game_time_str, "%Y-%m-%dT%H:%M:%SZ"
                        ) + timedelta(hours=8)
                        display_time = dt_obj.strftime("%H:%M") + " (台灣)"
                    except Exception:
                        pass

                # 建立防呆字典
                game_entry = {
                    "home_team": home_slug,
                    "away_team": away_slug,
                    "home_score": game.get("teams", {})
                    .get("home", {})
                    .get("score", None),
                    "away_score": game.get("teams", {})
                    .get("away", {})
                    .get("score", None),
                    "status": "Final" if is_final else "Upcoming",
                    "time": display_time,
                    "pitchers": {"away": away_pitcher, "home": home_pitcher},
                    "metrics": {"h_era": "-", "a_era": "-"},
                }

                # 注入整季防禦率
                if team_p_stats is not None and not team_p_stats.empty:
                    try:
                        h_p_row = team_p_stats[team_p_stats["Team"] == home_slug]
                        a_p_row = team_p_stats[team_p_stats["Team"] == away_slug]
                        if not h_p_row.empty:
                            game_entry["metrics"]["h_era"] = f"{float(h_p_row.iloc[0].get('ERA', 0)):.2f}"
                        if not a_p_row.empty:
                            game_entry["metrics"]["a_era"] = f"{float(a_p_row.iloc[0].get('ERA', 0)):.2f}"
                    except Exception:
                        pass

                result_data["dates"][target_date].append(game_entry)

        except Exception as e:
            print(f"⚠️ 解析日期 {target_date} 發生錯誤: {str(e)}")

    # 寫入 data.json
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=4)

    print("🏁 [資料同步完畢] 接下來一週的對戰組合與投手修復資料已完美打包！")


if __name__ == "__main__":
    fetch_mlb_dashboard_data()