from PIL import Image
from datetime import datetime
import requests
from io import BytesIO
import time
import os
from tqdm import tqdm
import shutil

unix_time = None

while unix_time is None:
    unix_time = input("請輸入時間戳: ")
    try:
        unix_time = int(unix_time)
    except ValueError:
        print("請輸入有效的整數時間戳")

timestamp_ms_start = unix_time - 10000
timestamp_ms_end = unix_time + 240000

print(f"開始時間: {datetime.fromtimestamp(timestamp_ms_start/1000).strftime('%Y-%m-%d %H:%M:%S')} ({timestamp_ms_start})")
print(f"結束時間: {datetime.fromtimestamp(timestamp_ms_end/1000).strftime('%Y-%m-%d %H:%M:%S')} ({timestamp_ms_end})")

raw = Image.open("./rts-image.png")

_t = round((timestamp_ms_end - timestamp_ms_start) / 1000)
missing_count = 0

if os.path.exists("./images"):
    shutil.rmtree("./images")

if not os.path.exists("./images"):
    os.makedirs("./images")

with tqdm(total=_t, desc="進度") as pbar:
    for t in range(_t):
        timestamp = timestamp_ms_start + t * 1000
        
        max_retries = 3
        retry_count = 0
        success = False

        while retry_count < max_retries:
            try:
                response = requests.get(
                    f"https://api-1.exptech.dev/api/v1/trem/rts-image/{timestamp}",
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
                    print(f"請求失敗，狀態碼: {response.status_code}，時間戳: {timestamp}")
                    break
            except Exception as e:
                print(f"處理時間戳 {timestamp} 時發生錯誤: {e}")
    
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
    file_list = sorted(os.listdir(image_folder))
    images = []
    
    for filename in file_list:
        img_path = os.path.join(image_folder, filename)
        img = Image.open(img_path)
        prepared_img = prepare_for_gif(img)
        images.append(prepared_img)
    
    try:
        images[0].save(
            output_path, # GIF檔案的儲存路徑
            save_all=True, # 設為True表示儲存所有圖片幀，而不是只儲存第一幀
            append_images=images[1:], # 將第二幀開始的所有圖片附加到GIF中
            duration=200, # 每一幀的顯示時間（單位：毫秒）
            loop=0, # 循環次數：0表示無限循環，1表示播放一次，n表示循環n次
            transparency=255, # 設定透明色的索引值（255通常用於完全透明）
            disposal=2 # 幀處理方法：0 = 不處理 | 1 = 保留上一幀 | 2 = 恢復到背景色（最常用）| 3 = 恢復到上一幀
        )
        print(f"GIF successfully created at {output_path}")
    except Exception as e:
        print(f"Error creating GIF: {e}")
        raise
    
    return output_path

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
    print(f"{len(missing)} 個缺失的時間戳 | 丟失率: {missing_percentage:.1f}%")

create_gif("./images", "output.gif")