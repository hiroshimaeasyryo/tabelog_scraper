import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

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

def get_search_url(page_number):
    return f"https://tabelog.com/rstLst/{page_number}/?Srt=D&SrtT=nod"

def scrape_search_page(driver, page_number):
    """
    検索ページから個別ページのURLを取得する
    """
    url = get_search_url(page_number)
    print(f"【検索ページ取得】{url}")
    try:
        driver.get(url)
    except Exception as e:
        print(f"検索ページの読み込みエラー: {url} - {e}")
        return []
    time.sleep(30)
    elements = driver.find_elements(By.CSS_SELECTOR, 'div.list-rst.js-bookmark.js-rst-cassette-wrap.js-done')
    detail_urls = []
    for el in elements:
        detail_url = el.get_attribute("data-detail-url")
        if detail_url:
            detail_urls.append(detail_url)
    return detail_urls

# def save_screenshot_on_error(driver, url):
#     """
#     エラー発生時にスクリーンショットを保存する
#     """
#     timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
#     filename = f"screenshot_{timestamp}.png"
#     try:
#         driver.save_screenshot(filename)
#         print(f"{url} でエラー発生時のスクリーンショットを保存: {filename}")
#     except Exception as e:
#         print(f"スクリーンショット保存失敗: {e}")

def scrape_detail_page_with_retry(url, max_retries=15):
    """
    個別ページから必要情報を取得する関数
    エラーが発生した場合は、最大 max_retries 回までリトライし、リトライごとにドライバーを初期化する
    """
    for attempt in range(max_retries):
        driver = None
        try:
            print(f"【個別ページ取得】{url} (Attempt {attempt+1})")
            driver = init_driver()
            driver.get(url)
            time.sleep(30)  # ページ読み込み待機
            
            # 各情報の抽出
            record = {'URL': url, '店名': '', 'ジャンル': '', '予約・お問い合わせ': '', '住所': ''}
            try:
                elem = driver.find_element(By.XPATH, '//th[normalize-space()="店名"]/following-sibling::td//span')
                record['店名'] = elem.text.strip()
            except Exception as e:
                record['店名'] = 'Not Found'
            try:
                elem = driver.find_element(By.XPATH, '//th[normalize-space()="ジャンル"]/following-sibling::td//span')
                record['ジャンル'] = elem.text.strip()
            except Exception as e:
                record['ジャンル'] = 'Not Found'
            try:
                elem = driver.find_element(By.XPATH, '//th[contains(text(),"予約・")]/following-sibling::td')
                record['予約・お問い合わせ'] = elem.text.strip()
            except Exception as e:
                record['予約・お問い合わせ'] = 'Not Found'
            try:
                elem = driver.find_element(By.XPATH, '//th[normalize-space()="住所"]/following-sibling::td//p[contains(@class,"rstinfo-table__address")]')
                record['住所'] = elem.text.strip()
            except Exception as e:
                record['住所'] = 'Not Found'
            
            driver.quit()
            return record
        except Exception as e:
            print(f"Error processing {url} on attempt {attempt+1}: {e}")
            if driver:
                try:
                    # save_screenshot_on_error(driver, url)
                    driver.quit()
                except Exception as ex:
                    print(f"Driver quit error: {ex}")
            if attempt == max_retries - 1:
                print(f"Max retries reached for {url}, skipping.")
                return None
            time.sleep(10)  # リトライ前に少し待機
    return None


def load_previous_data(filename):
    """
    以前のCSVデータを読み込む（存在しない場合は空のDataFrameを返す）
    """
    if os.path.exists(filename):
        return pd.read_csv(filename)
    else:
        return pd.DataFrame()

def compare_and_mark(new_df, old_df):
    """
    URLをキーに前回データと比較し、以下の通りマークする
    - 新規レコード：'New'
    - 変更あり：'Update'
    - 変更なし：空文字列
    """
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
                    new_df.at[idx, 'Status'] = ''
            else:
                new_df.at[idx, 'Status'] = 'New'
    return new_df

def main():
    all_records = []
    try:
        # 各検索ページごとに新たなドライバーを初期化して処理する
        for page in range(1, 61):
            search_driver = init_driver()
            detail_urls = scrape_search_page(search_driver, page)
            search_driver.quit()
            for detail_url in detail_urls:
                record = scrape_detail_page_with_retry(detail_url, max_retries=5)
                if record:
                    all_records.append(record)
                else:
                    print(f"Failed to process {detail_url} after maximum retries.")
    except Exception as e:
        print("予期せぬエラーが発生しました:", e)
    finally:
        # ここまでに取得できたデータを CSV として出力する
        new_df = pd.DataFrame(all_records)
        previous_df = load_previous_data('data.csv')
        result_df = compare_and_mark(new_df, previous_df)
        result_df.to_csv('data.csv', index=False, encoding='utf-8-sig')
        print("途中経過を data.csv に保存しました。")

if __name__ == '__main__':
    main()