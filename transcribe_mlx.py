import os
import time
import mlx_whisper
import gc

# ================= 配置 =================
# ✅ 路径指向你的本地模型
MODEL_PATH = "./models/turbo-4bit" 
# =======================================

def format_timestamp(seconds):
    """
    辅助函数：将秒数转换为 00:00.000 格式
    """
    if seconds is None:
        return "00:00.000"
    mm = int(seconds // 60)
    ss = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{mm:02d}:{ss:02d}.{ms:03d}"

def transcribe_one_file(audio_path, output_folder):
    """
    接收单个音频文件路径，进行转录，返回生成的 txt 路径。
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    filename = os.path.basename(audio_path)
    txt_filename = os.path.splitext(filename)[0] + ".txt"
    output_path = os.path.join(output_folder, txt_filename)

    if os.path.exists(output_path):
        print(f"⏩ [转录] 已存在，跳过: {txt_filename}")
        return output_path

    print(f"⚡️ [转录] 正在处理: {filename} ...")
    print(f"📥 [加载] 读取本地模型: {os.path.abspath(MODEL_PATH)}")
    
    start_time = time.time()

    try:
        # === 核心转录 (参数已优化) ===
        # mlx_whisper.transcribe 返回的是一个字典
        result = mlx_whisper.transcribe(
            audio_path, 
            path_or_hf_repo=MODEL_PATH, 
            verbose=True,      # 在终端打印进度
            language="zh",     # 强制中文
            
            # ✅ [关键修改 1] 提示词：给模型“洗脑”，让它忽略噪音，保持简体
            initial_prompt="以下是简体中文会议记录。请忽略重复的语气词、背景噪音和静音片段。不要输出繁体中文。",
            
            # ✅ [关键修改 2] 防死循环神器：禁止模型根据上一句猜测下一句
            # 这能有效防止“嗯嗯嗯”无限循环
            condition_on_previous_text=False,
            
            # ✅ [关键修改 3] 温度采样：如果模型卡住，允许它尝试一点点随机性
            temperature=(0.0, 0.2, 0.4),
            
            # 其他可选参数 (如果 MLX 支持的话，通常加上比较稳)
            compression_ratio_threshold=2.4, # 压缩率过高说明可能复读机了，此时会重试
            logprob_threshold=-1.0,          # 置信度过低则跳过
        )

        # ✅ [关键修改 4] 写入格式改为带时间戳
        # 这样 main.py 里的清洗函数才能工作！
        with open(output_path, "w", encoding="utf-8") as f:
            # 遍历每一个片段 (segment)
            for segment in result["segments"]:
                start = format_timestamp(segment['start'])
                end = format_timestamp(segment['end'])
                text = segment['text'].strip()
                
                # 写入格式: [00:12.500 --> 00:15.200] 文本内容
                if text: # 不写空行
                    f.write(f"[{start} --> {end}] {text}\n")

        duration = time.time() - start_time
        print(f"✅ [转录] 完成！耗时: {duration:.2f}秒")
        
        # 清理内存
        del result
        gc.collect()
        
        return output_path

    except Exception as e:
        print(f"❌ [转录] 失败: {e}")
        print(f" 调试提示：请检查 {MODEL_PATH} 里是否有 model.safetensors")
        return None