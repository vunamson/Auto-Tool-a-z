# main.py

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from create_site import simulate_login

configs = [
      {
        "Service": "Standard Delivery test",
        "Handling Time": "1–3 business days test",
        "Transit Time": "7–25 business days test",
        "Delivery Time": "8–28 business days test",
        "Fee": "$4.99 test",
        "Fulfillment Days": "Mon–Fri test"
      },
      {
        "Service": "Fast Delivery test",
        "Handling Time": "1–2 business days test",
        "Transit Time": "10–15 business days test",
        "Delivery Time": "11–17 business days test",
        "Fee": "$14.99 test",
        "Fulfillment Days": "Mon–Fri test"
      }
    ]


def main():
    # 1. Xác thực Google Sheets
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        r"C:\GameEC\Videos\Video.Intel5\DisplayAudio\11.3\Auto-Tool-a-z\credentials.json",
        scope
    )
    client = gspread.authorize(creds)

    # 2. Mở sheet và lấy dữ liệu
    sheet = client.open_by_key(
        "1qS_8caXKg02rOiC7Ux1UL9IILWTwggtfkH6pHDJYgG4"
    ).worksheet("Sheet1")

    # Giả sử hàng đầu là header, ta lấy từ hàng thứ 2
    rows = sheet.get_all_values()[1:]

    # 3. Lặp qua từng dòng: cột A=url, B=user, C=pass
    for idx, row in enumerate(rows, start=2):
        domain, url, user, password =row[0].strip(), row[1].strip(), row[2].strip(), row[3].strip()
        print(f"\n→ Hàng {idx}:")
        simulate_login(domain,url, user, password ,configs)

if __name__ == "__main__":
    main()
