import json
import traceback
from datetime import datetime, timedelta
import pandas as pd
import pybaseball as pyb


def fetch_mlb_dashboard_data():
    print("🚀 [PyBaseball 核心] 開始執行全自動化數據快取與降級調度...")

    # 初始化最健全的標準 JSON 資料結構
    result_data = {
        "meta": {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "engine": "pybaseball-automation-v2",
        },
        "dates": {},
    }

    # 獲取最近 3 天的日期（昨天、今天、明天），提供橫向選單切換
    today = datetime.now()
    date_list = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in [-1, 0, 1]]

    for target_date in date_list:
        print(f"📅 正在處理日期：{target_date} 的賽事排程...")
        result_data["dates"][target_date] = []

        # --- 容錯第一層：獲取當天全聯盟排程與基本對戰 ---
        try:
            try:
                # 獲取當天所有的比賽清單（安全調用）
                day_games = pyb.bref_daily_scheduled_and_results(target_date)
            except Exception:
                print(
                    f"⚠️ 無法從 bref 取得 {target_date} 原始數據，切換至備用空值。"
                )
                continue

            if day_games is None or day_games.empty:
                print(f"ℹ️ {target_date} 沒有任何排定賽事。")
                continue

            # 疊代當天的每一場比賽
            for _, row in day_games.iterrows():
                # 建立基礎字典，給予標準防呆預設值（橫線）
                game_entry = {
                    "home_team": str(row.get("Home", "TBD")),
                    "away_team": str(row.get("Away", "TBD")),
                    "home_score": None,
                    "away_score": None,
                    "status": "Upcoming",
                    "time": str(row.get("Time", "10:10 AM")),
                    "home_record": "-",
                    "away_record": "-",
                    "pitchers": {"home": "未定 (TBD)", "away": "未定 (TBD)"},
                    "metrics": {"h_avg": "-", "a_avg": "-", "h_era": "-", "a_era": "-"},
                }

                # 解析比分（如果比賽已經打完的話）
                try:
                    if (
                        pd.notna(row.get("R_home"))
                        and pd.notna(row.get("R_away"))
                    ):
                        game_entry["home_score"] = int(row["R_home"])
                        game_entry["away_score"] = int(row["R_away"])
                        game_entry["status"] = "Final"
                except Exception:
                    pass  # 抓不到比分就保持 None，不影響基本對戰卡片顯示

                # --- 容錯第二層：進階多維度指標抓取 ---
                home_slug = game_entry["home_team"]
                away_slug = game_entry["away_team"]

                try:
                    current_year = today.year
                    # 獲取整年團隊投球數據快取，用來抓取兩隊的 ERA
                    team_p_stats = pyb.team_pitching(current_year)
                    if not team_p_stats.empty:
                        h_p_row = team_p_stats[
                            team_p_stats["Team"] == home_slug
                        ]
                        a_p_row = team_p_stats[
                            team_p_stats["Team"] == away_slug
                        ]

                        if not h_p_row.empty:
                            game_entry["metrics"]["h_era"] = f"{float(h_p_row.iloc[0].get('ERA', 0)):.2f}"
                        if not a_p_row.empty:
                            game_entry["metrics"]["a_era"] = f"{float(a_p_row.iloc[0].get('ERA', 0)):.2f}"
                except Exception:
                    pass  # 某一項大數據庫超時或不支援，默默跳過，確保整場比賽資料不當機

                # 將此容錯處理後的乾淨比賽物件塞入當天賽程中
                result_data["dates"][target_date].append(game_entry)

        except Exception as e:
            print(f"❌ 解析日期 {target_date} 發生全局非預期錯誤: {str(e)}")
            traceback.print_exc()

    # --- 第三步：寫入 json 檔案 ---
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=4)

    print("🏁 [資料快取完畢] data.json 已經完美生成，具備極高容錯防護機制！")


if __name__ == "__main__":
    fetch_mlb_dashboard_data()