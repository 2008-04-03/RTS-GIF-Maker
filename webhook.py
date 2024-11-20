from PIL import Image
from datetime import datetime
import requests
from io import BytesIO
import time
from time import sleep as slp
import os
from tqdm import tqdm
import shutil
from threading import Thread
import json
import atexit

def get_first_5_timestamp():
    response = requests.get(f"https://api-1.exptech.dev/api/v1/trem/list",)
    earthquake = response.json()
    return [eq['ID'] for eq in earthquake[:5]]

def get_data_from_json():
    if os.path.exists("first_5_timestamp.json"):
        with open("first_5_timestamp.json", "r") as f:
            return json.load(f)
    else:
        return []

def save_data_to_json(data):
    with open("first_5_timestamp.json", "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if not os.path.exists("first_5_timestamp.json"):
    with open("first_5_timestamp.json", "w") as f:
        json.dump(get_first_5_timestamp(), f, ensure_ascii=False, indent=4)

first_5_timestamp = get_first_5_timestamp()

raw = Image.open("./rts-image.png")

def cleanup():
    if os.path.exists("./images"):
        shutil.rmtree("./images")
        os.makedirs("./images")

def cleanup2():
    if os.path.exists("./images"):
        shutil.rmtree("./images")

atexit.register(cleanup2)

cleanup()

debug = False

if not os.path.exists("./images"):
    os.makedirs("./images")

def search(timestamp):
    response = requests.get(f"https://api-1.exptech.dev/api/v1/trem/list")
    earthquake = response.json()
    for eq in earthquake:
        if round(float(eq['ID']) / 1000) == timestamp or int(float(eq['ID']) / 1000) == timestamp:
            return eq
    return None

def main():
    global first_5_timestamp
    if is_first_run:
        return
    got_first_5_timestamp = get_first_5_timestamp()
    if first_5_timestamp == got_first_5_timestamp:
        return

    first_5_timestamp = got_first_5_timestamp
    unix_time = int(first_5_timestamp[0])
    
    os.system("cls")

    latest_eq = search(int(unix_time/1000))
    if latest_eq:
        if latest_eq['Alarm'] != 1:
            print(f"最新地震檢知未公開，不製作GIF，時間戳: {unix_time}")
            return
    
    save_data_to_json(first_5_timestamp)
    timestamp_ms_start = unix_time - 10000
    timestamp_ms_end = unix_time + 240000
    print(f"處理ID: {unix_time}")
    print(f"開始時間: {datetime.fromtimestamp(timestamp_ms_start / 1000).strftime('%Y-%m-%d %H:%M:%S')} ({timestamp_ms_start})")
    print(f"結束時間: {datetime.fromtimestamp(timestamp_ms_end / 1000).strftime('%Y-%m-%d %H:%M:%S')} ({timestamp_ms_end})")

    _t = round((timestamp_ms_end - timestamp_ms_start) / 1000)
    
    with tqdm(total=_t, desc="進度") as pbar:
        for t in range(_t):
            timestamp = timestamp_ms_start + t * 1000
            
            max_retries = 3
            retry_count = 0

            while retry_count < max_retries:
                try:
                    response = requests.get(f"https://api-1.exptech.dev/api/v1/trem/rts-image/{timestamp}",)
                    
                    if response.status_code == 200:
                        result_image = raw.copy()
                        image_data = BytesIO(response.content)
                        variable_img = Image.open(image_data)
                        variable_img = variable_img.convert("RGBA")
                        result_image = Image.alpha_composite(result_image, variable_img)
                        result_image.save(f"./images/{timestamp}.png", format="PNG")
                        break
                    else:
                        print(f"請求失敗，狀態碼: {response.status_code}，時間戳: {timestamp}")
                        break
                except Exception as e:
                    print(f"處理時間戳 {timestamp} 時發生錯誤: {e}")
                    
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
        
        if debug:
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 已處理 prepare_for_gif")
        return p_img

    def create_gif(image_folder, output_path):
        if os.path.exists(output_path):
            if debug:
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 正在刪除舊的 GIF")
            os.remove(output_path)
            if debug:
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 已刪除舊的 GIF")

        file_list = sorted(os.listdir(image_folder))
        images = []
        
        if debug:
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} debug 1")
        
        for filename in file_list:
            img_path = os.path.join(image_folder, filename)
            img = Image.open(img_path)
            prepared_img = prepare_for_gif(img)
            images.append(prepared_img)
        
        if debug:
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} debug 2")

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
            
            if debug:
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} debug 3")
                print(f"GIF successfully created at {output_path}")
            
            webhook_url = ""
            webhook_data = {
                "username": "ExpTech | 探索科技",
                "avatar_url": "https://i.ibb.co/9HwcdXX/Exptech.png",
                "content": ""
            }
            
            if debug:
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} debug 4")
            
            with open(output_path, 'rb') as f:
                files = {
                    'file': ('output.gif', f)
                }
                webhook_response = requests.post(webhook_url, data=webhook_data, files=files)
            
            if debug:
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} debug 5")
            
            if webhook_response.status_code == 200:
                print(f"webhook 發送成功")
            else:
                print(f"webhook 發送失敗，狀態碼: {webhook_response.status_code}")
            
            if debug:
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} debug 6 - create gif")
        except Exception as e:
            print(f"Error creating GIF: {e}")
            raise e
        
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
        print(f"警告：發現 {len(missing)} 個缺失的時間戳")
        print(f"第一個缺失的時間戳: {datetime.fromtimestamp(missing[0]/1000)}")

    create_gif("./images", "output.gif")

if __name__ == "__main__":
    is_first_run = True
    def run():
        while True:
            main()
            slp(1)
    Thread(target=run).start()
    def set_is_first_run_false():
        global is_first_run
        slp(5)
        is_first_run = False
    Thread(target=set_is_first_run_false).start()