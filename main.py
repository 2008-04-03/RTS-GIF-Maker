from PIL import Image
from datetime import datetime
import requests
from io import BytesIO
import time
import os
from tqdm import tqdm
import shutil

date_start = "2024-11-16 17:30:40"
date_end = "2024-11-16 17:30:45"

datetime_start = datetime.strptime(date_start, "%Y-%m-%d %H:%M:%S")
datetime_end = datetime.strptime(date_end, "%Y-%m-%d %H:%M:%S")

timestamp_ms_start = int(datetime_start.timestamp() * 1000)
timestamp_ms_end = int(datetime_end.timestamp() * 1000)

raw = Image.open("./rts-image.png")

_t = round((timestamp_ms_end - timestamp_ms_start) / 1000)

if os.path.exists("./images"):
    shutil.rmtree("./images")

if not os.path.exists("./images"):
    os.makedirs("./images")

with tqdm(total=_t, desc="進度") as pbar:
    for t in range(_t):
        response = requests.get(
            f"https://api-2.exptech.dev/api/v1/trem/rts-image?time={timestamp_ms_start + t * 1000}")
        if response.status_code == 200:
            result_image = raw.copy()
            image_data = BytesIO(response.content)
            variable_img = Image.open(image_data)
            variable_img = variable_img.convert("RGBA")
            result_image = Image.alpha_composite(result_image, variable_img)
            result_image.save(
                f"./images/{timestamp_ms_start + t * 1000}.png", format="PNG")
        else:
            print(
                f"Failed to download image at timestamp {timestamp_ms_start + t * 1000}")
        time.sleep(0.5)
        pbar.update(1)

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
            output_path,
            save_all=True,
            append_images=images[1:],
            duration=100,
            loop=0,
            transparency=255,
            disposal=2
        )
        print(f"GIF successfully created at {output_path}")
    except Exception as e:
        print(f"Error creating GIF: {e}")
        raise
    
    return output_path

create_gif("./images", "output.gif")