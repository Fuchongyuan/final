import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def parse_mlb_time(time_str):
    """
    將 RotoWire 的美東時間字串（例如 "1:05 PM"）
    轉換為當天（或隔天）的台灣時間字串 (UTC+8)
    """
    try:
        time_str = time_str.strip()
        if not time_str:
            return "時間未定"
            
        # 取得目前美東大約日期基準 (UTC-4 夏令時間)
        est_now = datetime.utcnow() - timedelta(hours=4) 
        
        # 解析網頁上的時間 (例如 1:05 PM)
        parsed_time = datetime.strptime(time_str, "%I:%M %p")
        
        # 組合出完整的美東比賽時間
        est_game_datetime = est_now.replace(
            hour=parsed_time.hour, 
            minute=parsed_time.minute, 
            second=0, 
            microsecond=0
        )
        
        # 美東轉台灣時間 (+12 小時)
        tw_game_datetime = est_game_datetime + timedelta(hours=12)
        
        weekdays = ["一", "二", "三", "四", "五", "六", "日"]
        weekday_str = weekdays[tw_game_datetime.weekday()]
        
        return tw_game_datetime.strftime(f"%Y-%m-%d ({weekday_str}) %H:%M")
    except Exception:
        return time_str if time_str else "時間未定"

def get_mlb_games():
    url = "https://www.rotowire.com/baseball/odds.php"
    
    # 模擬真實瀏覽器標頭，防止被防爬蟲機制阻擋
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://www.google.com/'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"無法存取網站，HTTP 狀態碼: {response.status_code}")
            return []
            
        # 使用 lxml 解析器，速度更快更穩定
        soup = BeautifulSoup(response.text, 'lxml')
        games_list = []
        game_cards = soup.select('.odds-box') 
        
        for card in game_cards:
            try:
                away_row = card.select_one('.line-top')
                home_row = card.select_one('.line-bottom')
                if not away_row or not home_row:
                    continue
                
                # 抓取並轉換比賽時間
                time_el = card.select_one('.odds-meta__time')
                raw_time = time_el.text.strip() if time_el else ""
                tw_time_str = parse_mlb_time(raw_time)
                
                # 抓取隊名
                away_team = away_row.select_one('.odds-team a').text.strip() if away_row.select_one('.odds-team a') else "Unknown"
                home_team = home_row.select_one('.odds-team a').text.strip() if home_row.select_one('.odds-team a') else "Unknown"
                
                # 客隊先發投手與數據解析
                away_pitcher_element = away_row.select_one('.odds-pitcher')
                away_pitcher_name, away_era, away_whip = "TBD", "N/A", "N/A"
                if away_pitcher_element and away_pitcher_element.select_one('a'):
                    away_pitcher_name = away_pitcher_element.select_one('a').text.strip()
                    stats_text = away_pitcher_element.text.replace(away_pitcher_name, "").strip().strip('()')
                    if ',' in stats_text:
                        away_era, away_whip = [s.strip() for s in stats_text.split(',')]

                # 主隊先發投手與數據解析
                home_pitcher_element = home_row.select_one('.odds-pitcher')
                home_pitcher_name, home_era, home_whip = "TBD", "N/A", "N/A"
                if home_pitcher_element and home_pitcher_element.select_one('a'):
                    home_pitcher_name = home_pitcher_element.select_one('a').text.strip()
                    stats_text = home_pitcher_element.text.replace(home_pitcher_name, "").strip().strip('()')
                    if ',' in stats_text:
                        home_era, home_whip = [s.strip() for s in stats_text.split(',')]

                games_list.append({
                    "game_time": tw_time_str,
                    "away_team": away_team,
                    "home_team": home_team,
                    "away_pitcher": {"name": away_pitcher_name, "era": away_era, "whip": away_whip},
                    "home_pitcher": {"name": home_pitcher_name, "era": home_era, "whip": home_whip}
                })
            except Exception:
                continue 
                
        return games_list
    except Exception as e:
        print(f"爬蟲發生錯誤: {e}")
        return []

def main():
    # 取得當前台灣時間 (UTC+8) 作為更新時間戳記
    tw_time = datetime.utcnow() + timedelta(hours=8)
    
    data = {
        "last_updated": tw_time.strftime('%Y-%m-%d %H:%M'),
        "games": get_mlb_games()
    }
    
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print(f"成功抓取 {len(data['games'])} 場比賽數據。")

if __name__ == "__main__":
    main()