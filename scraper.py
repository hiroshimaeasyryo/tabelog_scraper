import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# 実行開始時間を記録
start_time = time.time()

# 最大実行時間（秒単位）6時間より少し短く（5時間で保存）
# 試験的に短めに設定
MAX_EXECUTION_TIME = 1 * 10 * 60  # 10分

def init_driver():
    """ヘッドレスChromeのドライバーを初期化"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(600)
    return driver

def get_search_url(page_number):
    return f"https://tabelog.com/rstLst/{page_number}/?Srt=D&SrtT=nod"

def scrape_search_page(driver, page_number):
    """検索ページから個別ページのURLを取得"""
    url = get_search_url(page_number)
    print(f"【検索ページ取得】{url}")
    try:
        driver.get(url)
        time.sleep(10)  # 適切な待機時間
        elements = driver.find_elements(By.CSS_SELECTOR, 'div.list-rst.js-bookmark.js-rst-cassette-wrap.js-done')
        return [el.get_attribute("data-detail-url") for el in elements if el.get_attribute("data-detail-url")]
    except Exception as e:
        print(f"検索ページの読み込みエラー: {url} - {e}")
        return []

def scrape_detail_page_with_retry(url, max_retries=15):
    """個別ページから情報を取得（最大15回リトライ）"""
    for attempt in range(max_retries):
        driver = None
        try:
            print(f"【個別ページ取得】{url} (Attempt {attempt+1})")
            driver = init_driver()
            driver.get(url)
            time.sleep(10)  # ページ読み込み待機

            record = {'URL': url, '店名': '', 'ジャンル': '', '予約・お問い合わせ': '', '住所': ''}
            try:
                record['店名'] = driver.find_element(By.XPATH, '//th[normalize-space()="店名"]/following-sibling::td//span').text.strip()
            except:
                record['店名'] = 'Not Found'
            try:
                record['ジャンル'] = driver.find_element(By.XPATH, '//th[normalize-space()="ジャンル"]/following-sibling::td//span').text.strip()
            except:
                record['ジャンル'] = 'Not Found'
            try:
                record['予約・お問い合わせ'] = driver.find_element(By.XPATH, '//th[contains(text(),"予約・")]/following-sibling::td').text.strip()
            except:
                record['予約・お問い合わせ'] = 'Not Found'
            try:
                record['住所'] = driver.find_element(By.XPATH, '//th[normalize-space()="住所"]/following-sibling::td//p[contains(@class,"rstinfo-table__address")]').text.strip()
            except:
                record['住所'] = 'Not Found'

            driver.quit()
            return record
        except Exception as e:
            print(f"Error processing {url} on attempt {attempt+1}: {e}")
            if driver:
                driver.quit()
            if attempt == max_retries - 1:
                print(f"Max retries reached for {url}, skipping.")
                return None
            time.sleep(10)  # リトライ前に少し待機
    return None

def load_previous_data(filename):
    """以前のCSVデータを読み込む（存在しない場合は空のDataFrameを返す）"""
    if os.path.exists(filename):
        return pd.read_csv(filename)
    return pd.DataFrame()

def compare_and_mark(new_df, old_df):
    """URLをキーに前回データと比較し、新規・更新をマーク"""
    new_df['Status'] = ''
    if old_df.empty:
        new_df['Status'] = 'New'
    else:
        for idx, row in new_df.iterrows():
            url = row['URL']
            if url in old_df['URL'].values:
                old_row = old_df[old_df['URL'] == url].iloc[0]
                if (row['店名'] != old_row['店名'] or
                    row['ジャンル'] != old_row['ジャンル'] or
                    row['予約・お問い合わせ'] != old_row['予約・お問い合わせ'] or
                    row['住所'] != old_row['住所']):
                    new_df.at[idx, 'Status'] = 'Update'
            else:
                new_df.at[idx, 'Status'] = 'New'
    return new_df

def save_data(data, partial=False):
    """データをCSVとして保存"""
    df = pd.DataFrame(data)
    filename = "data_partial.csv" if partial else "data.csv"
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"✅ {filename} にデータを保存しました！（{len(df)}件）")

def main():
    all_records = []
    try:
        for page in range(1, 61):
            # 5時間経過時点で強制保存
            elapsed_time = time.time() - start_time
            if elapsed_time > MAX_EXECUTION_TIME:
                print("⚠️ 5時間経過！途中データを保存して終了します。")
                save_data(all_records, partial=True)
                return  

            search_driver = init_driver()
            detail_urls = scrape_search_page(search_driver, page)
            search_driver.quit()

            for detail_url in detail_urls:
                record = scrape_detail_page_with_retry(detail_url, max_retries=5)
                if record:
                    all_records.append(record)
    except Exception as e:
        print("予期せぬエラーが発生しました:", e)
    finally:
        new_df = pd.DataFrame(all_records)
        previous_df = load_previous_data('data.csv')
        result_df = compare_and_mark(new_df, previous_df)
        save_data(result_df)

if __name__ == '__main__':
    main()
