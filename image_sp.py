import os
import boto3
from PIL import Image
import requests
from woocommerce import API  # pip install woocommerce

# 1) AWS S3 client
s3 = boto3.client('s3',
    aws_access_key_id='AKIA…',
    aws_secret_access_key='…',
    region_name='us-east-1'
)
BUCKET = 'my-shop-assets'

# 2) WooCommerce REST API client
wcapi = API(
    url="https://your-site.com",
    consumer_key="ck_…",
    consumer_secret="cs_…",
    version="wc/v3"
)

# 3) Duyệt tất cả design × mockup
for dfile in os.listdir('designs'):
    if not dfile.lower().endswith('.png'): continue
    design = Image.open(f'designs/{dfile}')
    for mfile in os.listdir('mockups'):
        if not mfile.lower().endswith(('.png','.jpg')): continue
        mockup = Image.open(f'mockups/{mfile}').convert("RGBA")
        # scale design nếu cần, ví dụ bằng width mockup * 0.8:
        w, h = mockup.size
        design_resized = design.resize((int(w*0.8), int(h*0.8)), Image.ANTIALIAS)
        # ghép chính giữa
        offset = ((w - design_resized.width)//2, (h - design_resized.height)//2)
        composite = Image.new("RGBA", mockup.size)
        composite.paste(mockup, (0,0))
        composite.paste(design_resized, offset, design_resized)
        # lưu tạm
        tmp_path = f'tmp/{dfile[:-4]}__{mfile[:-4]}.png'
        os.makedirs('tmp', exist_ok=True)
        composite.convert("RGB").save(tmp_path, 'PNG')

        # 4) Upload lên S3
        key = f'products/{os.path.basename(tmp_path)}'
        s3.upload_file(tmp_path, BUCKET, key, ExtraArgs={'ACL':'public-read','ContentType':'image/png'})
        url = f'https://{BUCKET}.s3.amazonaws.com/{key}'
        print("Uploaded:", url)

        # 5) Tạo/update product lên WooCommerce
        product_data = {
            "name": f"{dfile[:-4]} on {mfile[:-4]}",
            "type": "simple",
            "regular_price": "19.99",
            "images": [{"src": url}],
            # categories: parent > child, giả sử bạn xác định sẵn ID:
            "categories": [
                {"id": 123},  # parent
                {"id": 456}   # child
            ]
        }
        resp = wcapi.post("products", product_data)
        if resp.status_code in (200,201):
            print("Product created:", resp.json().get("id"))
        else:
            print("Error:", resp.status_code, resp.text)
