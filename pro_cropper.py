"""pro_cropper.py: A professional 800x650 image cropper with live preview, stats, and persistent history."""
import argparse
import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageOps, ImageTk

# --- Configuration ---
OUT_W, OUT_H = 800, 650
ASPECT = OUT_W / OUT_H
POS = {"left": 0, "top": 0, "center": 0.5, "right": 1, "bottom": 1}

# Colors
BG_MAIN = "#121212"
BG_PANEL = "#1e1e1e"
LIME = "#D4FF33"
TEXT_GRAY = "#888888"

# Path for history
HISTORY_FILE = Path(__file__).parent / "history.json"

def load(f):
    return ImageOps.exif_transpose(Image.open(f)).convert("RGB")

def best_crop_size(im):
    cw = im.width
    ch = int(round(cw / ASPECT))
    if ch > im.height:
        ch = im.height
        cw = int(round(ch * ASPECT))
    return cw, ch

def do_crop(im, x, y):
    cw, ch = best_crop_size(im)
    x = int(max(0, min(x, im.width - cw)))
    y = int(max(0, min(y, im.height - ch)))
    return im.crop((x, y, x + cw, y + ch)).resize((OUT_W, OUT_H), Image.LANCZOS)

# --- Modern Professional GUI ---
def gui():
    ctk.set_appearance_mode("dark")
    
    root = ctk.CTk()
    root.title("Pro Cropper")
    root.geometry("1150x780")
    root.configure(fg_color=BG_MAIN)
    root.minsize(950, 600)

    # Fonts
    try:
        ctk.FontManager.load_font("Urbanist-Regular.ttf")
        ctk.FontManager.load_font("Urbanist-Bold.ttf")
        font_family = "Urbanist"
    except:
        font_family = "Helvetica"
    
    font_h1 = ctk.CTkFont(family=font_family, size=24, weight="bold")
    font_h2 = ctk.CTkFont(family=font_family, size=16, weight="bold")
    font_btn = ctk.CTkFont(family=font_family, size=14, weight="bold")
    font_txt = ctk.CTkFont(family=font_family, size=12)
    font_stat = ctk.CTkFont(family=font_family, size=14, weight="bold")

    # App State
    st = {
        "stats_saved": 0,
        "stats_edited": 0,
        "recent_files": [], 
        "im": None,
        "saved": True
    }

    # Top Navigation Bar
    top_bar = ctk.CTkFrame(root, fg_color="transparent", height=60)
    top_bar.pack(fill="x", padx=20, pady=(15, 0))
    
    ctk.CTkLabel(top_bar, text="Cropper", font=font_h1).pack(side="left")
    
    # Buttons (Right aligned)
    btn_save = ctk.CTkButton(top_bar, text="Save Image", font=font_btn, 
                             fg_color=LIME, text_color="black", hover_color="#b5db22",
                             corner_radius=10, width=120, state="disabled")
    btn_save.pack(side="right", padx=(10, 0))
    
    btn_open = ctk.CTkButton(top_bar, text="Open Image", font=font_btn, 
                             fg_color="transparent", border_width=1, border_color="#444",
                             hover_color="#333", corner_radius=10, width=120)
    btn_open.pack(side="right")

    # Stats Counters
    stats_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
    stats_frame.pack(side="right", padx=20)
    
    lbl_stat_edited = ctk.CTkLabel(stats_frame, text="Edited: 0", font=font_stat, text_color=TEXT_GRAY)
    lbl_stat_edited.pack(side="left", padx=15)
    
    lbl_stat_saved = ctk.CTkLabel(stats_frame, text="Saved: 0", font=font_stat, text_color=TEXT_GRAY)
    lbl_stat_saved.pack(side="left")

    # Main Layout
    main_frame = ctk.CTkFrame(root, fg_color="transparent")
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)

    # --- LEFT PANEL ---
    left_panel = ctk.CTkFrame(main_frame, fg_color=BG_PANEL, corner_radius=15, width=350)
    left_panel.pack(side="left", fill="y", padx=(0, 20))
    left_panel.pack_propagate(False)

    ctk.CTkLabel(left_panel, text="Live Preview (800x650)", font=font_h2).pack(pady=(20, 10))
    
    preview_cv = tk.Canvas(left_panel, width=300, height=244, bg="#000", highlightthickness=0)
    preview_cv.pack(pady=10)
    
    info_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
    info_frame.pack(fill="x", padx=20, pady=(10, 0))
    
    lbl_dims = ctk.CTkLabel(info_frame, text="Source: -- x --", font=font_txt, text_color=TEXT_GRAY)
    lbl_dims.pack(anchor="w", pady=5)
    
    lbl_crop = ctk.CTkLabel(info_frame, text="Crop Offset: X: 0, Y: 0", font=font_txt, text_color=TEXT_GRAY)
    lbl_crop.pack(anchor="w", pady=5)

    # --- RECENT FILES SECTION (Bottom Left) ---
    recent_container = ctk.CTkFrame(left_panel, fg_color="transparent")
    recent_container.pack(side="bottom", fill="x", padx=20, pady=20)
    
    recent_header = ctk.CTkFrame(recent_container, fg_color="transparent")
    recent_header.pack(fill="x", pady=(0, 10))
    ctk.CTkLabel(recent_header, text="Recent Files", font=font_h2).pack(side="left")
    
    # Small, pill-shaped "Show All" button (hidden by default)
    btn_show_all = ctk.CTkButton(
        recent_header, text="Show All", font=font_txt,
        fg_color="#444444", hover_color="#666666", text_color="white",
        corner_radius=15, width=70, height=24
    )
    
    # Non-scrollable grid for exactly up to 6 items
    recent_list_frame = ctk.CTkFrame(recent_container, fg_color="transparent")
    recent_list_frame.pack(fill="x")
    recent_list_frame.grid_columnconfigure((0, 1, 2), weight=1)

    # --- RIGHT PANEL ---
    right_panel = ctk.CTkFrame(main_frame, fg_color=BG_PANEL, corner_radius=15)
    right_panel.pack(side="left", fill="both", expand=True)

    # Editor View
    editor_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
    editor_frame.pack(fill="both", expand=True)
    
    # Top bar inside editor for the 'X' button
    editor_top = ctk.CTkFrame(editor_frame, fg_color="transparent", height=40)
    editor_top.pack(fill="x", padx=10, pady=(10, 0))
    
    btn_close_x = ctk.CTkButton(editor_top, text="✕", font=font_btn, width=30, height=30,
                                fg_color="transparent", hover_color="#331111", text_color="#ff4444",
                                state="disabled")
    btn_close_x.pack(side="left")

    cv = tk.Canvas(editor_frame, bg=BG_PANEL, highlightthickness=0)
    cv.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # --- GALLERY CONTAINER (With floating exit button) ---
    gallery_container = ctk.CTkFrame(right_panel, fg_color=BG_PANEL)
    gallery_frame = ctk.CTkScrollableFrame(gallery_container, fg_color=BG_PANEL)
    gallery_frame.pack(fill="both", expand=True)
    
    # Floating Exit Button (Placed relative to gallery_container so it doesn't scroll)
    btn_exit_gallery = ctk.CTkButton(
        gallery_container, text="Exit", font=font_btn,
        fg_color="#555555", hover_color="#777777", text_color="white",
        corner_radius=20, width=120, height=40
    )
    btn_exit_gallery.place(relx=0.95, rely=0.95, anchor="se") # Pinned to bottom right
    
    # --- HISTORY LOGIC ---
    def save_history():
        data = {
            "stats_saved": st["stats_saved"],
            "stats_edited": st["stats_edited"],
            "recent_paths": [str(item["path"]) for item in st["recent_files"]]
        }
        try:
            with open(HISTORY_FILE, "w") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Failed to save history: {e}")

    def load_history():
        if not HISTORY_FILE.exists():
            return
            
        try:
            with open(HISTORY_FILE, "r") as f:
                data = json.load(f)
                
            st["stats_saved"] = data.get("stats_saved", 0)
            st["stats_edited"] = data.get("stats_edited", 0)
            
            lbl_stat_edited.configure(text=f"Edited: {st['stats_edited']}")
            lbl_stat_saved.configure(text=f"Saved: {st['stats_saved']}")
            
            # Rebuild the recent files list
            for p_str in data.get("recent_paths", []):
                p = Path(p_str)
                if p.exists(): # Ensure file still exists on disk
                    im = load(p)
                    
                    # Use ImageOps.fit to crop-to-fill instead of thumbnail (squish)
                    thumb = ImageOps.fit(im, (80, 60), method=Image.LANCZOS)
                    tk_thumb = ctk.CTkImage(light_image=thumb, dark_image=thumb, size=(80, 60))
                    
                    thumb_large = ImageOps.fit(im, (140, 100), method=Image.LANCZOS)
                    tk_large = ctk.CTkImage(light_image=thumb_large, dark_image=thumb_large, size=(140, 100))
                    
                    st["recent_files"].append({
                        "path": p, 
                        "tk": tk_thumb, 
                        "tk_large": tk_large
                    })
            update_recent_ui()
        except Exception as e:
            print(f"Failed to load history: {e}")

    # --- LOGIC FUNCTIONS ---
    def draw():
        if not st["im"]: return
        if not st["saved"]:
            btn_save.configure(text="Save Changes", fg_color=LIME)
        else:
            btn_save.configure(text="Save Image", fg_color=LIME)

        im, sc = st["im"], st["sc"]
        cw, ch = best_crop_size(im)
        
        cv.delete("all")
        cw_canvas = cv.winfo_width()
        ch_canvas = cv.winfo_height()
        img_w, img_h = int(im.width * sc), int(im.height * sc)
        ox = (cw_canvas - img_w) // 2
        oy = (ch_canvas - img_h) // 2
        
        cv.create_image(ox, oy, image=st["tk"], anchor="nw")
        
        x, y = st["x"] * sc, st["y"] * sc
        cv.create_rectangle(ox + x, oy + y, ox + x + cw * sc, oy + y + ch * sc, outline=LIME, width=3)
        
        cv.create_rectangle(ox, oy, ox + img_w, oy + y, fill="black", stipple="gray50", outline="")
        cv.create_rectangle(ox, oy + y + ch * sc, ox + img_w, oy + img_h, fill="black", stipple="gray50", outline="")
        cv.create_rectangle(ox, oy + y, ox + x, oy + y + ch * sc, fill="black", stipple="gray50", outline="")
        cv.create_rectangle(ox + x + cw * sc, oy + y, ox + img_w, oy + y + ch * sc, fill="black", stipple="gray50", outline="")

        # Live Preview
        preview_im = im.crop((int(st["x"]), int(st["y"]), int(st["x"] + cw), int(st["y"] + ch)))
        preview_im = preview_im.resize((300, 244), Image.LANCZOS)
        st["tk_preview"] = ImageTk.PhotoImage(preview_im)
        
        preview_cv.delete("all")
        preview_cv.create_image(0, 0, image=st["tk_preview"], anchor="nw")
        lbl_crop.configure(text=f"Crop Offset: X: {int(st['x'])}, Y: {int(st['y'])}")

    def load_image(f_path):
        im = load(f_path)
        sc = min((cv.winfo_width() - 20) / im.width, (cv.winfo_height() - 20) / im.height, 1.0)
        cw, ch = best_crop_size(im)
        
        st.update(
            im=im, sc=sc, 
            x=(im.width - cw) / 2, y=(im.height - ch) / 2,
            f=Path(f_path),
            tk=ImageTk.PhotoImage(im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)),
            saved=False
        )
        
        st["stats_edited"] += 1
        lbl_stat_edited.configure(text=f"Edited: {st['stats_edited']}")
        btn_save.configure(state="normal")
        btn_close_x.configure(state="normal")
        lbl_dims.configure(text=f"Source: {im.width} x {im.height}")
        
        # Switch to Editor View
        gallery_container.pack_forget()
        editor_frame.pack(fill="both", expand=True)
        
        # Update Recent Files List
        st["recent_files"] = [x for x in st["recent_files"] if x["path"] != Path(f_path)]
        
        # Use ImageOps.fit to crop-to-fill instead of thumbnail (squish)
        thumb = ImageOps.fit(im, (80, 60), method=Image.LANCZOS)
        tk_thumb = ctk.CTkImage(light_image=thumb, dark_image=thumb, size=(80, 60))
        
        thumb_large = ImageOps.fit(im, (140, 100), method=Image.LANCZOS)
        tk_large = ctk.CTkImage(light_image=thumb_large, dark_image=thumb_large, size=(140, 100))
        
        # Don't store 'im' (PIL Image) in history to save RAM
        st["recent_files"].insert(0, {"path": Path(f_path), "tk": tk_thumb, "tk_large": tk_large})
        st["recent_files"] = st["recent_files"][:20]
        
        update_recent_ui()
        draw()
        save_history()

    def update_recent_ui():
        for widget in recent_list_frame.winfo_children():
            widget.destroy()
            
        if not st["recent_files"]:
            btn_show_all.pack_forget()
            return
            
        for i, item in enumerate(st["recent_files"][:6]):
            row, col = divmod(i, 3)
            btn = ctk.CTkButton(
                recent_list_frame, image=item["tk"], text="", width=80, height=60,
                fg_color="transparent", hover_color="#333", 
                command=lambda p=item["path"]: load_image(p)
            )
            btn.grid(row=row, column=col, padx=2, pady=2)
            
        if len(st["recent_files"]) > 6:
            btn_show_all.pack(side="right")
        else:
            btn_show_all.pack_forget()

    def close_session():
        if not st["im"]: return
        
        if not st["saved"]:
            ans = messagebox.askyesnocancel("Unsaved Changes", "You have unsaved changes. Save before closing?")
            if ans is None: return
            if ans: save()
                
        st["im"] = None
        st["saved"] = True
        cv.delete("all")
        preview_cv.delete("all")
        btn_save.configure(state="disabled", text="Save Image")
        btn_close_x.configure(state="disabled")
        lbl_dims.configure(text="Source: -- x --")
        lbl_crop.configure(text="Crop Offset: X: 0, Y: 0")
        
        gallery_container.pack_forget()
        editor_frame.pack(fill="both", expand=True)

    def show_gallery():
        if not st["recent_files"]: return
        editor_frame.pack_forget()
        gallery_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        for widget in gallery_frame.winfo_children():
            widget.destroy()
            
        # 3-column grid
        gallery_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        for i, item in enumerate(st["recent_files"]):
            row, col = divmod(i, 3)
            
            card = ctk.CTkFrame(gallery_frame, fg_color="#2a2a2a", corner_radius=10, width=160, height=160)
            card.grid_propagate(False) 
            card.grid(row=row, column=col, padx=15, pady=15)
            
            btn = ctk.CTkButton(
                card, image=item["tk_large"], text="", 
                fg_color="transparent", hover_color="#444", 
                command=lambda p=item["path"]: load_image(p)
            )
            btn.pack(pady=(15, 5))
            
            raw_name = item["path"].name
            display_name = raw_name if len(raw_name) <= 15 else raw_name[:12] + "..."
            
            lbl = ctk.CTkLabel(card, text=display_name, font=font_txt, text_color="white")
            lbl.pack(pady=(0, 10))

        spacer_row = (len(st["recent_files"]) - 1) // 3 + 1
        spacer = ctk.CTkFrame(gallery_frame, fg_color="transparent", height=80)
        spacer.grid(row=spacer_row, column=0, columnspan=3)

    def open_():
        f = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png *.webp")])
        if f: 
            load_image(f)

    def on_resize(event):
        if st["im"]:
            st["sc"] = min((event.width - 20) / st["im"].width, (event.height - 20) / st["im"].height, 1.0)
            st["tk"] = ImageTk.PhotoImage(st["im"].resize((int(st["im"].width * st["sc"]), int(st["im"].height * st["sc"])), Image.LANCZOS))
            draw()

    def drag(e):
        if not st["im"]: return
        
        cw_canvas = cv.winfo_width()
        ch_canvas = cv.winfo_height()
        img_w, img_h = int(st["im"].width * st["sc"]), int(st["im"].height * st["sc"])
        ox = (cw_canvas - img_w) // 2
        oy = (ch_canvas - img_h) // 2
        
        mouse_x = (e.x - ox) / st["sc"]
        mouse_y = (e.y - oy) / st["sc"]
        
        cw, ch = best_crop_size(st["im"])
        
        st["x"] = min(max(mouse_x - cw / 2, 0), st["im"].width - cw)
        st["y"] = min(max(mouse_y - ch / 2, 0), st["im"].height - ch)
        draw()

    def save():
        if not st["im"]: return
        dst = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            initialfile=st["f"].stem + "_800x650.jpg"
        )
        if dst: 
            do_crop(st["im"], st["x"], st["y"]).save(dst, quality=95)
            st["stats_saved"] += 1
            lbl_stat_saved.configure(text=f"Saved: {st['stats_saved']}")
            st["saved"] = True
            draw()
            save_history()

    # Bindings
    cv.bind("<Configure>", on_resize)
    cv.bind("<B1-Motion>", drag)
    cv.bind("<Button-1>", drag)
    
    btn_open.configure(command=open_)
    btn_save.configure(command=save)
    btn_close_x.configure(command=close_session)
    btn_show_all.configure(command=show_gallery)
    btn_exit_gallery.configure(command=lambda: (gallery_container.pack_forget(), editor_frame.pack(fill="both", expand=True)))

    # Load history on startup
    load_history()

    root.mainloop()

# --- CLI Logic ---
p = argparse.ArgumentParser()
p.add_argument("inputs", nargs="*", type=Path)
p.add_argument("-o", "--output", type=Path, default=Path("cropped"))
p.add_argument("--halign", choices=["left", "center", "right"], default="center")
p.add_argument("--valign", choices=["top", "center", "bottom"], default="center")
a = p.parse_args()

if not a.inputs:
    gui()
else:
    a.output.mkdir(exist_ok=True)
    for f in a.inputs:
        ImageOps.fit(load(f), (OUT_W, OUT_H),
                     centering=(POS[a.halign], POS[a.valign]),
                     method=Image.LANCZOS).save(a.output / f"{f.stem}.jpg", quality=95)
        print(f"{f} -> {a.output / (f.stem + '.jpg')}")