import os
import threading
import tempfile
import traceback
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
                for i, (yaw, pitch, roll) in enumerate(transforms):
                    self.log(f"  - 適用後プレビュー {i + 1}/{len(transforms)} を生成中... (Y:{yaw}, P:{pitch})")
                    preview_after_path = os.path.join(self.temp_dir.name, f"preview_after_{i}.jpg")
                    
                    filter_list = [f'v360=output=rectilinear:h_fov={settings["h_fov"]}:v_fov={settings["v_fov"]}:w=480:h=480:yaw={yaw}:pitch={pitch}:roll={roll}']
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
                output_dir = os.path.join(os.path.dirname(video_path), "output_images")
                os.makedirs(output_dir, exist_ok=True)

                output_width = settings['width']
                h_fov = settings['h_fov']
                v_fov = settings['v_fov']
                output_height = int(output_width * (v_fov / h_fov))
                if output_height <= 0:
                    raise ValueError("計算後の高さが0以下です。")

                color_filter_list = []
                if settings.get('lut_path') and os.path.exists(settings['lut_path']):
                    color_filter_list.append(f"lut3d=file='{sanitize_path_for_ffmpeg_filter(settings['lut_path'])}'")
                eq_options = f'eq=saturation={settings["saturation"]}:contrast={settings["contrast"]}:brightness={settings["brightness"]}:gamma={settings["gamma"]}'
                if eq_options != "eq=saturation=1.0:contrast=1.0:brightness=0.0:gamma=1.0":
                    color_filter_list.append(eq_options)

                total_tasks = len(transforms)
                success_count = 0
                cancelled = False

                for index, (yaw, pitch, roll) in enumerate(transforms):
                    if self.cancel_event.is_set():
                        cancelled = True
                        break

                    self.callbacks['progress'](index, total_tasks, f"視点 {index + 1}/{total_tasks} を処理中...")

                    filter_chain = [
                        f'v360=input=e:output=rectilinear:h_fov={h_fov}:v_fov={v_fov}:w={output_width}:h={output_height}:yaw={yaw}:pitch={pitch}:roll={roll}',
                        f"fps={settings['fps']}"
                    ]
                    filter_chain.extend(color_filter_list)
                    final_filters = ",".join(filter_chain)
                    
                    output_file_pattern = os.path.join(output_dir, f'Y{yaw:+04d}_P{pitch:+03d}_frame_%04d.jpg')
                    cmd = ['ffmpeg', '-y', '-i', video_path, '-vf', final_filters, '-qmin', '1', '-q', '1', output_file_pattern]

                    desc = f"視点 {index + 1}/{total_tasks} (Y:{yaw}, P:{pitch}) の処理"
                    success, was_cancelled, err = FFmpegRunner.run_async(cmd, desc, self.cancel_event, self.log)

                    if was_cancelled:
                        cancelled = True
                        break
                    if success:
                        success_count += 1
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