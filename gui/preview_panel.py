import customtkinter as ctk
from core.utils import load_and_resize_image
from constants import BEFORE_PREVIEW_SIZE, AFTER_PREVIEW_SIZE, MAX_PREVIEWS

class PreviewPanel(ctk.CTkScrollableFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # 適用前画像
        ctk.CTkLabel(self, text="適用前（元動画の1フレーム目）", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        self.lbl_before = ctk.CTkLabel(self, text="No Image", width=BEFORE_PREVIEW_SIZE[0], height=BEFORE_PREVIEW_SIZE[1], fg_color="gray")
        self.lbl_before.pack(pady=5)
        
        ctk.CTkFrame(self, height=2, fg_color="gray").pack(fill="x", padx=10, pady=10)
        
        # 適用後画像
        ctk.CTkLabel(self, text="適用後プレビュー（選択した視点）", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        self.after_container = ctk.CTkFrame(self, fg_color="transparent")
        self.after_container.pack(fill="both", expand=True)
        self.after_labels = []
        
        for i in range(MAX_PREVIEWS):
            frame = ctk.CTkFrame(self.after_container)
            lbl_text = ctk.CTkLabel(frame, text="")
            lbl_text.pack(pady=2)
            lbl_img = ctk.CTkLabel(frame, text="No Image", width=AFTER_PREVIEW_SIZE[0], height=AFTER_PREVIEW_SIZE[1], fg_color="gray")
            lbl_img.pack(padx=5, pady=5)
            self.after_labels.append({"frame": frame, "text": lbl_text, "img": lbl_img})

    def update_before_image(self, path):
        img = load_and_resize_image(path, BEFORE_PREVIEW_SIZE)
        if img:
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=BEFORE_PREVIEW_SIZE)
            self.lbl_before.configure(image=ctk_img, text="")
            self.lbl_before.image = ctk_img

    def clear_after_images(self):
        for item in self.after_labels:
            item["frame"].grid_forget()
            item["img"].configure(image=None, text="No Image")
            item["text"].configure(text="")

    def update_after_images(self, preview_data):
        self.clear_after_images()
        columns = 2
        for i, (yaw, pitch, path) in enumerate(preview_data):
            if i >= MAX_PREVIEWS: break
            
            img = load_and_resize_image(path, AFTER_PREVIEW_SIZE)
            if img:
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=AFTER_PREVIEW_SIZE)
                item = self.after_labels[i]
                item["img"].configure(image=ctk_img, text="")
                item["img"].image = ctk_img
                item["text"].configure(text=f"Yaw:{yaw}, Pitch:{pitch}")
                
                row, col = divmod(i, columns)
                item["frame"].grid(row=row, column=col, padx=5, pady=5)