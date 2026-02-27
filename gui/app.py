import customtkinter as ctk
import os
from gui.settings_panel import SettingsPanel
from gui.preview_panel import PreviewPanel
from core.processor import VideoProcessor

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class LogWindow(ctk.CTkToplevel):
    """ログを表示用ポップアップウィンドウ"""
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.title("実行ログ")
        self.geometry("700x500")
        
        # [×]ボタンを押したときにウィンドウを破棄せず、隠すだけにする
        self.protocol("WM_DELETE_WINDOW", self.hide_window)
        
        self.textbox = ctk.CTkTextbox(self, font=ctk.CTkFont(family="Consolas", size=12))
        self.textbox.pack(fill="both", expand=True, padx=10, pady=10)
        self.textbox.configure(state="disabled")
        
        self.btn_clear = ctk.CTkButton(self, text="ログをクリア", command=self.clear_log)
        self.btn_clear.pack(side="bottom", pady=(0, 10))

    def hide_window(self):
        self.withdraw()
        
    def append_log(self, msg):
        self.textbox.configure(state="normal")
        self.textbox.insert("end", msg + "\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")
        
    def clear_log(self):
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("360度動画 アライメント前処理ツール")
        self.geometry("1200x800")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 1. メイン領域 (左:設定, 右:プレビュー)
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True)
        
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=4)
        self.main_frame.grid_columnconfigure(1, weight=6)
        
        self.left_container = ctk.CTkFrame(self.main_frame)
        self.left_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))
        
        self.preview_panel = PreviewPanel(self.main_frame)
        self.preview_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=(10, 0))
        
        self.settings_panel = SettingsPanel(self.left_container)
        self.settings_panel.pack(fill="both", expand=True)
        
        self.action_frame = ctk.CTkFrame(self.left_container, fg_color="transparent")
        self.action_frame.pack(fill="x", pady=10)
        
        self.btn_preview = ctk.CTkButton(self.action_frame, text="プレビュー更新", command=self.on_preview)
        self.btn_preview.pack(side="left", padx=5, expand=True, fill="x")
        
        self.btn_run = ctk.CTkButton(self.action_frame, text="本実行", command=self.on_run, fg_color="green", hover_color="darkgreen")
        self.btn_run.pack(side="left", padx=5, expand=True, fill="x")
        
        self.btn_cancel = ctk.CTkButton(self.action_frame, text="中止", command=self.on_cancel, fg_color="red", hover_color="darkred", state="disabled")
        self.btn_cancel.pack(side="left", padx=5, expand=True, fill="x")
        
        self.progress_frame = ctk.CTkFrame(self.left_container, fg_color="transparent")
        self.lbl_progress = ctk.CTkLabel(self.progress_frame, text="進捗:")
        self.lbl_progress.pack(anchor="w")
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.pack(fill="x", pady=5)
        self.progress_bar.set(0)
        
        # 2. ステータスバー (最下部)
        self.statusbar = ctk.CTkFrame(self, height=35, corner_radius=0)
        self.statusbar.pack(fill="x", side="bottom")

        self.btn_show_log = ctk.CTkButton(self.statusbar, text="ログウィンドウ表示", width=140, height=24, command=self.toggle_log_window)
        self.btn_show_log.pack(side="right", padx=10, pady=5)

        self.lbl_status = ctk.CTkLabel(self.statusbar, text="準備完了", anchor="w")
        self.lbl_status.pack(side="left", fill="x", expand=True, padx=10)

        # 3. ログウィンドウの初期化 (起動時は非表示)
        self.log_window = LogWindow(self)
        self.log_window.withdraw()

        self.processor = VideoProcessor({
            'log': self.append_log,
            'error': self.show_error,
            'preview_first_frame': self.on_preview_first_frame,
            'preview_done': self.on_preview_done,
            'progress': self.on_progress,
            'done': self.on_run_done
        })

    def toggle_log_window(self):
        if self.log_window.state() == "withdrawn":
            self.log_window.deiconify()  # ウィンドウを表示
        self.log_window.focus()          # ウィンドウを最前面に

    def append_log(self, msg):
        def _update():
            self.log_window.append_log(msg)
            # ステータスバーにも最新の1行を表示
            last_line = msg.strip().split('\n')[-1]
            if last_line:
                self.lbl_status.configure(text=last_line)
        self.after(0, _update)

    def show_error(self, err_msg):
        self.append_log(f"\n[エラー]\n{err_msg}\n")
        self.toggle_log_window()  # エラー時は自動でログウィンドウを開く
        
    def _validate_inputs(self):
        settings = self.settings_panel.get_settings()
        if not settings['video_path'] or not os.path.exists(settings['video_path']):
            self.show_error("有効な動画ファイルが選択されていません。")
            return False, None, None
        
        transforms = self.settings_panel.get_selected_transforms()
        if not transforms:
            self.show_error("角度が選択されていません。")
            return False, None, None
            
        return True, settings, transforms

    def on_preview(self):
        valid, settings, transforms = self._validate_inputs()
        if not valid: return
        
        self.btn_preview.configure(state="disabled")
        self.btn_run.configure(state="disabled")
        self.processor.generate_preview_async(settings['video_path'], transforms, settings)

    def on_preview_first_frame(self, path):
        self.after(0, lambda: self.preview_panel.update_before_image(path))

    def on_preview_done(self, preview_paths):
        def _update():
            if preview_paths:
                self.preview_panel.update_after_images(preview_paths)
            self.btn_preview.configure(state="normal")
            self.btn_run.configure(state="normal")
        self.after(0, _update)

    def on_run(self):
        valid, settings, transforms = self._validate_inputs()
        if not valid: return
        
        self.btn_preview.configure(state="disabled")
        self.btn_run.configure(state="disabled")
        self.btn_cancel.configure(state="normal")
        
        self.progress_frame.pack(fill="x", padx=5, pady=5)
        self.progress_bar.set(0)
        self.lbl_progress.configure(text="処理を開始しています...")
        
        self.append_log("\n--- 本処理を開始します ---")
        self.processor.run_processing_async(settings['video_path'], transforms, settings)

    def on_progress(self, current, total, msg):
        def _update():
            self.progress_bar.set(current / total if total > 0 else 0)
            self.lbl_progress.configure(text=msg)
            self.lbl_status.configure(text=msg)
        self.after(0, _update)

    def on_run_done(self, success_count, total_tasks, cancelled, output_dir):
        def _update():
            self.append_log("\n==================== 処理結果 ====================")
            if cancelled:
                self.append_log(f"処理が中止されました。({success_count}/{total_tasks} 完了)")
            elif success_count == total_tasks:
                self.append_log(f"全ての処理が完了しました！\n出力先: {os.path.abspath(output_dir)}")
            else:
                self.append_log(f"いくつかの処理に失敗しました。({success_count}/{total_tasks} 完了)")
            
            self.btn_preview.configure(state="normal")
            self.btn_run.configure(state="normal")
            self.btn_cancel.configure(state="disabled")
            self.progress_frame.pack_forget()
        self.after(0, _update)

    def on_cancel(self):
        self.append_log("--- 中止命令を受け付けました ---")
        self.btn_cancel.configure(state="disabled")
        self.processor.cancel()

    def on_closing(self):
        if self.processor:
            self.processor.cancel()
            self.processor.cleanup()
        self.destroy()