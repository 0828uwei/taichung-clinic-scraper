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

def run_scraper():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--lang=zh-TW')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    # 使用 webdriver-manager 自動下載並匹配與當前 Chrome 相符的 ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # 定義所有目標行政區（簡稱，用於地址比對）
    target_districts = [
        '北區', '西區', '東區', '中區', '北屯區', 
        '烏日區', '大肚區', '清水區', '大甲區', 
        '神岡區', '后里區', 
        '鹿港鎮', '和美鎮', '溪湖鎮', '二林鎮', 
        '田中鎮', '北斗鎮', '花壇鄉', '秀水鄉', '永靖鄉'
    ]

    # 自動組合全名（台中市/彰化縣）
    districts = [f"台中市{d}" if '區' in d else f"彰化縣{d}" for d in target_districts]

    # 搜尋關鍵字類別
    categories = [
        '醫美', '美學', '肌膚管理', '皮膚科', '整形外科', 
        '診所', '泌尿科', '骨科', '婦產科', '醫學美容',
        '美容', '皮膚管理'
    ]

    all_clinics = []
    seen_names = set()  # 純診所名稱（去空格）做唯一去重判斷

    print("🚀 開始執行診所自動抓取作業...\n", flush=True)

    for dist in districts:
        for cat in categories:
            keyword = f"{dist} {cat}"
            print(f"🔍 搜尋中：{keyword}", flush=True)
            
            url = f"https://www.google.com/maps/search/{quote(keyword)}"
            driver.get(url)
            time.sleep(3)

            try:
                scrollable_div = driver.find_element(By.XPATH, '//div[@role="feed"]')
                for _ in range(8):
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

                    # 利用去空格後的診所名稱做唯一 Key，徹底解決重複問題
                    clean_name = re.sub(r'\s+', '', name)
                    if not clean_name or clean_name in seen_names:
                        continue

                    info_tags = item.find_all('div', class_='W4Efsd')
                    address, phone = '', ''
                    if len(info_tags) > 1:
                        info_text = info_tags[1].text
                        parts = info_text.split('·')
                        for p in parts:
                            p = p.strip()
                            if '台中市' in p or '彰化縣' in p or '區' in p or '鄉' in p or '鎮' in p:
                                address = p
                            elif p.replace(' ', '').replace('-', '').isdigit():
                                phone = p

                    # 根據實際地址自動校正行政區，防止跨區推播污染
                    real_district = ''
                    for td in target_districts:
                        if td in address:
                            prefix = '彰化縣' if ('鎮' in td or '鄉' in td) else '台中市'
                            real_district = f"{prefix}{td}"
                            break

                    final_district = real_district if real_district else dist

                    seen_names.add(clean_name)
                    all_clinics.append({
                        '診所名稱': name,
                        '搜尋行政區': final_district,  # 使用校正後的真實行政區
                        '診所類別': cat,
                        '地址': address,
                        '電話': phone
                    })
                    count += 1
                except Exception:
                    continue
            print(f"    └─ 抓取到 {count} 筆新資料", flush=True)

    driver.quit()

    # 必抓保底清單
    must_have_clinics = [
        {
            '診所名稱': '沐泳吉玥診所',
            '搜尋行政區': '台中市北屯區',
            '診所類別': '醫美',
            '地址': '台中市北屯區',
            '電話': ''
        },
        {
            '診所名稱': '日安青禾皮膚科診所',
            '搜尋行政區': '台中市東區',
            '診所類別': '皮膚科',
            '地址': '台中市東區',
            '電話': ''
        },
        {
            '診所名稱': '漢蒂妮風尚診所',
            '搜尋行政區': '台中市西區',
            '診所類別': '醫美',
            '地址': '台中市西區',
            '電話': ''
        }
    ]

    for item in must_have_clinics:
        clean_name = re.sub(r'\s+', '', item['診所名稱'])
        if clean_name not in seen_names:
            seen_names.add(clean_name)
            all_clinics.append(item)
            print(f"📌 強制補入重點店家：{item['診所名稱']}", flush=True)

    # -------------------------------------------------------------
    # 🎯 【全新新增】：過濾牙醫相關診所
    # -------------------------------------------------------------
    dental_keywords = ['牙', '齒', '矯正', '植牙']
    filtered_clinics = []
    dental_count = 0

    for clinic in all_clinics:
        name = clinic['診所名稱']
        cat = clinic['診所類別']
        
        # 只要名稱或類別含有牙醫關鍵字，就跳過不納入
        if any(kw in name for kw in dental_keywords) or any(kw in cat for kw in dental_keywords):
            dental_count += 1
            continue
        
        filtered_clinics.append(clinic)

    print(f"\n🧹 已自動幫你過濾掉 {dental_count} 筆牙醫診所資料！", flush=True)

    # 輸出 CSV
    df = pd.DataFrame(filtered_clinics)
    output_filename = 'taichung_clinics.csv'
    df.to_csv(output_filename, index=False, encoding='utf-8-sig')
    print(f"✅ 抓取與淨化完成！共收集 {len(df)} 筆目標診所/工作室，檔案已儲存至 {output_filename}", flush=True)

if __name__ == '__main__':
    run_scraper()
