import os
import csv
from io import BytesIO
from PIL import Image
import boto3
from botocore.config import Config
from boto3.s3.transfer import TransferConfig
from concurrent.futures import ThreadPoolExecutor, as_completed
from woocommerce import API
import gspread
from oauth2client.service_account import ServiceAccountCredentials


scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(r"C:\GameEC\Videos\Video.Intel5\DisplayAudio\11.3\Auto-Tool-a-z\credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open_by_key("1qS_8caXKg02rOiC7Ux1UL9IILWTwggtfkH6pHDJYgG4").worksheet("Sheet3")
# ————————————————
#  CẤU HÌNH CHUNG
# ————————————————
AWS_ACCESS_KEY_ID     = "DO0099R9G9QJ7EJA4QQ3"
AWS_SECRET_ACCESS_KEY = "IHYo5eULE0wMO3B1jdB54rXt0GoJSFUttCesKtGh9uk"
AWS_REGION            = "us-east-1"
BUCKET_NAME           = "trumpany"
S3_BASE_URL           = f"https://nyc3.digitaloceanspaces.com"
# S3_BASE_URL           = f"https://{BUCKET_NAME}.s3.amazonaws.com"

WC_URL             = "https://ovohoki.com"
WC_CONSUMER_KEY    = "ck_25a5fa55787360104552885a3ac083bb774b4734"
WC_CONSUMER_SECRET = "cs_23bd13500645f4697ca33c8e12d7cfcf220b5021"

DESIGN_DIR = "designs"
MOCKUP_DIR = "mockups"
CSV_FILE   = "products.csv"
# CSV columns:
# design_filename,mockup_filename,product_name,regular_price,sku,description,category
# category ví dụ: "Parent>Child,OtherParent>OtherChild"

# ————————————————
#  KHỞI TẠO CLIENTS
# ————————————————
# S3 với retry & multipart
s3_config = Config(retries={"max_attempts":5,"mode":"standard"})
s3_client = boto3.client(
    "s3",
    aws_access_key_id     = AWS_ACCESS_KEY_ID,
    aws_secret_access_key = AWS_SECRET_ACCESS_KEY,
    region_name           = AWS_REGION,
    config                = s3_config
)
transfer_config = TransferConfig(
    multipart_threshold = 5*1024*1024,
    multipart_chunksize = 5*1024*1024,
    max_concurrency     = 4,
    use_threads         = True
)

# WooCommerce REST API client
wcapi = API(
    url            = WC_URL,
    consumer_key   = WC_CONSUMER_KEY,
    consumer_secret= WC_CONSUMER_SECRET,
    version        = "wc/v3",
    timeout        = 30
)

# Cache để tránh gọi API category lặp
cat_cache = {}

def get_category_id(name, parent_id=None):
    """
    Lấy hoặc tạo category với name dưới parent_id, trả về ID.
    """
    key = (name.strip().lower(), parent_id or 0)
    if key in cat_cache:
        return cat_cache[key]

    params = {"search": name.strip()}
    if parent_id:
        params["parent"] = parent_id

    resp = wcapi.get("products/categories", params=params).json()
    for cat in resp:
        if (cat["name"].lower() == name.strip().lower()
            and cat["parent"] == (parent_id or 0)):
            cat_cache[key] = cat["id"]
            return cat["id"]

    # Nếu chưa tồn tại, tạo mới
    data = {"name": name.strip()}
    if parent_id:
        data["parent"] = parent_id
    new_cat = wcapi.post("products/categories", data).json()
    cat_cache[key] = new_cat["id"]
    return new_cat["id"]

def composite_and_upload(design_path, mockup_path):
    """
    Ghép design lên mockup (resize 80%), lưu JPEG in-memory,
    upload lên S3, trả về URL.
    """
    design = Image.open(design_path).convert("RGBA")
    mockup = Image.open(mockup_path).convert("RGBA")
    w, h = mockup.size

    # Resize design
    design_resized = design.resize((int(w*0.8), int(h*0.8)), Image.ANTIALIAS)
    offset = ((w - design_resized.width)//2, (h - design_resized.height)//2)

    # Composite
    composite = Image.new("RGBA", mockup.size)
    composite.paste(mockup, (0,0))
    composite.paste(design_resized, offset, design_resized)

    # Lưu in-memory
    buf = BytesIO()
    composite.convert("RGB").save(buf, format="JPEG", quality=85)
    buf.seek(0)

    # Upload
    fn = f"{os.path.splitext(os.path.basename(design_path))[0]}__{os.path.splitext(os.path.basename(mockup_path))[0]}.jpg"
    key = f"products/{fn}"
    s3_client.upload_fileobj(
        buf, BUCKET_NAME, key,
        ExtraArgs={"ACL":"public-read","ContentType":"image/jpeg"},
        Config=transfer_config
    )
    return f"{S3_BASE_URL}/{key}"

def process_row(row):
    """
    Xử lý 1 dòng CSV:
      - Composite & upload ảnh → img_url
      - Tạo mảng category [{"id":...},...]
      - Build payload product
    """
    img_url = composite_and_upload(
        os.path.join(DESIGN_DIR, row["design_filename"]),
        os.path.join(MOCKUP_DIR, row["mockup_filename"])
    )
    # Parse nhiều path category
    cats = []
    for path in row["category"].split(","):
        parent_id = None
        for part in path.split(">"):
            cid = get_category_id(part, parent_id)
            parent_id = cid
        cats.append({"id": parent_id})

    return {
        "name":           row["product_name"],
        "type":           "simple",
        "regular_price":  str(row["regular_price"]),
        "sku":            row.get("sku",""),
        "description":    row.get("description",""),
        "images":         [{"src": img_url}],
        "categories":     cats
    }

def main():
    # Đọc CSV và xử lý song song
    products = []
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        with ThreadPoolExecutor(max_workers=5) as ex:
            futures = {ex.submit(process_row,row): row for row in reader}
            for fut in as_completed(futures):
                row = futures[fut]
                try:
                    p = fut.result()
                    products.append(p)
                    print("Prepared:", p["name"])
                except Exception as e:
                    print("Error:", row, e)

    # Batch tạo sản phẩm (10 cái/lượt)
    for i in range(0, len(products), 10):
        batch = products[i:i+10]
        resp = wcapi.post("products/batch", {"create": batch}).json()
        print("Batch response:", resp)

if __name__ == "__main__":
    main()
