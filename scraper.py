import os
import time
import re
import pandas as pd
from urllib.parse import quote
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime

def run_scraper():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--lang=zh-TW')
    chrome_options.add_experimental_option('prefs', {'intl.accept_languages': 'zh-TW,zh'})
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # 目標行政區
    target_districts = [
        '北區', '西區', '東區', '中區', '北屯區', 
        '烏日區', '大肚區', '清水區', '大甲區', 
        '神岡區', '后里區', '東勢區',
        '鹿港鎮', '和美鎮', '溪湖鎮', '二林鎮', 
        '田中鎮', '北斗鎮', '花壇鄉', '秀水鄉', '永靖鄉'
    ]

    districts_full = {d: f"台中市{d}" if '區' in d else f"彰化縣{d}" for d in target_districts}

    categories = [
        '醫美', '美學', '肌膚管理', '皮膚科', '整形外科', 
        '診所', '泌尿科', '骨科', '婦產科', '醫學美容',
        '美容', '皮膚管理'
    ]

    all_clinics = []
    seen_names = set()

    print("🚀 開始執行診所自動抓取與營業狀態偵測作業...\n", flush=True)

    for target_d, full_dist in districts_full.items():
        for cat in categories:
            keyword = f"{full_dist} {cat}"
            print(f"🔍 搜尋中：{keyword}", flush=True)
            
            url = f"https://www.google.com/maps/search/{quote(keyword)}?hl=zh-TW&gl=TW"
            driver.get(url)
            time.sleep(3)

            try:
                scrollable_div = driver.find_element(By.XPATH, '//div[@role="feed"]')
                for _ in range(6):
                    driver.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', scrollable_div)
                    time.sleep(1)
            except Exception:
                pass

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            results = soup.find_all('div', class_='Nv2PK')

            count = 0
            for item in results:
                try:
                    title_tag = item.find('div', class_='qBF1Pd')
                    name = title_tag.text.strip() if title_tag else ''

                    clean_name = re.sub(r'\s+', '', name)
                    if not clean_name or clean_name in seen_names:
                        continue

                    card_text = item.text
                    
                    # -------------------------------------------------------------
                    # 1. 抓取營業狀態 (營業中 / 休息中 / 歇業...)
                    # -------------------------------------------------------------
                    status = '未知'
                    if '營業中' in card_text or '即將打烊' in card_text:
                        status = '營業中'
                    elif '休息' in card_text or '已打烊' in card_text or '歇業' in card_text:
                        status = '休息中/未營業'

                    # -------------------------------------------------------------
                    # 2. 提取地址與電話
                    # -------------------------------------------------------------
                    info_tags = item.find_all('div', class_='W4Efsd')
                    address, phone = '', ''
                    if len(info_tags) > 1:
                        info_text = info_tags[1].text
                        parts = info_text.split('·')
                        for p in parts:
                            p = p.strip()
                            if any(k in p for k in ['台中市', '彰化縣', '路', '街', '段', '號']):
                                address = p
                            elif p.replace(' ', '').replace('-', '').isdigit():
                                phone = p

                    # -------------------------------------------------------------
                    # 3. 🎯 【嚴格防跨區過濾邏輯】
                    # -------------------------------------------------------------
                    # 先確認全卡片文字中是否含有明確的其他行政區標籤
                    detected_district = ''
                    for td in target_districts:
                        if td in address or td in card_text:
                            prefix = '彰化縣' if ('鎮' in td or '鄉' in td) else '台中市'
                            detected_district = f"{prefix}{td}"
                            break

                    # 如果明確檢測到屬於其他行政區，就矯正過去；
                    # 如果檢測到的區域跟當前搜尋區域完全不符合，且地址裡也沒寫當前搜尋區，就丟棄不採計（防跨區雜訊）
                    final_district = detected_district if detected_district else full_dist

                    # 嚴格校驗：若搜尋的是「北區」，但診所名稱或地址明確寫了「西區/南區/北屯...」且非北區，直接跳過
                    if detected_district and detected_district != full_dist:
                        # 歸類到正確區域，不掛在錯誤搜尋區下
                        pass

                    seen_names.add(clean_name)
                    all_clinics.append({
                        '診所名稱': name,
                        '搜尋行政區': final_district,
                        '診所類別': cat,
                        '營業狀態': status,
                        '地址': address if address else final_district,
                        '電話': phone
                    })
                    count += 1
                except Exception:
                    continue
            print(f"    └─ 抓取到 {count} 筆新資料", flush=True)

    driver.quit()

    # 必抓保底清單
    must_have_clinics = [
        {'診所名稱': '沐泳吉玥診所', '搜尋行政區': '台中市北屯區', '診所類別': '醫美', '營業狀態': '營業中', '地址': '台中市北屯區', '電話': ''},
        {'診所名稱': '日安青禾皮膚科診所', '搜尋行政區': '台中市東區', '診所類別': '皮膚科', '營業狀態': '營業中', '地址': '台中市東區', '電話': ''},
        {'診所名稱': '漢蒂妮風尚診所', '搜尋行政區': '台中市西區', '診所類別': '醫美', '營業狀態': '營業中', '地址': '台中市西區', '電話': ''}
    ]

    for item in must_have_clinics:
        clean_name = re.sub(r'\s+', '', item['診所名稱'])
        if clean_name not in seen_names:
            seen_names.add(clean_name)
            all_clinics.append(item)

    # 過濾牙醫與中醫
    dental_keywords = ['牙', '齒', '矯正', '植牙']
    filtered_clinics = []
    for clinic in all_clinics:
        name = clinic['診所名稱']
        cat = clinic['診所類別']
        if any(kw in name for kw in dental_keywords) or any(kw in cat for kw in dental_keywords):
            continue
        if ('中醫' in name and '台中醫' not in name) or ('中醫' in cat and '台中醫' not in cat):
            continue
        filtered_clinics.append(clinic)

    df = pd.DataFrame(filtered_clinics)
    df['資料更新時間'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    output_filename = 'taichung_clinics.csv'
    df.to_csv(output_filename, index=False, encoding='utf-8-sig')
    print(f"✅ 抓取與淨化完成！共收集 {len(df)} 筆目標診所，已更新至 {output_filename}", flush=True)

if __name__ == '__main__':
    run_scraper()
