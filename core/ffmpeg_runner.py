import subprocess
import threading
import os
import traceback
import time
import re

class FFmpegRunner:
    # ログから時間(time=00:01:23.45)を抽出する正規表現
    time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")

    @staticmethod
    def get_video_duration(video_path):
        """動画の総再生時間（秒）を取得する"""
        cmd = ['ffmpeg', '-i', video_path]
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        process = subprocess.run(cmd, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace', creationflags=creationflags)
        
        # Duration: 00:02:30.50 などを探す
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", process.stderr)
        if match:
            h, m, s = match.groups()
            return int(h) * 3600 + int(m) * 60 + float(s)
        return 0.0

    @staticmethod
    def run_sync(command, description="FFmpeg", logger=None):
        try:
            if logger:
                logger(f"--- Running {description} Command (Sync) ---\n{' '.join(command)}")
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace', creationflags=creationflags)
            if logger:
                logger(f"--- {description} Success ---")
            return True, None
        except subprocess.CalledProcessError as e:
            error_output = f"FFmpegでエラーが発生しました: {description}\n\nコマンド:\n{' '.join(e.cmd)}\n\nエラー出力:\n{e.stderr}"
            return False, error_output

    @staticmethod
    def run_async(command, description="FFmpeg", cancel_event=None, logger=None, progress_callback=None):
        if logger:
            logger(f"--- Running {description} Command (Async) ---\n{' '.join(command)}")
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                       text=True, encoding='utf-8', errors='replace', creationflags=creationflags)
            
            stderr_lines = []
            def reader_thread():
                try:
                    for line in iter(process.stderr.readline, ''):
                        stderr_lines.append(line)
                        # 進捗の抽出とコールバック
                        if progress_callback:
                            match = FFmpegRunner.time_pattern.search(line)
                            if match:
                                h, m, s = match.groups()
                                current_sec = int(h) * 3600 + int(m) * 60 + float(s)
                                progress_callback(current_sec)
                finally:
                    process.stderr.close()

            reader = threading.Thread(target=reader_thread)
            reader.start()

            # プロセスが終了するまでループで監視
            while process.poll() is None:
                if cancel_event and cancel_event.is_set():
                    if logger:
                        logger(f"--- Cancelling {description} ---")
                    process.terminate()
                    process.wait()
                    reader.join()
                    return False, True, "Cancelled"
                time.sleep(0.1)

            reader.join()
            if process.returncode == 0:
                if logger:
                    logger(f"--- {description} Success ---")
                return True, False, None
            else:
                stderr_output = "".join(stderr_lines)
                error_msg = f"FFmpegでエラーが発生しました: {description}\n\nコマンド:\n{' '.join(command)}\n\nエラー出力:\n{stderr_output}"
                return False, False, error_msg

        except Exception as e:
            error_msg = f"コマンド実行中に予期せぬエラー: {description}\n{traceback.format_exc()}"
            return False, False, error_msg