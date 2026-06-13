import json
import traceback
from datetime import datetime, timedelta
import urllib.request

def fetch_mlb_dashboard_data():
    print("🚀 [MLB 全能完全體 V12] 換源機制啟動：改由 ESPN 核心 API 注入穩定數據庫...")

    result_data = {
        "meta": {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "engine": "espn-mlb-backbone-v12"
        },
        "dates": {}
    }

    # ESPN API 主要是用 YYYYMMDD 格式查詢
    today = datetime.now()
    
    # 產出未來 8 天的日期清單
    for i in range(0, 8):
        target_dt = today + timedelta(days=i)
        date_str_dash = target_dt.strftime("%Y-%m-%d")  # 前端頁籤用
        date_str_espn = target_dt.strftime("%Y%m%d")    # ESPN API 用
        
        print(f"📅 正在同步日期：{date_str_dash} (ESPN: {date_str_espn}) ...")
        result_data["dates"][date_str_dash] = []
        
        url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={date_str_espn}"
        
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                api_data = json.loads(response.read().decode('utf-8'))
                
            events = api_data.get("events", [])
            for event in events:
                competitions = event.get("competitions", [])
                if not competitions:
                    continue
                
                comp = competitions[0]
                status_type = event.get("status", {}).get("type", {}).get("name", "STATUS_SCHEDULED")
                
                # 狀態轉換
                if status_type == "STATUS_FINAL":
                    game_status = "Final"
                elif status_type == "STATUS_IN_PROGRESS":
                    game_status = "Live"
                else:
                    game_status = "Upcoming"
                    
                display_time = event.get("status", {}).get("type", {}).get("detail", "TBD")
                # 簡單格式化台灣時間顯示
                if "AM" in display_time or "PM" in display_time:
                    display_time = display_time + " (美東)"
                
                # 隊伍與比分、統計數據解析
                competitors = comp.get("competitors", [])
                home_obj = {}
                away_obj = {}
                
                for team in competitors:
                    t_side = team.get("homeAway", "home")
                    t_info = {
                        "slug": team.get("team", {}).get("abbreviation", "TBD"),
                        "full_name": team.get("team", {}).get("displayName", ""),
                        "logo": team.get("team", {}).get("logo", ""),
                        "record": team.get("records", [{}])[0].get("summary", "0-0") if team.get("records") else "0-0",
                        "score": int(team.get("score", 0)),
                        "hits": 0,
                        "errors": 0,
                        "stats_summary": {
                            "AVG": ".000", "OBP": ".000", "SLG": ".000", "HR": "0", "R": "0"
                        }
                    }
                    
                    # 撈取球隊的單場 H/E (安打/失誤)
                    linescore = team.get("linescores", [])
                    # 這裡 ESPN 若有給 linescore 則加總或抓取單場值
                    # 為了簡單與相容，直接從團隊統計或事件中抓
                    
                    # 撈取 ESPN 精華：團隊賽季打擊數據 (保底用)
                    # ESPN 的 statistics 通常會附帶球隊目前的累積數據
                    t_stats = team.get("statistics", [])
                    for s in t_stats:
                        s_name = s.get("name")
                        if s_name == "battingAverage": t_info["stats_summary"]["AVG"] = s.get("displayValue", ".000")
                        elif s_name == "onBasePercentage": t_info["stats_summary"]["OBP"] = s.get("displayValue", ".000")
                        elif s_name == "sluggingPercentage": t_info["stats_summary"]["SLG"] = s.get("displayValue", ".000")
                        elif s_name == "homeRuns": t_info["stats_summary"]["HR"] = s.get("displayValue", "0")
                        elif s_name == "runs": t_info["stats_summary"]["R"] = s.get("displayValue", "0")
                        elif s_name == "hits": t_info["hits"] = int(s.get("displayValue", 0)) if game_status != "Upcoming" else 0
                        elif s_name == "errors": t_info["errors"] = int(s.get("displayValue", 0)) if game_status != "Upcoming" else 0

                    if t_side == "home":
                        home_obj = t_info
                    else:
                        away_obj = t_info

                # 投手解析邏輯
                prob_away = {"name": "未定 (TBD)", "meta": "RHP", "stats": "賽季: -.-- ERA"}
                prob_home = {"name": "未定 (TBD)", "meta": "RHP", "stats": "賽季: -.-- ERA"}
                curr_away = {"name": "尚未登板", "stats": "單場: -"}
                curr_home = {"name": "尚未登板", "stats": "單場: -"}

                # ESPN 賽前會放上預計先發選手
                notes = comp.get("notes", [])
                # 撈取先發投手名字
                for athlete in comp.get("leaders", []):
                    # 尋找與投手相關的動態欄位
                    a_name = athlete.get("leaders", [{}])[0].get("athlete", {}).get("displayName", "")
                    a_stat = athlete.get("leaders", [{}])[0].get("displayValue", "")
                    if "pitching" in athlete.get("name", "") or "P" in athlete.get("name", ""):
                        # 簡單分配
                        if not prob_away["name"] or prob_away["name"] == "未定 (TBD)":
                            prob_away["name"] = a_name
                            prob_away["stats"] = a_stat
                        else:
                            prob_home["name"] = a_name
                            prob_home["stats"] = a_stat

                game_entry = {
                    "home_team": home_obj.get("slug", "TBD"),
                    "away_team": away_obj.get("slug", "TBD"),
                    "home_logo": home_obj.get("logo", ""),
                    "away_logo": away_obj.get("logo", ""),
                    "home_record": home_obj.get("record", "0-0"),
                    "away_record": away_obj.get("record", "0-0"),
                    "status": game_status,
                    "time": display_time,
                    "rhe": {
                        "away": {"R": away_obj.get("score", 0), "H": away_obj.get("hits", 0), "E": away_obj.get("errors", 0)},
                        "home": {"R": home_obj.get("score", 0), "H": home_obj.get("hits", 0), "E": home_obj.get("errors", 0)}
                    },
                    "pitchers": {
                        "probable_away": prob_away, "probable_home": prob_home,
                        "current_away": curr_away, "current_home": curr_home
                    },
                    # 💡 核心改動：改放團隊最新的強大火力的賽季三圍，賽前抓不到打線時絕對有數據看！
                    "team_stats": {
                        "away": away_obj.get("stats_summary"),
                        "home": home_obj.get("stats_summary")
                    }
                }
                result_data["dates"][date_str_dash].append(game_entry)
                
        except Exception as e:
            print(f"⚠️ 解析日期 {date_str_dash} 錯誤: {str(e)}")
            traceback.print_exc()

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=4)
    print("🏁 [ESPN 數據洗腦完畢] data.json 導出成功！")

if __name__ == "__main__":
    fetch_mlb_dashboard_data()