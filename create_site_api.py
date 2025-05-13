# create_site_api.py

import re
import requests
from requests.auth import HTTPBasicAuth

def fetch_page(site_url: str, page_title: str, user: str, pw: str):
    base = site_url.rstrip('/')
    # 1) tìm page_id theo search
    r1 = requests.get(
        f"{base}/wp-json/wp/v2/pages",
        params={"search": page_title},
        auth=HTTPBasicAuth(user, pw),
        timeout=10
    )
    r1.raise_for_status()
    candidates = r1.json()
    matches = [
        p for p in candidates
        if p.get("title", {}).get("rendered", "").strip().lower() == page_title.lower()
    ]
    if not matches:
        raise RuntimeError(f"Không tìm thấy page với title '{page_title}'")
    page_id = matches[0]["id"]

    # 2) lấy raw content (fallback rendered)
    try:
        r2 = requests.get(
            f"{base}/wp-json/wp/v2/pages/{page_id}",
            params={"context": "edit"},
            auth=HTTPBasicAuth(user, pw),
            timeout=10
        )
        r2.raise_for_status()
        raw = r2.json().get("content", {}).get("raw")
        if raw:
            print('raw' ,raw)
            return page_id, raw
    except requests.exceptions.HTTPError as e:
        if e.response.status_code != 401:
            raise
    # fallback
    r3 = requests.get(f"{base}/wp-json/wp/v2/pages/{page_id}",
                      auth=HTTPBasicAuth(user, pw), timeout=10)
    r3.raise_for_status()
    rendered = r3.json().get("content", {}).get("rendered", "")
    return page_id, rendered


def build_delivery_table_html(configs: list[dict]) -> str:
    """
    Sinh nguyên khối Gutenberg block: heading(level3) + table
    """
    thead = (
        "<thead><tr>"
        "<th>Service</th><th>Handling Time</th>"
        "<th>Transit Time</th><th>Delivery Time</th>"
        "<th>Fee</th><th>Fulfillment Days</th>"
        "</tr></thead>"
    )
    rows = ""
    for cfg in configs:
        rows += (
            "<tr>"
            f"<td>{cfg['Service']}</td>"
            f"<td>{cfg['Handling Time']}</td>"
            f"<td>{cfg['Transit Time']}</td>"
            f"<td>{cfg['Delivery Time']}</td>"
            f"<td>{cfg['Fee']}</td>"
            f"<td>{cfg['Fulfillment Days']}</td>"
            "</tr>"
        )

    # Gutenberg heading level 3 + table block
    return (
        '<!-- wp:heading {\"level\":3} -->'
        '<h3>Delivery Estimates &amp; Fees</h3>'
        '<!-- /wp:heading -->'
        '<!-- wp:table -->'
        '<figure class="wp-block-table"><table class="has-fixed-layout">'
        f'{thead}<tbody>{rows}</tbody></table></figure>'
        '<!-- /wp:table -->'
    )


def update_page_content(site_url: str, page_id: int, old_html: str,
                        new_table_block: str, user: str, pw: str):
    """
    Thay cả block heading+table cũ bằng new_table_block.
    """
    # Regex: từ comment wp:heading chứa Delivery Estimates & Fees
    # cho đến comment đóng wp:table
    pattern = re.compile(
        r"(?s)<!-- wp:heading.*?Delivery Estimates &amp; Fees.*?<!-- \/wp:table -->"
    )
    new_raw = pattern.sub(new_table_block, old_html)

    api = f"{site_url.rstrip('/')}/wp-json/wp/v2/pages/{page_id}"
    resp = requests.post(
        api,
        auth=HTTPBasicAuth(user, pw),
        json={"content": new_raw},
        timeout=10
    )
    if resp.status_code == 401:
        raise RuntimeError(
            "❌ Unauthorized – bạn cần dùng WordPress Application Password"
        )
    resp.raise_for_status()
    print(f"✅ Đã cập nhật Delivery Estimates & Fees trên page {page_id}")
