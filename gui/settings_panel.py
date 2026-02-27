import customtkinter as ctk
from tkinter import filedialog
from constants import HORIZONTAL_ANGLES, VERTICAL_ANGLES

class SettingsPanel(ctk.CTkScrollableFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.video_path_var = ctk.StringVar()
        self.lut_path_var = ctk.StringVar()
        self.h_fov_var = ctk.DoubleVar(value=90.0)
        self.v_fov_var = ctk.DoubleVar(value=90.0)
        self.width_var = ctk.StringVar(value="1920")
        self.fps_var = ctk.StringVar(value="1.0")
        
        self.saturation_var = ctk.DoubleVar(value=1.0)
        self.contrast_var = ctk.DoubleVar(value=1.0)
        self.brightness_var = ctk.DoubleVar(value=0.0)
        self.gamma_var = ctk.DoubleVar(value=1.0)
        self.angle_vars = {}

        self._build_ui()

    def _build_ui(self):
        # 1. ファイル選択
        ctk.CTkLabel(self, text="1. ファイル選択", font=ctk.CTkFont(weight="bold", size=14)).pack(anchor="w", pady=(10, 5), padx=10)
        file_frame = ctk.CTkFrame(self, fg_color="transparent")
        file_frame.pack(fill="x", padx=10)
        ctk.CTkLabel(file_frame, text="動画:").pack(side="left", padx=(0, 5))
        ctk.CTkEntry(file_frame, textvariable=self.video_path_var, state="readonly", width=200).pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(file_frame, text="選択...", width=60, command=self._browse_video).pack(side="left")

        ctk.CTkFrame(self, height=2, fg_color="gray").pack(fill="x", padx=10, pady=10)

        # 2. 切り出し設定
        ctk.CTkLabel(self, text="2. 切り出し設定", font=ctk.CTkFont(weight="bold", size=14)).pack(anchor="w", pady=(0, 5), padx=10)
        angle_frame = ctk.CTkFrame(self)
        angle_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(angle_frame, text="↓P / Y→", width=60).grid(row=0, column=0, padx=2, pady=2)
        for col, yaw in enumerate(HORIZONTAL_ANGLES):
            ctk.CTkLabel(angle_frame, text=f"{yaw: >4}").grid(row=0, column=col+1, padx=2, pady=2)
            
        for row, pitch in enumerate(VERTICAL_ANGLES):
            ctk.CTkLabel(angle_frame, text=f"{pitch: >3}°", width=60, anchor="e").grid(row=row+1, column=0, padx=2, pady=2)
            for col, yaw in enumerate(HORIZONTAL_ANGLES):
                var = ctk.BooleanVar(value=(pitch == 0 and yaw % 90 == 0))
                self.angle_vars[(yaw, pitch)] = var
                ctk.CTkCheckBox(angle_frame, text="", variable=var, width=20).grid(row=row+1, column=col+1, padx=2, pady=2)

        param_frame = ctk.CTkFrame(self, fg_color="transparent")
        param_frame.pack(fill="x", padx=10, pady=5)
        
        self._add_slider_row(param_frame, "水平FOV", self.h_fov_var, 30, 160, 130, row=0)
        self._add_slider_row(param_frame, "垂直FOV", self.v_fov_var, 30, 160, 130, row=1)
        
        ctk.CTkLabel(param_frame, text="出力幅(px)").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        ctk.CTkEntry(param_frame, textvariable=self.width_var, width=80).grid(row=2, column=1, sticky="w", padx=5, pady=5)
        
        ctk.CTkLabel(param_frame, text="出力FPS").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        ctk.CTkEntry(param_frame, textvariable=self.fps_var, width=80).grid(row=3, column=1, sticky="w", padx=5, pady=5)

        ctk.CTkFrame(self, height=2, fg_color="gray").pack(fill="x", padx=10, pady=10)

        # 3. 色調整設定
        ctk.CTkLabel(self, text="3. 色調整設定 (オプション)", font=ctk.CTkFont(weight="bold", size=14)).pack(anchor="w", pady=(0, 5), padx=10)
        self.color_toggle_btn = ctk.CTkButton(self, text="設定を展開", command=self._toggle_color_settings)
        self.color_toggle_btn.pack(anchor="w", padx=10, pady=5)

        self.color_frame = ctk.CTkFrame(self, fg_color="transparent")
        
        lut_row = ctk.CTkFrame(self.color_frame, fg_color="transparent")
        lut_row.pack(fill="x", pady=5)
        ctk.CTkLabel(lut_row, text="LUT:").pack(side="left", padx=5)
        ctk.CTkEntry(lut_row, textvariable=self.lut_path_var, state="readonly", width=150).pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(lut_row, text="選択...", width=60, command=self._browse_lut).pack(side="left", padx=5)

        color_param_frame = ctk.CTkFrame(self.color_frame, fg_color="transparent")
        color_param_frame.pack(fill="x", pady=5)
        self._add_slider_row(color_param_frame, "彩度", self.saturation_var, 0.0, 2.0, 40, row=0)
        self._add_slider_row(color_param_frame, "コントラスト", self.contrast_var, 0.0, 2.0, 40, row=1)
        self._add_slider_row(color_param_frame, "明るさ", self.brightness_var, -1.0, 1.0, 40, row=2)
        self._add_slider_row(color_param_frame, "ガンマ", self.gamma_var, 0.1, 3.0, 29, row=3)
        
        self.color_settings_visible = False

    def _add_slider_row(self, parent, label_text, variable, from_, to, steps, row):
        ctk.CTkLabel(parent, text=label_text).grid(row=row, column=0, sticky="e", padx=5, pady=5)
        slider = ctk.CTkSlider(parent, variable=variable, from_=from_, to=to, number_of_steps=steps)
        slider.grid(row=row, column=1, sticky="we", padx=5, pady=5)
        val_label = ctk.CTkLabel(parent, text="", width=40, anchor="w")
        val_label.grid(row=row, column=2, sticky="w", padx=5)
        
        def update_lbl(*args):
            val_label.configure(text=f"{variable.get():.2f}")
        variable.trace_add("write", update_lbl)
        update_lbl()

    def _browse_video(self):
        path = filedialog.askopenfilename(filetypes=[("動画ファイル", "*.mov *.mp4")])
        if path: self.video_path_var.set(path)

    def _browse_lut(self):
        path = filedialog.askopenfilename(filetypes=[("Cube LUT", "*.cube")])
        if path: self.lut_path_var.set(path)

    def _toggle_color_settings(self):
        if self.color_settings_visible:
            self.color_frame.pack_forget()
            self.color_toggle_btn.configure(text="設定を展開")
        else:
            self.color_frame.pack(fill="x", padx=10, pady=5)
            self.color_toggle_btn.configure(text="設定を閉じる")
        self.color_settings_visible = not self.color_settings_visible

    def get_selected_transforms(self):
        transforms = []
        for pitch in VERTICAL_ANGLES:
            for yaw in HORIZONTAL_ANGLES:
                if self.angle_vars[(yaw, pitch)].get():
                    transforms.append((yaw, pitch, 0))
        return transforms

    def get_settings(self):
        return {
            'video_path': self.video_path_var.get(),
            'lut_path': self.lut_path_var.get(),
            'h_fov': self.h_fov_var.get(),
            'v_fov': self.v_fov_var.get(),
            'width': int(self.width_var.get() or 1920),
            'fps': self.fps_var.get() or "2.0",
            'saturation': self.saturation_var.get(),
            'contrast': self.contrast_var.get(),
            'brightness': self.brightness_var.get(),
            'gamma': self.gamma_var.get(),
        }