# create_site.py

import random
from sys import _xoptions
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains    # ← Thêm dòng này
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support import expected_conditions as EC
import time

def get_random_user_agent():    
    chrome_version = f"{random.randint(2, 200)}.0.0.0"  # Tạo số ngẫu nhiên từ 2.0.0.0 - 200.0.0.0
    return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36"

def create_driver(): 
    chrome_options = uc.ChromeOptions()
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.set_capability('LT:Options', _xoptions)
    user_agent = get_random_user_agent()
    chrome_options.add_argument(f"user-agent={user_agent}")
    
    print(f"🆕 Đã thay đổi User-Agent: {user_agent}")
    return uc.Chrome(headless=False)

def update_delivery_info(driver, site_url: str, configs: list[dict], page_title: str = "Shipping Policy"):
    """
    Bước 1: vào /wp-admin/edit.php?post_type=page
    Bước 2: search page_title
    Bước 3: click Edit
    Bước 4: chờ table và update giống trước
    """
    wait = WebDriverWait(driver, 10)

    # --- Bước 1 & 2: vào list Pages và search ---
    list_url = f"{site_url.rstrip('/')}/wp-admin/edit.php?post_type=page"
    driver.get(list_url)

    # chờ ô tìm kiếm xuất hiện, nhập tiêu đề và submit
    search_box = wait.until(EC.presence_of_element_located((By.ID, "post-search-input")))
    search_box.clear()
    search_box.send_keys(page_title)
    driver.find_element(By.ID, "search-submit").click()

    #  click Edit trên dòng kết quả ---
    edit = wait.until(EC.element_to_be_clickable((
        By.XPATH, f"//a[contains(@class,'row-title') and normalize-space()='{page_title}']"
    )))
    edit.click()

    # --- 2) Chờ editor load xong ---
    wait.until(EC.url_contains("post.php?post="))
    time.sleep(1)  # đảm bảo block đã vẽ xong
    print(' Chờ editor load xong ---')
    # --- 3) Scroll đến đúng tiêu đề block ---
    table = wait.until(EC.presence_of_element_located((
        By.CSS_SELECTOR,
        "figure.wp-block-table table"
    )))
    print('# --- 3) Scroll đến đúng tiêu đề block ---')
    # scroll vào giữa màn hình cho chắc
    driver.execute_script("arguments[0].scrollIntoView({block:'center'})", table)
    time.sleep(0.5)
    print('# scroll vào giữa màn hình cho chắc')
    rows = table.find_elements(By.TAG_NAME, "tr")

    for i, cfg in enumerate(configs, start=1):
        cells = rows[i].find_elements(By.TAG_NAME, "td")
        vals = [
            cfg["Service"],
            cfg["Handling Time"],
            cfg["Transit Time"],
            cfg["Delivery Time"],
            cfg["Fee"],
            cfg["Fulfillment Days"]
        ]
        for j, text in enumerate(vals):
            cell = cells[j]
            # double-click để bật inline edit Gutenberg
            ActionChains(driver).double_click(cell).perform()
            time.sleep(0.2)
            p = cell.find_element(By.TAG_NAME, "p")
            # xóa text cũ và nhập text mới
            driver.execute_script("arguments[0].innerText = ''", p)
            p.send_keys(text)
            time.sleep(0.1)

    # --- 5) Lưu bài viết ---
    update_btn = driver.find_element(
        By.CSS_SELECTOR,
        "button.editor-post-publish-button, button.editor-post-update-button"
    )
    update_btn.click()
    # chờ confirm đã lưu
    time.sleep(2)
    print(f"✅ Đã cập nhật '{page_title}' trên {site_url}")


def simulate_login(domain: str ,url: str, user: str, password: str,configs: list[dict]):
    """
    Giả lập đăng nhập WordPress admin bằng Selenium.
    """
    # Khởi driver (chắc bạn đã cài ChromeDriver và thêm vào PATH)
    driver = create_driver()
    try:
        driver.get(url)
        time.sleep(10)

        # WordPress default field IDs
        driver.find_element(By.ID, "user_login").send_keys(user)
        driver.find_element(By.ID, "user_pass").send_keys(password)
        driver.find_element(By.ID, "wp-submit").click()

        time.sleep(3)

        if "/wp-admin/" in driver.current_url:
            print(f"[OK]   Đăng nhập thành công: {url}")
            update_delivery_info(
                driver,
                site_url= domain,
                configs=configs,
                page_title="Shipping Policy"
            )
        else:
            print(f"[FAIL] Đăng nhập không thành công: {url} (URL trả về: {driver.current_url})")
    except Exception as e:
        print(f"[ERROR] {url} → {e}")
    finally:
        # driver.quit()
        pass