import os
import threading
import tempfile
import traceback
import time
from core.ffmpeg_runner import FFmpegRunner
from core.utils import sanitize_path_for_ffmpeg_filter

class VideoProcessor:
    def __init__(self, callbacks):
        self.callbacks = callbacks
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cancel_event = None

    def log(self, msg):
        if 'log' in self.callbacks:
            self.callbacks['log'](msg)

    def generate_preview_async(self, video_path, transforms, settings):
        def task():
            try:
                self.log("プレビュー画像を生成中...")
                first_frame_path = os.path.join(self.temp_dir.name, "first_frame.png")
                cmd_extract = ['ffmpeg', '-y', '-i', video_path, '-vframes', '1', '-f', 'image2', first_frame_path]
                
                success, err = FFmpegRunner.run_sync(cmd_extract, "フレーム抽出", self.log)
                if not success:
                    self.callbacks['error'](err)
                    self.callbacks['preview_done'](None)
                    return

                self.callbacks['preview_first_frame'](first_frame_path)

                preview_paths = []
                fov = settings["fov"]
                for i, (yaw, pitch, roll) in enumerate(transforms):
                    self.log(f"  - 適用後プレビュー {i + 1}/{len(transforms)} を生成中... (Y:{yaw}, P:{pitch})")
                    preview_after_path = os.path.join(self.temp_dir.name, f"preview_after_{i}.jpg")
                    
                    filter_list = [f'v360=output=rectilinear:h_fov={fov}:v_fov={fov}:w=480:h=480:yaw={yaw}:pitch={pitch}:roll={roll}']
                    if settings.get('lut_path') and os.path.exists(settings['lut_path']):
                        filter_list.append(f"lut3d=file='{sanitize_path_for_ffmpeg_filter(settings['lut_path'])}'")
                    eq_options = f'eq=saturation={settings["saturation"]}:contrast={settings["contrast"]}:brightness={settings["brightness"]}:gamma={settings["gamma"]}'
                    if eq_options != "eq=saturation=1.0:contrast=1.0:brightness=0.0:gamma=1.0":
                        filter_list.append(eq_options)
                    
                    final_filters = ",".join(filter_list)
                    cmd_preview = ['ffmpeg', '-y', '-i', first_frame_path, '-vf', final_filters, preview_after_path]
                    
                    success, err = FFmpegRunner.run_sync(cmd_preview, f"適用後プレビュー{i+1}")
                    if success:
                        preview_paths.append((yaw, pitch, preview_after_path))
                    else:
                        self.log(f"プレビュー生成失敗: {err}")

                self.log("プレビューを更新しました。")
                self.callbacks['preview_done'](preview_paths)
            except Exception as e:
                self.callbacks['error'](f"プレビュー処理中にエラー:\n{traceback.format_exc()}")
                self.callbacks['preview_done'](None)

        threading.Thread(target=task, daemon=True).start()

    def run_processing_async(self, video_path, transforms, settings):
        self.cancel_event = threading.Event()
        def task():
            try:
                # 動画の総再生時間を取得
                total_duration = FFmpegRunner.get_video_duration(video_path)
                
                output_dir = os.path.join(os.path.dirname(video_path), "output_images")
                os.makedirs(output_dir, exist_ok=True)

                output_size = settings['size']
                fov = settings['fov']
                video_name = os.path.splitext(os.path.basename(video_path))[0]
                
                if output_size <= 0:
                    raise ValueError("出力サイズが0以下です。")

                color_filter_list = []
                if settings.get('lut_path') and os.path.exists(settings['lut_path']):
                    color_filter_list.append(f"lut3d=file='{sanitize_path_for_ffmpeg_filter(settings['lut_path'])}'")
                eq_options = f'eq=saturation={settings["saturation"]}:contrast={settings["contrast"]}:brightness={settings["brightness"]}:gamma={settings["gamma"]}'
                if eq_options != "eq=saturation=1.0:contrast=1.0:brightness=0.0:gamma=1.0":
                    color_filter_list.append(eq_options)

                total_tasks = len(transforms)
                success_count = 0
                cancelled = False
                
                start_time = time.time()

                for index, (yaw, pitch, roll) in enumerate(transforms):
                    if self.cancel_event.is_set():
                        cancelled = True
                        break

                    # 進捗表示のコールバック関数
                    def progress_cb(current_sec):
                        if total_duration > 0:
                            # 現在のタスクの進捗 (0.0 ~ 1.0)
                            task_progress = max(0.0, min(1.0, current_sec / total_duration))
                            # 全体の進捗 (0.0 ~ 1.0)
                            overall_progress = (index + task_progress) / total_tasks
                            
                            elapsed_time = time.time() - start_time
                            # 1%以上進んでいたら予測する（計算のブレを防ぐため）
                            if overall_progress > 0.01:
                                total_estimated = elapsed_time / overall_progress
                                remain_sec = total_estimated - elapsed_time
                                
                                eta_struct = time.localtime(time.time() + remain_sec)
                                eta_str = time.strftime("%H:%M:%S", eta_struct)
                                
                                rm_m, rm_s = divmod(int(remain_sec), 60)
                                rm_h, rm_m = divmod(rm_m, 60)
                                remain_str = f"{rm_h}時間{rm_m}分{rm_s}秒" if rm_h > 0 else f"{rm_m}分{rm_s}秒"
                                
                                msg = f"処理中 {index+1}/{total_tasks} ({overall_progress*100:.1f}%) | 残り: {remain_str} (終了予定: {eta_str})"
                            else:
                                msg = f"処理中 {index+1}/{total_tasks} ({overall_progress*100:.1f}%) | 計算中..."
                        else:
                            msg = f"処理中 {index+1}/{total_tasks}"
                            overall_progress = index / total_tasks
                            
                        # app.pyの update_progress に渡す（1.0を最大値とする）
                        self.callbacks['progress'](overall_progress, 1.0, msg)


                    filter_chain = [
                        f'v360=input=e:output=rectilinear:h_fov={fov}:v_fov={fov}:w={output_size}:h={output_size}:yaw={yaw}:pitch={pitch}:roll={roll}',
                        f"fps={settings['fps']}"
                    ]
                    filter_chain.extend(color_filter_list)
                    
                    # タイムベースをミリ秒(1/1000)にし、PTSを経過時間(秒)×1000 に設定する
                    filter_chain.append("settb=1/1000")
                    filter_chain.append("setpts='round(T*1000)'")
                    final_filters = ",".join(filter_chain)
                    
                    output_file_pattern = os.path.join(output_dir, f'{video_name}_Y{yaw:+04d}_P{pitch:+03d}_%08d.jpg')

                    # -frame_pts 1 と -vsync 0 を指定して、PTS(ミリ秒)をそのままファイル名として出力する
                    cmd = [
                        'ffmpeg', '-y', '-i', video_path, 
                        '-vf', final_filters, 
                        '-vsync', '0', '-frame_pts', '1', 
                        '-qmin', '1', '-q', '1', 
                        output_file_pattern
                    ]

                    desc = f"視点 {index + 1}/{total_tasks} (Y:{yaw}, P:{pitch}) の処理"
                    success, was_cancelled, err = FFmpegRunner.run_async(cmd, desc, self.cancel_event, self.log, progress_callback=progress_cb)

                    if was_cancelled:
                        cancelled = True
                        break
                    if success:
                        success_count += 1
                        # タスク完了時に進捗を更新
                        self.callbacks['progress']((index + 1) / total_tasks, 1.0, f"完了 {index+1}/{total_tasks}")
                    else:
                        self.callbacks['error'](err)

                self.callbacks['done'](success_count, total_tasks, cancelled, output_dir)
            except Exception as e:
                self.callbacks['error'](f"処理中にエラーが発生しました:\n{traceback.format_exc()}")

        threading.Thread(target=task, daemon=True).start()

    def cancel(self):
        if self.cancel_event:
            self.cancel_event.set()

    def cleanup(self):
        self.temp_dir.cleanup()