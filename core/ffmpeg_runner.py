import subprocess
import threading
import os
import traceback

class FFmpegRunner:
    @staticmethod
    def run_sync(command, description="FFmpeg", logger=None):
        try:
            if logger:
                logger(f"--- Running {description} Command (Sync) ---\n{' '.join(command)}")
            subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
            if logger:
                logger(f"--- {description} Success ---")
            return True, None
        except subprocess.CalledProcessError as e:
            error_output = f"FFmpegでエラーが発生しました: {description}\n\nコマンド:\n{' '.join(e.cmd)}\n\nエラー出力:\n{e.stderr}"
            return False, error_output

    @staticmethod
    def run_async(command, description="FFmpeg", cancel_event=None, logger=None):
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
                finally:
                    process.stderr.close()

            reader = threading.Thread(target=reader_thread)
            reader.start()

            while process.poll() is None:
                if cancel_event and cancel_event.is_set():
                    if logger:
                        logger(f"--- Cancelling {description} ---")
                    process.terminate()
                    process.wait()
                    reader.join()
                    return False, True, "Cancelled"
                process.wait(timeout=0.1)

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