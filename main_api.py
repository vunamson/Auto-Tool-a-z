# main_api.py

import random
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from create_site_api import fetch_page, build_delivery_table_html, update_page_content

def main():
    # 1) Auth với Google Sheets
    scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        r"C:\GameEC\Videos\Video.Intel5\DisplayAudio\11.3\Auto-Tool-a-z\credentials.json",
        scope
    )
    client = gspread.authorize(creds)

    # 2) Đọc sheet (A=site_url, B=ignored, C=user, D=pass)
    sheet = client.open_by_key("1qS_8caXKg02rOiC7Ux1UL9IILWTwggtfkH6pHDJYgG4").worksheet("Sheet1")
    rows = sheet.get_all_values()[1:]
    page_title = "Shipping Policy"
     # --- Standard Delivery ---
    # a ∈ [1,2], b ∈ [3,5]
    a = random.randint(1, 2)
    b = random.randint(3, 5)
    handling_std = f"{a}–{b} business days"
    # c ∈ [7,10], d ∈ [21,25]
    c = random.randint(7, 10)
    d = random.randint(21, 25)
    transit_std = f"{c}–{d} business days"
    # delivery lower = a + c, upper = b + d
    delivery_std = f"{a + c}–{b + d} business days"
    # --- Fast Delivery ---
    # b2 ∈ [2,4]
    b2 = random.randint(2, 4)
    handling_fast = f"1–{b2} business days"
    # d2 ∈ [11,15]
    d2 = random.randint(11, 15)
    transit_fast = f"10–{d2} business days"
    # delivery lower = 11, upper = b2 + d2
    delivery_fast = f"11–{b2 + d2} business days"
    configs = [
        {
            "Service": "Standard Delivery",
            "Handling Time": handling_std,
            "Transit Time": transit_std,
            "Delivery Time": delivery_std,
            "Fee": "$4.99",
            "Fulfillment Days": "Mon–Fri"
        },
        {
            "Service": "Fast Delivery",
             "Handling Time": handling_fast,
            "Transit Time": transit_fast,
            "Delivery Time": delivery_fast,
            "Fee": "$14.99",
            "Fulfillment Days": "Mon–Fri"
        }
    ]

    for idx, row in enumerate(rows, start=2):
        site_url = row[0].strip()
        user = row[2].strip()
        pw = row[3].strip()
        pw_a = row[4].strip()
        print(f"\n→ Hàng {idx}: {site_url}")
        # 1) Lấy page
        page_id, old_html = fetch_page(site_url, page_title, user, pw)
        print('✅ page id : ' ,page_id)
        new_table = build_delivery_table_html(configs)
        print('✅ khởi tạo xong new_table')
        update_page_content(site_url, page_id, old_html, new_table, user, pw)

if __name__ == "__main__":
    main()
