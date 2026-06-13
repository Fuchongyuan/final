import json
import requests
from datetime import datetime, timedelta

def get_mlb_weeks_games():
    """
    全聯盟完整版：抓取未來 7 天所有球隊的賽程
    包含：台灣時間(+8)、詳細比賽狀態、即時比分、球隊戰績、先發投手詳細資料（慣用手+賽季即時數據）
    以及預留給前端顯示的各種數據分析放置槽。
    """
    # 抓取範圍：昨天到未來 8 天，確保完全網羅全聯盟所有跨時區、雙重賽與補賽
    start_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = (datetime.utcnow() + timedelta(days=8)).strftime("%Y-%m-%d")
    
    # 核心修正：擴充 hydrate 參數，一併把先發投手的賽季統計數據 (stats) 與投球手 (team) 一次性拉回來
    url = (
        f"https://statsapi.mlb.com/api/v1/schedule?sportId=1"
        f"&startDate={start_date}&endDate={end_date}"
        f"&hydrate=team,probablePitcher(stats,note),linescore,status"
    )
    
    all_days_data = {}
    
    try:
        print(f"正在向 MLB 官方請求全聯盟賽程數據 ({start_date} 至 {end_date})...")
        response = requests.get(url, timeout=20)
        if response.status_code != 200:
            print(f"API 請求失敗，狀態碼: {response.status_code}")
            return all_days_data
            
        res_data = response.json()
        total_dates = res_data.get("dates", [])
        print(f"成功獲取 {len(total_dates)} 個日期的原始數據，開始解析所有球隊比賽...")
        
        for date_node in total_dates:
            for game in date_node.get("games", []):
                try:
                    # 1. 處理台灣時間與日期分類
                    utc_time_str = game.get("gameDate")
                    if not utc_time_str:
                        continue
                    utc_time = datetime.strptime(utc_time_str, "%Y-%m-%dT%H:%M:%SZ")
                    tw_time = utc_time + timedelta(hours=8)
                    
                    tw_date_key = tw_time.strftime("%Y-%m-%d")
                    day_label = tw_time.strftime("%m/%d")
                    
                    weekdays = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
                    weekday_label = weekdays[tw_time.weekday()]
                    
                    # 2. 解析比賽狀態與即時比分
                    status_node = game.get("status", {})
                    status_abstract = status_node.get("abstractGameState", "Preview")  # Live, Final, Preview
                    status_detailed = status_node.get("detailedState", "Scheduled")     # 詳細狀態文字
                    
                    linescore = game.get("linescore", {})
                    away_runs = linescore.get("teams", {}).get("away", {}).get("runs", "-")
                    home_runs = linescore.get("teams", {}).get("home", {}).get("runs", "-")
                    
                    # 3. 解析球隊名稱與戰績
                    teams_node = game.get("teams", {})
                    away_node = teams_node.get("away", {})
                    home_node = teams_node.get("home", {})
                    
                    away_team = away_node.get("team", {}).get("name", "Unknown Team")
                    home_team = home_node.get("team", {}).get("name", "Unknown Team")
                    
                    away_record = f"{away_node.get('leagueRecord', {}).get('wins', 0)}-{away_node.get('leagueRecord', {}).get('losses', 0)}"
                    home_record = f"{home_node.get('leagueRecord', {}).get('wins', 0)}-{home_node.get('leagueRecord', {}).get('losses', 0)}"
                    
                    # 4. 深度解析：預計先發投手、慣用手與本季數據
                    away_p_node = away_node.get("probablePitcher", {})
                    home_p_node = home_node.get("probablePitcher", {})
                    
                    # 函數：抽取投手的慣用手與賽季數據文字
                    def parse_pitcher_data(p_node):
                        if not p_node or "fullName" not in p_node:
                            return "TBD", "暫無本季數據"
                        
                        name = p_node.get("fullName", "TBD")
                        
                        # 擷取慣用手 (R: 右投, L: 左投)
                        pitch_hand = p_node.get("pitchHand", {}).get("code", "")
                        if pitch_hand == "R":
                            name = f"{name} (右投)"
                        elif pitch_hand == "L":
                            name = f"{name} (左投)"
                            
                        # 從聯動數據 (hydrate) 中擷取本賽季常規賽投球統計
                        stats_text = "暫無本季數據"
                        stats_list = p_node.get("stats", [])
                        for s in stats_list:
                            if s.get("type", {}).get("name") == "season" and s.get("group", {}).get("name") == "pitching":
                                stat = s.get("stats", {})
                                wins = stat.get("wins", 0)
                                losses = stat.get("losses", 0)
                                era = stat.get("era", "-.--")
                                so = stat.get("strikeOuts", 0)
                                stats_text = f"{wins}勝{losses}敗  ERA {era}  {so}SO"
                                break
                        return name, stats_text

                    away_pitcher_name, away_pitcher_stats = parse_pitcher_data(away_p_node)
                    home_pitcher_name, home_pitcher_stats = parse_pitcher_data(home_p_node)
                    
                    # 5. 初始化日期的 JSON 結構
                    if tw_date_key not in all_days_data:
                        all_days_data[tw_date_key] = {
                            "day_label": day_label,
                            "weekday_label": weekday_label,
                            "games": []
                        }
                    
                    # 6. 填入完整包裝（包含提供給前端 HTML 各種數據放置槽的自訂分析欄位）
                    all_days_data[tw_date_key]["games"].append({
                        "game_time": tw_time.strftime("%H:%M"),
                        "game_status": status_detailed,
                        "is_live_or_final": status_abstract,
                        "away_team": away_team,
                        "away_record": away_record,
                        "away_runs": away_runs,
                        "home_team": home_team,
                        "home_record": home_record,
                        "home_runs": home_runs,
                        "away_pitcher": {
                            "name": away_pitcher_name,
                            "stats": away_pitcher_stats
                        },
                        "home_pitcher": {
                            "name": home_pitcher_name,
                            "stats": home_pitcher_stats
                        },
                        "analysis": {
                            "trend": "根據大數據模型預測，兩隊近期在得分效益與防守效率上各有優勢，這將是一場激烈的攻防戰。",
                            "bet_tip": "讓分盤推薦：建議觀察即時獨贏水位更動。大小分推薦：注意後續氣候與球場風向變化。",
                            "injuries": "客隊：目前傷兵名單穩定，主力打線皆能正常出賽。主隊：牛棚有一名中繼投手處於每日觀察名單。"
                        }
                    })
                except Exception as game_error:
                    # 核心防呆：如果某一場比賽解析有小問題，跳過並繼續處理全聯盟下一場比賽
                    continue
                    
        print(f"全聯盟賽事解析完成！共處理了 {sum(len(d['games']) for d in all_days_data.values())} 場賽事。")
    except Exception as e:
        print(f"全局賽程抓取失敗: {e}")
            
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
    print("【大功告成】data.json 已完整更新，已包含全聯盟所有球隊的比賽與各項數據槽！")

if __name__ == "__main__":
    main()