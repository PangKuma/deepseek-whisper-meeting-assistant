import os
import time
from faster_whisper import WhisperModel

# ================= 配置区域 =================
# 1. 音频存放的文件夹（当前目录下的 audio 文件夹）
INPUT_FOLDER = "audio_input"
# 2. 文本输出的文件夹
OUTPUT_FOLDER = "text_output"
# 3. 模型大小：推荐 "medium" (平衡) 或 "large-v3" (更准但慢)
# macOS M1/M2/M3 跑 medium 速度通常不错
MODEL_SIZE = "small" 
# ===========================================

def transcribe_all():
    # 1. 准备环境
    if not os.path.exists(INPUT_FOLDER):
        os.makedirs(INPUT_FOLDER)
        print(f"📁 已创建输入文件夹: {INPUT_FOLDER}")
        print(f"👉 请把你的 MP3 文件放入 {INPUT_FOLDER} 文件夹中！")
        return

    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    print(f"🚀 正在加载 Whisper 模型 ({MODEL_SIZE})... 第一次运行会自动下载模型，请耐心等待...")
    # macOS 这里的 device="cpu" 是正常的，M芯片的 CPU 跑这个很快
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    print("✅ 模型加载完毕！开始干活...")

    # 2. 扫描文件
    files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith(('.mp3', '.wav', '.m4a'))]
    
    if not files:
        print("📭 输入文件夹里没有音频文件。请放进去一个试试！")
        return

    # 3. 开始转录
    for filename in files:
        audio_path = os.path.join(INPUT_FOLDER, filename)
        txt_filename = os.path.splitext(filename)[0] + ".txt"
        output_path = os.path.join(OUTPUT_FOLDER, txt_filename)

        # 如果已经转录过，就跳过
        if os.path.exists(output_path):
            print(f"⏩ 跳过已存在文件: {filename}")
            continue

        print(f"\n🎙️  正在转录: {filename} ...")
        start_time = time.time()

        # 核心转录逻辑
        segments, info = model.transcribe(audio_path, beam_size=1)
        
        # 实时写入文件（防止程序崩了白跑）
        with open(output_path, "w", encoding="utf-8") as f:
            for segment in segments:
                # 打印进度条效果
                print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
                f.write(segment.text + "\n")

        duration = time.time() - start_time
        print(f"✅ 完成！耗时: {duration:.2f}秒。已保存到: {output_path}")

if __name__ == "__main__":
    transcribe_all()