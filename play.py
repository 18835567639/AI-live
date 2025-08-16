# venv\Scripts\activate


import itertools
import json
import subprocess
from pathlib import Path
import datetime

import obsws_python as obs
import pygame
from pydub import AudioSegment

# 初始化：设置混音器，2声道，44.1kHz，16位，缓冲512
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

VOICE_CHANNEL = pygame.mixer.Channel(0)
BGM_CHANNEL = pygame.mixer.Channel(1)

# ----------------[ 可调参数 ]-----------------
VERSION = "1"  # scene版本
OBS_HOST, OBS_PORT, OBS_PWD = "localhost", 6688, "6pkRZwWmFmQGvP0b"
IMAGE_SRC_NAME = "ProductImage"  # OBS 里图片源名称
IMG_SWITCH_SEC = 3  # 同一商品多图切换间隔
KOKORO_ENTRY = ["python", "tts.py"]  # Kokoro-onnx 合成命令
# -------------------------------------------------


# 循环播放背景音乐
def play_bgm(path):
    bgm = pygame.mixer.Sound(str(path))
    BGM_CHANNEL.play(bgm, loops=-1)  # 无限循环播放


# 播放语音文件
def play_voice_async(wav: Path):
    snd = pygame.mixer.Sound(str(wav))
    VOICE_CHANNEL.play(snd)


# AI实时生成语音文件
def make_audio(text, wav_path):
    # 调用 Kokoro 生成语音
    cmd = KOKORO_ENTRY + ["--text", text, "--output", wav_path]
    subprocess.run(cmd, check=True)


# 获取语音文件时长
def audio_len_seconds(path):
    if path.exists():
        seg = AudioSegment.from_file(path)  # 自动识别格式
        return seg.duration_seconds
    else:
        return 0


# 设置商品图片
def set_obs_image(ws, img_path: Path):
    ws.set_input_settings(
        "ProductImage",  # OBS 中图片源的名称
        {"file": str(img_path)},
        True,  # 立即生效
    )


# 设置商品文案
def set_obs_text(ws, source, new_text: str):
    ws.set_input_settings(
        source,  # OBS 中图片源的名称
        {"text": new_text},
        True,  # 立即生效
    )

# 播报当前时间
def play_current_time():
    # 获取北京时间
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    hh = now.hour
    mm = now.minute
    fname = f"{hh:02d}_{mm:02d}.wav"
    wav_path = Path(f"product/scene_{VERSION}/minutes/{fname}").resolve()
    if wav_path.exists():
        print(f"正在播报当前时间：{fname}")
        play_voice_async(wav_path)
        while VOICE_CHANNEL.get_busy():
            pygame.time.wait(300)
    else:
        print(f"未找到时间语音文件: {wav_path}")

def main():
    # 连接 OBS
    ws = obs.ReqClient(host=OBS_HOST, port=OBS_PORT, password=OBS_PWD, timeout=3)

    print("✅ 已连接 OBS WebSocket")

    json_path = f"product/scene_{VERSION}/product_{VERSION}.json"
    with open(json_path, "r", encoding="utf-8") as f:
        products = json.load(f)

    # 播放背景音乐
    play_bgm("product/scene_1/back_audio.mp3")

    for idx, item in enumerate(products, 1):
        # 播报当前时间
        play_current_time()

        # ---------- 获取语音文件 ----------
        wav_path = Path(item["goods_wav"]).resolve()
        if not wav_path.exists():
            print(f"🎤 缺失语音《{wav_path}》")
            # make_audio(item["intro"], str(wav_path))
        
        end_wav_path = Path(f"product/scene_{VERSION}/cart_sort/{item['cart_sort']}.wav").resolve()

        # ---------- 更新标题 ----------
        set_obs_text(ws, "ProductText", item["goods_name"])

        # ---------- 更新购物车指引文案 ----------
        set_obs_text(ws, "CartText", f"购物车{item['cart_sort']}号链接")

        # ---------- 当前商品介绍时长 ----------
        # duration = audio_len_seconds(wav_path)

        # ---------- 当前商品结束语时长 ----------
        # end_duration = audio_len_seconds(end_wav_path)

        # ---------- 图片列表 ----------
        imgs = item.get("images", [])
        if imgs:
            img_cycle = itertools.cycle(imgs)
            first_img = Path(next(img_cycle)).resolve()
            if first_img.exists():
                set_obs_image(ws, first_img)
            else:
                print("⚠ 图片不存在:", first_img)
        else:
            print("⚠ 未设置图片")
            set_obs_image(ws, products[0]["images"][0])

        # -------- 播放语音并轮播图片 --------
        print(f"开始播放 ---《{item['goods_name']}》---")
        play_voice_async(wav_path)

        # ---------- 轮播期间 ----------
        while VOICE_CHANNEL.get_busy():
            pygame.time.wait(IMG_SWITCH_SEC * 1000)
            if imgs:
                next_img = Path(next(img_cycle)).resolve()
                if next_img.exists():
                    set_obs_image(ws, next_img)
                else:
                    print("⚠ 图片不存在:", next_img)


        # ---------- 播放结束语音, 结束语文件名对应购物车n号链接 ----------
        if end_wav_path.exists():
            pygame.time.wait(2000)
            play_voice_async(end_wav_path)
            while VOICE_CHANNEL.get_busy():
                pygame.time.wait(300)
        else:
            print(f"《{item['goods_name']}》无结束语文件")

        print(f"---《{item['goods_name']}》--- 结束")


        # ---------- 缓冲 ----------
        pygame.time.wait(int(item.get("buffer", 3)) * 1000)

    ws.disconnect()
    print("\n🎉 所有商品播放完毕，脚本结束")


if __name__ == "__main__":
    main()
