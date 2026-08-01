import os
import time
import pandas as pd
from urllib.parse import quote
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def run_scraper():
    # 設定 Headless Chrome (針對 GitHub Actions 運作環境)
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--lang=zh-TW')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    driver = webdriver.Chrome(options=chrome_options)

    # 定義目標行政區與診所科別類別
    districts = ['台中市北區', '台中市西區', '台中市東區', '台中市中區', '台中市烏日區', '台中市霧峰區', '台中市清水區', '台中市大甲區', '台中市神岡區', '台中市后里區', '台中市石岡區', '台中市外埔區', '台中市東勢區', '台中市新社區', '台中市北屯區', '台中市烏日區', '台中市大肚區''彰化縣鹿港鎮', '彰化縣和美鎮', '彰化縣溪湖鎮', '彰化縣二林鎮', 
        '彰化縣田中鎮', '彰化縣北斗鎮', '彰化縣花壇鄉', '彰化縣秀水鄉',
        '彰化縣伸港鄉', '彰化縣大村鄉', '彰化縣永靖鄉', '彰化縣蒲鹽鄉']
    categories = ['醫美診所', '肌膚管理', '整形外科', '皮膚科', '泌尿科', '骨科', '皮膚管理', '美學診所', '診所', '外科', '婦產科', '整形', '醫美', '整外', '雷射', '除毛', '音波', '電波', '拉提', '包皮', '醫學美容', '肉毒', '玻尿酸', '皮膚']

    all_clinics = []
    seen_keys = set()

    print("🚀 開始執行台中診所自動抓取作業...\n")

    for dist in districts:
        for cat in categories:
            keyword = f"{dist} {cat}"
            print(f"🔍 搜尋中：{keyword}")
            
            url = f"https://www.google.com/maps/search/{quote(keyword)}"
            driver.get(url)
            time.sleep(3)

            # 模擬向下滾動選單載入更多診所
            try:
                scrollable_div = driver.find_element(By.XPATH, '//div[@role="feed"]')
                for _ in range(5):
                    driver.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', scrollable_div)
                    time.sleep(1.5)
            except Exception:
                pass

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            results = soup.find_all('div', class_='Nv2PK')

            count = 0
            for item in results:
                try:
                    title_tag = item.find('div', class_='qBF1Pd')
                    name = title_tag.text.strip() if title_tag else ''

                    info_tags = item.find_all('div', class_='W4Efsd')
                    address, phone = '', ''
                    if len(info_tags) > 1:
                        info_text = info_tags[1].text
                        parts = info_text.split('·')
                        for p in parts:
                            p = p.strip()
                            if '台中市' in p or '區' in p:
                                address = p
                            elif p.replace(' ', '').replace('-', '').isdigit():
                                phone = p

                    unique_key = f"{name}_{dist}"
                    if name and unique_key not in seen_keys:
                        seen_keys.add(unique_key)
                        all_clinics.append({
                            '診所名稱': name,
                            '搜尋行政區': dist,
                            '診所類別': cat,
                            '地址': address,
                            '電話': phone
                        })
                        count += 1
                except Exception:
                    continue
            print(f"   └─ 抓取到 {count} 筆新資料")

    driver.quit()

    # 輸出為 CSV 檔案
    df = pd.DataFrame(all_clinics)
    output_filename = 'taichung_clinics.csv'
    df.to_csv(output_filename, index=False, encoding='utf-8-sig')
    print(f"\n✅ 抓取完成！共收集 {len(df)} 筆不重複診所，檔案已儲存至 {output_filename}")

if __name__ == '__main__':
    run_scraper()
