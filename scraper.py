import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


# 実行開始時間を記録
start_time = time.time()

# 最大実行時間（秒単位） 6時間より少し短く（5時間で保存）
MAX_EXECUTION_TIME = 5 * 60 * 60  # 5時間 = 18000秒

def init_driver():
    """
    ヘッドレスChromeのドライバーを初期化する関数
    """
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # ログ出力を有効にするオプション
    options.add_argument("--enable-logging")
    options.add_argument("--v=1")
    service = Service(ChromeDriverManager().install(), log_path="chromedriver.log")
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(600)
    return driver

def scrape_data():
    """スクレイピング実行"""
    all_records = []

    for page in range(1, 61):
        # 経過時間をチェックし、5時間超えたら強制的に途中保存
        elapsed_time = time.time() - start_time
        if elapsed_time > MAX_EXECUTION_TIME:
            print("⚠️ 5時間経過！途中データを保存して終了します。")
            save_data(all_records, partial=True)
            return  # ここで強制終了

        print(f"【検索ページ取得】ページ {page}")
        driver = init_driver()
        driver.get(f"https://tabelog.com/rstLst/{page}/?Srt=D&SrtT=nod")
        time.sleep(5)  # 適切な待機時間を入れる
        elements = driver.find_elements(By.CSS_SELECTOR, 'div.list-rst.js-bookmark.js-rst-cassette-wrap.js-done')
        detail_urls = [el.get_attribute("data-detail-url") for el in elements if el.get_attribute("data-detail-url")]
        driver.quit()

        for url in detail_urls:
            record = scrape_detail_page(url)
            if record:
                all_records.append(record)

    # すべてのデータを保存
    save_data(all_records)

def scrape_detail_page(url):
    """個別ページから情報を取得"""
    driver = init_driver()
    driver.get(url)
    time.sleep(5)

    record = {"URL": url, "店名": "", "ジャンル": "", "予約・お問い合わせ": "", "住所": ""}
    try:
        record["店名"] = driver.find_element(By.XPATH, '//th[normalize-space()="店名"]/following-sibling::td//span').text.strip()
    except:
        record["店名"] = "Not Found"
    try:
        record["ジャンル"] = driver.find_element(By.XPATH, '//th[normalize-space()="ジャンル"]/following-sibling::td//span').text.strip()
    except:
        record["ジャンル"] = "Not Found"
    try:
        record["予約・お問い合わせ"] = driver.find_element(By.XPATH, '//th[contains(text(),"予約・")]/following-sibling::td').text.strip()
    except:
        record["予約・お問い合わせ"] = "Not Found"
    try:
        record["住所"] = driver.find_element(By.XPATH, '//th[normalize-space()="住所"]/following-sibling::td//p[contains(@class,"rstinfo-table__address")]').text.strip()
    except:
        record["住所"] = "Not Found"

    driver.quit()
    return record

def save_data(data, partial=False):
    """データをCSVとして保存"""
    df = pd.DataFrame(data)
    filename = "data_partial.csv" if partial else "data.csv"
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"✅ {filename} にデータを保存しました！（{len(df)}件）")

if __name__ == "__main__":
    scrape_data()