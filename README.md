# 台中診所自動抓取系統 (Taichung Clinic Scraper)

本專案使用 Python 與 GitHub Actions 自動抓取 Google Maps 上台中指定區域的診所清單（含醫美、肌膚管理、整形外科、皮膚科、泌尿科、骨科）。

## 檔案結構
- `scraper.py`: 爬蟲主程式
- `.github/workflows/main.yml`: GitHub Actions 自動化腳本
- `taichung_clinics.csv`: 抓取完成後的診所名單（執行後自動產生）

## 使用方式
1. 開啟 GitHub Actions 頁面。
2. 點擊 「Auto Run Clinic Scraper」。
3. 點擊右側 「Run workflow」 即可開始手動抓取。
