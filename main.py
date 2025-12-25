import os
import time
import subprocess
import gc
import json
import shutil
import sys
import atexit
# 引入转录和总结模块
from transcribe_mlx import transcribe_one_file
from summarize import summarize_one_file

# ================= 配置区域 =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_FOLDER = os.path.join(BASE_DIR, "video_input")
AUDIO_FOLDER = os.path.join(BASE_DIR, "audio_input")
TEXT_FOLDER = os.path.join(BASE_DIR, "text_output")
MD_TEMP_FOLDER = os.path.join(BASE_DIR, "md_output")
SUMMARY_FOLDER = os.getenv("SUMMARY_FOLDER", os.path.join(BASE_DIR, "summary_output"))
LOG_FILE = os.path.join(BASE_DIR, "running.log")
LOCK_FILE = os.path.join(BASE_DIR, "running.lock") # <--- 新增：锁文件路径

# 定义支持的格式
VIDEO_EXTS = ('.mp4', '.mov', '.mkv', '.webm')
AUDIO_EXTS = ('.mp3', '.wav', '.m4a', '.aac', '.flac')

# 确保文件夹存在
for folder in [VIDEO_FOLDER, AUDIO_FOLDER, TEXT_FOLDER, MD_TEMP_FOLDER, SUMMARY_FOLDER]:
    if not os.path.exists(folder): os.makedirs(folder)

# ================= 日志记录类 =================
class DualLogger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "a", encoding='utf-8')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()

# ================= 锁机制辅助函数 =================
def acquire_lock():
    """尝试获取锁，如果锁存在且进程活跃，则返回 False"""
    if os.path.exists(LOCK_FILE):
        # 可选：如果你想更高级，可以检查文件创建时间，如果超过2小时强制删除
        # 但目前为了安全，只要有文件就认为在跑
        return False
    
    # 创建锁文件
    with open(LOCK_FILE, 'w') as f:
        f.write(f"running at {time.time()}")
    return True

def release_lock():
    """释放锁"""
    if os.path.exists(LOCK_FILE):
        try:
            os.remove(LOCK_FILE)
            print("🔓 任务结束，已释放运行锁。")
        except:
            pass

# 注册退出时的清理函数（防止报错后锁没删掉）
atexit.register(release_lock)

# ===========================================

def wait_for_file_ready(file_path, stable_duration=3, timeout=300):
    """确保文件已完全写入磁盘"""
    if not os.path.exists(file_path): return False
    print(f"⏳ [检测] 等待文件就绪: {os.path.basename(file_path)} ...")
    start_time = time.time()
    last_size = -1
    stable_count = 0 
    while True:
        if time.time() - start_time > timeout: return False
        try:
            current_size = os.path.getsize(file_path)
            if current_size > 0 and current_size == last_size:
                stable_count += 1
            else:
                stable_count = 0
            last_size = current_size
            if stable_count >= stable_duration: return True
        except: pass
        time.sleep(1)

def ensure_audio_standard(input_path, output_audio_path, max_retries=3):
    cmd = ["ffmpeg", "-i", input_path, "-vn", "-ac", "1", "-ar", "16000", "-ab", "32k", output_audio_path, "-y", "-loglevel", "error"]
    
    for attempt in range(1, max_retries + 1):
        try:
            subprocess.run(cmd, check=True, stdin=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            print(f"⚠️ FFmpeg 转换失败 (尝试 {attempt}/{max_retries})")
            if attempt == max_retries: return False
            time.sleep(2)
    return False

def process_one_cycle(file_name, source_folder, file_type):
    input_path_abs = os.path.join(source_folder, file_name)
    temp_audio_name = os.path.splitext(file_name)[0] + "_processed.mp3"
    processed_audio_path = os.path.join(AUDIO_FOLDER, temp_audio_name)
    
    print(f"\n ========== 任务开始 [{file_type}]: {file_name} ==========")
    
    # 1. 等待文件就绪
    if not wait_for_file_ready(input_path_abs): 
        print(f"❌ 文件未就绪或超时: {file_name}")
        return None

    # 2. 预处理音频
    if not ensure_audio_standard(input_path_abs, processed_audio_path):
        print(f"❌ 音频处理失败: {file_name}")
        return None
    
    # 3. 删除源文件
    try:
        if os.path.exists(input_path_abs): 
            os.remove(input_path_abs) 
            print(f"🗑️ 已删除源文件: {file_name}")
    except Exception as e:
        print(f"⚠️ 删除源文件失败: {e}")

    # 4. 转录
    try:
        txt_path = transcribe_one_file(processed_audio_path, TEXT_FOLDER)
    except Exception as e:
        print(f"❌ 转录过程出错: {e}")
        txt_path = None

    if os.path.exists(processed_audio_path): os.remove(processed_audio_path)
    
    if not txt_path: return None

    # 5. 总结
    try:
        md_path, info = summarize_one_file(txt_path, SUMMARY_FOLDER)
    except Exception as e:
        print(f"❌ 总结过程出错: {e}")
        md_path, info = None, None
    
    if os.path.exists(txt_path): os.remove(txt_path)

    # 6. 准备给 n8n 的回传数据 (=== 关键修复部分 ===)
    if info and md_path and os.path.exists(md_path):
        # 获取原始文件名
        original_name = os.path.basename(md_path)
        
        # 🛠️ 修复：清洗文件名
        # replace(":", "-")  -> 把冒号换成短横线 (解决时间格式 10:48)
        # replace("/", "-")  -> 把斜杠换成短横线 (解决路径误判 10/48)
        # replace("\\", "-") -> 把反斜杠换成短横线 (解决 Windows 路径误判)
        # replace(" ", "_")  -> 把空格换成下划线 (解决 URL 编码问题)
        safe_name = original_name.replace(":", "-").replace("/", "-").replace("\\", "-").replace(" ", "_")
        
        # 设定新的存储路径到 md_output 文件夹
        temp_md_path = os.path.join(MD_TEMP_FOLDER, safe_name)
        
        try:
            # 复制文件并重命名为安全的文件名
            shutil.copy2(md_path, temp_md_path)
            
            # 路径映射 (Host -> Docker)
            info['full_path'] = temp_md_path.replace(MD_TEMP_FOLDER, "/home/node/.n8n-files/md_output")
            
            # ⚠️ 重要：更新 info 里的 file_name，确保 n8n 拿到的是清洗后的名字
            info['file_name'] = safe_name 
            info['source_type'] = file_type
            
        except Exception as e:
            print(f"❌ 文件复制/重命名失败: {e}")
            return None

    print(f"✅ ========== {file_name} 处理完成 ==========")
    return info

def main():
    sys.stdout = DualLogger(LOG_FILE)
    sys.stderr = sys.stdout

    print(f"\n------------------------------------------------")
    print(f"⏰ 触发时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # === 1. 关键逻辑：检查是否加锁 ===
    if not acquire_lock():
        print("🔒 检测到上一次任务仍在运行中 (存在 running.lock)。")
        print("🚫 本次触发跳过，避免多开卡死。")
        # 直接返回空结果，n8n 那边会收到 "no_task"，这是安全的
        return []

    # 使用 try...finally 确保无论代码是否报错，最后一定解锁
    try:
        print("🎙️ 会议助理 v5.3 (防拥堵安全版)")
        
        results = []
        ALL_SUPPORTED_EXTS = VIDEO_EXTS + AUDIO_EXTS
        
        # 扫描文件
        video_files = []
        if os.path.exists(VIDEO_FOLDER):
            raw_files = os.listdir(VIDEO_FOLDER)
            video_files = [f for f in raw_files if f.lower().endswith(ALL_SUPPORTED_EXTS) and not f.startswith("._")]

        audio_files = []
        if os.path.exists(AUDIO_FOLDER):
            raw_audio = os.listdir(AUDIO_FOLDER)
            audio_files = [f for f in raw_audio if f.lower().endswith(AUDIO_EXTS) and "_processed" not in f and not f.startswith("._")]
        
        tasks = []
        for f in video_files: tasks.append({'name': f, 'folder': VIDEO_FOLDER, 'type': 'video'})
        for f in audio_files: tasks.append({'name': f, 'folder': AUDIO_FOLDER, 'type': 'audio'})
        
        if not tasks:
            print("😴 当前无新文件，待机中...")
            return results

        print(f"🚀 发现 {len(tasks)} 个新任务，锁定队列开始处理...")
        
        tasks.sort(key=lambda x: x['name'])

        for i, task in enumerate(tasks):
            try:
                info = process_one_cycle(task['name'], task['folder'], task['type'])
                if info:
                    results.append(info)
            except Exception as e:
                print(f"❌ 任务出错: {e}")
                import traceback
                traceback.print_exc()
            
            # 任务间歇
            if i < len(tasks) - 1: time.sleep(3) 
        
        return results

    finally:
        # === 2. 关键逻辑：运行完必须解锁 ===
        release_lock()

if __name__ == "__main__":
    final_results = main()
    
    report = {
        "status": "completed" if final_results else "skipped_or_empty",
        "count": len(final_results) if final_results else 0,
        "details": final_results,
        "time": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    print(f"\nN8N_RESULT: {json.dumps(report, ensure_ascii=False)}")