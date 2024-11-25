from PIL import Image
from datetime import datetime
import requests
from io import BytesIO
import time
import os
from tqdm import tqdm
import shutil
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def log(msg: str, type_: int = 1) -> None:
    if type_ == 1:  # Info
        color_code = "92"  # Bright Green
        type_str = "Info"
    elif type_ == 2:  # Warn
        color_code = "93"  # Bright Yellow
        type_str = "Warn"
    else:  # Error
        color_code = "91"  # Bright Red
        type_str = "Error"

    print(f"\033[{color_code}m[{type_str}][{time.strftime('%Y/%m/%d %H:%M:%S')}]: {msg}\033[0m")

unix_time = None

while unix_time is None:
    unix_time = input("請輸入時間戳: ")
    try:
        unix_time = int(unix_time)
    except ValueError:
        log("請輸入有效的整數時間戳", 3)

timestamp_ms_start = unix_time - 10000
timestamp_ms_end = unix_time + 240000

log(f"開始時間: {datetime.fromtimestamp(timestamp_ms_start/1000).strftime('%Y-%m-%d %H:%M:%S')} ({timestamp_ms_start})")
log(f"結束時間: {datetime.fromtimestamp(timestamp_ms_end/1000).strftime('%Y-%m-%d %H:%M:%S')} ({timestamp_ms_end})")

raw = Image.open("./rts-image.png")

_t = round((timestamp_ms_end - timestamp_ms_start) / 1000)
missing_count = 0

if os.path.exists("./images"):
    shutil.rmtree("./images")

if not os.path.exists("./images"):
    os.makedirs("./images")

# 修改session建立部分
session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)

with tqdm(total=_t, desc="進度") as pbar:
    for t in range(_t):
        timestamp = timestamp_ms_start + t * 1000
        
        max_retries = 3
        retry_count = 0
        success = False

        while retry_count < max_retries:
            try:
                response = session.get(
                    f"https://api-1.exptech.dev/api/v1/trem/rts-image/{timestamp}",
                    timeout=10,
                    verify=True
                )
                
                if response.status_code == 200:
                    result_image = raw.copy()
                    image_data = BytesIO(response.content)
                    variable_img = Image.open(image_data)
                    variable_img = variable_img.convert("RGBA")
                    result_image = Image.alpha_composite(result_image, variable_img)
                    result_image.save(f"./images/{timestamp}.png", format="PNG")
                    success = True
                    break
                else:
                    log(f"請求失敗，狀態碼: {response.status_code}，時間戳: {timestamp}", 2)
                    break
            except Exception as e:
                log(f"處理時間戳 {timestamp} 時發生錯誤: {e}", 3)
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(1 * retry_count)  # 漸進式延遲
    
        if not success:
            missing_count += 1
        missing_percentage = (missing_count / _t) * 100
        pbar.update(1)
        time.sleep(0.1)

def prepare_for_gif(im):
    rgba = im.convert('RGBA')
    alpha = rgba.split()[3]
    rgb = rgba.convert('RGB')
    p_img = rgb.convert('P', palette=Image.ADAPTIVE, colors=255)
    p_img.info['transparency'] = 255
    mask = Image.eval(alpha, lambda a: 255 if a < 128 else 0)
    p_img.paste(255, mask)
    
    return p_img

def create_gif(image_folder, output_path):
    if os.path.exists(output_path):
        os.remove(output_path)
        
    file_list = sorted(os.listdir(image_folder))
    images = []
    
    for filename in file_list:
        img_path = os.path.join(image_folder, filename)
        img = Image.open(img_path)
        prepared_img = prepare_for_gif(img)
        images.append(prepared_img)
    
    try:
        images[0].save(
            output_path,
            save_all=True,
            append_images=images[1:],
            duration=200,
            loop=0,
            transparency=255,
            disposal=2
        )
        print(f"成功創建GIF於 {output_path}")
    except Exception as e:
        print(f"創建GIF時發生錯誤: {e}")
        raise

def verify_image_sequence(image_folder, start_time, end_time, interval=1000):
    missing_timestamps = []
    current = start_time
    while current <= end_time:
        if not os.path.exists(f"{image_folder}/{current}.png"):
            missing_timestamps.append(current)
        current += interval
    return missing_timestamps

missing = verify_image_sequence("./images", timestamp_ms_start, timestamp_ms_end)
if missing:
    log(f"{len(missing)} 個缺失的時間戳 | 丟失率: {missing_percentage:.1f}%", 2)

try:
    create_gif("./images", "output.gif")
    log("成功創建GIF於 output.gif", 1)
except Exception as e:
    log(f"創建GIF時發生錯誤: {e}", 3)

# 清理臨時文件
for filename in os.listdir("./images"):
    if filename.endswith(".png"):
        file_path = os.path.join("./images", filename)
        os.remove(file_path)
log("已清理所有臨時PNG文件", 1)