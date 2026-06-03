import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def parse_mlb_time(time_str):
    try:
        time_str = time_str.strip()
        if not time_str:
            return "時間未定"
        est_now = datetime.utcnow() - timedelta(hours=4) 
        parsed_time = datetime.strptime(time_str, "%I:%M %p")
        est_game_datetime = est_now.replace(
            hour=parsed_time.hour, minute=parsed_time.minute, second=0, microsecond=0
        )
        tw_game_datetime = est_game_datetime + timedelta(hours=12)
        weekdays = ["一", "二", "三", "四", "五", "六", "日"]
        return tw_game_datetime.strftime(f"%Y-%m-%d ({weekdays[tw_game_datetime.weekday()]}) %H:%M")
    except Exception:
        return time_str if time_str else "時間未定"

def get_mlb_games():
    url = "https://www.rotowire.com/baseball/odds.php"
    
    # 升級版偽裝瀏覽器 Header
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }
    
    try:
        print("正在嘗試連線到 RotoWire...")
        response = requests.get(url, headers=headers, timeout=15)
        print(f"網頁回應狀態碼: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ 錯誤：被網站阻擋或伺服器異常，狀態碼為 {response.status_code}")
            return []
            
        soup = BeautifulSoup(response.text, 'lxml')
        
        # 嘗試尋找主要比賽區塊，若 .odds-box 找不到，嘗試抓取表格列
        game_cards = soup.select('.odds-box')
        if not game_cards:
            game_cards = soup.find_all('div', class_='odds-box')
            
        print(f"成功偵測到 {len(game_cards)} 場比賽區塊")
        
        games_list = []
        for index, card in enumerate(game_cards, 1):
            try:
                # 拆分上下列
                away_row = card.select_one('.line-top') or card.find('div', class_='line-top')
                home_row = card.select_one('.line-bottom') or card.find('div', class_='line-bottom')
                
                if not away_row or not home_row:
                    continue
                
                # 開賽時間
                time_el = card.select_one('.odds-meta__time')
                raw_time = time_el.text.strip() if time_el else ""
                tw_time_str = parse_mlb_time(raw_time)
                
                # 隊名 (相容超連結與非超連結模式)
                away_team_el = away_row.select_one('.odds-team a') or away_row.select_one('.odds-team')
                home_team_el = home_row.select_one('.odds-team a') or home_row.select_one('.odds-team')
                away_team = away_team_el.text.strip() if away_team_el else "Unknown"
                home_team = home_team_el.text.strip() if home_team_el else "Unknown"
                
                # 投手解析降級策略
                def parse_pitcher(row_el):
                    p_name, p_era, p_whip = "TBD", "N/A", "N/A"
                    p_el = row_el.select_one('.odds-pitcher') or row_el.find('div', class_='odds-pitcher')
                    if p_el:
                        a_tag = p_el.find('a')
                        if a_tag:
                            p_name = a_tag.text.strip()
                            stats = p_el.text.replace(p_name, "").strip().strip('()')
                        else:
                            # 處理沒有超連結只有純文字的情況
                            full_text = p_el.text.strip()
                            if '(' in full_text:
                                p_name = full_text.split('(')[0].strip()
                                stats = full_text.split('(')[1].strip(')')
                            else:
                                p_name = full_text if full_text else "TBD"
                                stats = ""
                        
                        if stats and ',' in stats:
                            parts = stats.split(',')
                            if len(parts) == 2:
                                p_era, p_whip = parts[0].strip(), parts[1].strip()
                    return p_name, p_era, p_whip

                away_name, away_era, away_whip = parse_pitcher(away_row)
                home_name, home_era, home_whip = parse_pitcher(home_row)

                games_list.append({
                    "game_time": tw_time_str,
                    "away_team": away_team,
                    "home_team": home_team,
                    "away_pitcher": {"name": away_name, "era": away_era, "whip": away_whip},
                    "home_pitcher": {"name": home_name, "era": home_era, "whip": home_whip}
                })
            except Exception as e:
                print(f"解析第 {index} 場比賽時跳過，原因: {e}")
                continue 
                
        return games_list
    except Exception as e:
        print(f"爬蟲核心邏輯發生崩潰: {e}")
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
        
    print(f"【執行完畢】最終成功寫入 {len(games)} 場比賽數據到 data.json")

if __name__ == "__main__":
    main()