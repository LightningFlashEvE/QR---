import os
import io
import sys
import ctypes
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import tkinter.font as tkfont
from typing import Optional, Union

from PIL import Image, ImageTk
import qrcode
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H
from qrcode.image.svg import SvgImage


ERROR_CORRECTION_MAP = {
	"L (7%)": ERROR_CORRECT_L,
	"M (15%)": ERROR_CORRECT_M,
	"Q (25%)": ERROR_CORRECT_Q,
	"H (30%)": ERROR_CORRECT_H,
}


def enable_windows_hi_dpi() -> None:
	if os.name != "nt":
		return
	try:
		# Windows 8.1+ Per-Monitor DPI Aware
		ctypes.windll.shcore.SetProcessDpiAwareness(2)
	except Exception:
		try:
			# Legacy system DPI aware
			ctypes.windll.user32.SetProcessDPIAware()
		except Exception:
			pass


class QRCodeApp(tk.Tk):
	def __init__(self) -> None:
		super().__init__()
		self.title("二维码生成器（可控参数）")
		self.geometry("1200x700")
		self.minsize(1100, 680)

		self._configure_scaling()
		self._configure_fonts()

		self.input_text_var = tk.StringVar()
		self.version_var = tk.StringVar(value="自动")
		self.error_correction_var = tk.StringVar(value="M (15%)")
		self.box_size_var = tk.IntVar(value=10)
		self.border_var = tk.IntVar(value=4)
		self.fill_color_var = tk.StringVar(value="#000000")
		self.back_color_var = tk.StringVar(value="#FFFFFF")
		self.format_var = tk.StringVar(value="PNG")
		self.logo_path_var = tk.StringVar(value="")
		self.logo_scale_percent_var = tk.IntVar(value=20)

		self.preview_image_tk: Optional[ImageTk.PhotoImage] = None
		self._update_timer: Optional[str] = None

		self._build_ui()

	def _build_ui(self) -> None:
		container = ttk.Frame(self)
		container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

		left_frame = ttk.Frame(container)
		left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

		right_frame = ttk.Frame(container, width=400)
		right_frame.pack(side=tk.RIGHT, fill=tk.Y)

		self._build_left(left_frame)
		self._build_right(right_frame)

	def _configure_scaling(self) -> None:
		if os.name != "nt":
			return
		try:
			# 强制设置更高的缩放比例
			self.tk.call("tk", "scaling", 2.0)
		except Exception:
			pass

	def _configure_fonts(self) -> None:
		# 使用更清晰的 Windows 字体并增加字号
		try:
			for name in (
				"TkDefaultFont",
				"TkTextFont",
				"TkMenuFont",
				"TkHeadingFont",
				"TkCaptionFont",
				"TkSmallCaptionFont",
				"TkTooltipFont",
			):
				font_obj = tkfont.nametofont(name)
				font_obj.configure(family="Microsoft YaHei", size=11)
		except Exception:
			pass

	def _build_left(self, parent: ttk.Frame) -> None:
		# 输入内容
		input_label = ttk.Label(parent, text="内容（文本/URL/JSON等）：")
		input_label.pack(anchor=tk.W)
		self.input_text = tk.Text(parent, height=10, wrap=tk.WORD)
		self.input_text.pack(fill=tk.BOTH, expand=True)

		# 操作按钮行 - 横向并排排列
		btn_row = ttk.Frame(parent)
		btn_row.pack(fill=tk.X, pady=(8, 0))

		load_btn = ttk.Button(btn_row, text="从文件载入…", command=self._on_load_from_file)
		load_btn.pack(side=tk.LEFT)

		clear_btn = ttk.Button(btn_row, text="清空", command=self._on_clear_input)
		clear_btn.pack(side=tk.LEFT, padx=(8, 0))

		self.gen_btn = ttk.Button(btn_row, text="生成预览", command=self._on_generate_preview)
		self.gen_btn.pack(side=tk.LEFT, padx=(8, 0))

		self.save_btn = ttk.Button(btn_row, text="保存…", command=self._on_save)
		self.save_btn.pack(side=tk.LEFT, padx=(8, 0))

		# 预览与导出
		preview_group = ttk.LabelFrame(parent, text="预览")
		preview_group.pack(fill=tk.BOTH, expand=True, pady=10)

		preview_inner = ttk.Frame(preview_group)
		preview_inner.pack(fill=tk.BOTH, expand=True)

		self.preview_label = ttk.Label(preview_inner, text="生成后显示预览", anchor=tk.CENTER)
		self.preview_label.pack(fill=tk.BOTH, expand=True, ipadx=20, ipady=20)

	def _build_right(self, parent: ttk.Frame) -> None:
		# 参数设置
		param_group = ttk.LabelFrame(parent, text="参数")
		param_group.pack(fill=tk.BOTH, expand=True)

		# 版本
		row_ver = ttk.Frame(param_group)
		row_ver.pack(fill=tk.X, padx=8, pady=6)
		label_ver = ttk.Label(row_ver, text="版本（1-40）")
		label_ver.pack(side=tk.LEFT)
		version_values = ["自动"] + [str(i) for i in range(1, 41)]
		combo_ver = ttk.Combobox(row_ver, textvariable=self.version_var, values=version_values, width=8, state="readonly")
		combo_ver.pack(side=tk.RIGHT)
		combo_ver.bind("<<ComboboxSelected>>", lambda e: self._on_param_change())

		# 纠错等级
		row_ec = ttk.Frame(param_group)
		row_ec.pack(fill=tk.X, padx=8, pady=6)
		label_ec = ttk.Label(row_ec, text="纠错等级")
		label_ec.pack(side=tk.LEFT)
		combo_ec = ttk.Combobox(row_ec, textvariable=self.error_correction_var, values=list(ERROR_CORRECTION_MAP.keys()), width=10, state="readonly")
		combo_ec.pack(side=tk.RIGHT)
		combo_ec.bind("<<ComboboxSelected>>", lambda e: self._on_param_change())

		# 像素大小
		row_bs = ttk.Frame(param_group)
		row_bs.pack(fill=tk.X, padx=8, pady=6)
		label_bs = ttk.Label(row_bs, text="像素大小（box_size）")
		label_bs.pack(side=tk.LEFT)
		spin_bs = tk.Spinbox(row_bs, from_=1, to=50, textvariable=self.box_size_var, width=6)
		spin_bs.pack(side=tk.RIGHT)
		spin_bs.bind("<KeyRelease>", lambda e: self._on_param_change())
		spin_bs.bind("<ButtonRelease-1>", lambda e: self._on_param_change())

		# 边框
		row_bd = ttk.Frame(param_group)
		row_bd.pack(fill=tk.X, padx=8, pady=6)
		label_bd = ttk.Label(row_bd, text="边框（border）")
		label_bd.pack(side=tk.LEFT)
		spin_bd = tk.Spinbox(row_bd, from_=0, to=10, textvariable=self.border_var, width=6)
		spin_bd.pack(side=tk.RIGHT)
		spin_bd.bind("<KeyRelease>", lambda e: self._on_param_change())
		spin_bd.bind("<ButtonRelease-1>", lambda e: self._on_param_change())

		# 前景色
		row_fc = ttk.Frame(param_group)
		row_fc.pack(fill=tk.X, padx=8, pady=6)
		label_fc = ttk.Label(row_fc, text="前景色")
		label_fc.pack(side=tk.LEFT)
		btn_fc = ttk.Button(row_fc, textvariable=self.fill_color_var, command=self._on_pick_fill_color)
		btn_fc.pack(side=tk.RIGHT)

		# 背景色
		row_bc = ttk.Frame(param_group)
		row_bc.pack(fill=tk.X, padx=8, pady=6)
		label_bc = ttk.Label(row_bc, text="背景色")
		label_bc.pack(side=tk.LEFT)
		btn_bc = ttk.Button(row_bc, textvariable=self.back_color_var, command=self._on_pick_back_color)
		btn_bc.pack(side=tk.RIGHT)

		# 输出格式
		row_fmt = ttk.Frame(param_group)
		row_fmt.pack(fill=tk.X, padx=8, pady=6)
		label_fmt = ttk.Label(row_fmt, text="输出格式")
		label_fmt.pack(side=tk.LEFT)
		combo_fmt = ttk.Combobox(row_fmt, textvariable=self.format_var, values=["PNG", "SVG"], width=8, state="readonly")
		combo_fmt.pack(side=tk.RIGHT)
		combo_fmt.bind("<<ComboboxSelected>>", lambda e: self._on_format_change())

		# Logo 嵌入
		logo_group = ttk.LabelFrame(parent, text="Logo（仅PNG支持嵌入）")
		logo_group.pack(fill=tk.X, expand=False, pady=(6, 0))

		row_logo_path = ttk.Frame(logo_group)
		row_logo_path.pack(fill=tk.X, padx=8, pady=6)
		entry_logo = ttk.Entry(row_logo_path, textvariable=self.logo_path_var)
		entry_logo.pack(side=tk.LEFT, fill=tk.X, expand=True)
		btn_pick_logo = ttk.Button(row_logo_path, text="选择…", command=self._on_pick_logo)
		btn_pick_logo.pack(side=tk.LEFT, padx=(6, 0))
		btn_clear_logo = ttk.Button(row_logo_path, text="清除", command=self._on_clear_logo)
		btn_clear_logo.pack(side=tk.LEFT, padx=(6, 0))

		row_logo_scale = ttk.Frame(logo_group)
		row_logo_scale.pack(fill=tk.X, padx=8, pady=(0, 8))
		label_logo = ttk.Label(row_logo_scale, text="Logo占二维码宽度%")
		label_logo.pack(side=tk.LEFT)
		spin_logo = tk.Spinbox(row_logo_scale, from_=5, to=40, textvariable=self.logo_scale_percent_var, width=6)
		spin_logo.pack(side=tk.RIGHT)
		spin_logo.bind("<KeyRelease>", lambda e: self._on_param_change())
		spin_logo.bind("<ButtonRelease-1>", lambda e: self._on_param_change())

		self._on_format_change()

	def _on_format_change(self) -> None:
		fmt = self.format_var.get().upper()
		if fmt == "SVG" and self.logo_path_var.get():
			messagebox.showinfo("提示", "SVG 不支持嵌入位图 Logo，已清除 Logo 设置。")
			self.logo_path_var.set("")

	def _on_pick_fill_color(self) -> None:
		color = colorchooser.askcolor(initialcolor=self.fill_color_var.get(), title="选择前景色")
		if color and color[1]:
			self.fill_color_var.set(color[1])
			self._on_param_change()

	def _on_pick_back_color(self) -> None:
		color = colorchooser.askcolor(initialcolor=self.back_color_var.get(), title="选择背景色")
		if color and color[1]:
			self.back_color_var.set(color[1])
			self._on_param_change()

	def _on_pick_logo(self) -> None:
		path = filedialog.askopenfilename(title="选择Logo图片", filetypes=[
			("图像文件", ".png .jpg .jpeg .bmp .gif"),
			("所有文件", "*.*"),
		])
		if path:
			self.logo_path_var.set(path)
			if self.format_var.get().upper() == "SVG":
				messagebox.showwarning("提示", "当前格式为SVG，不支持嵌入位图Logo。将使用PNG进行预览与导出建议。")
			self._on_param_change()

	def _on_clear_logo(self) -> None:
		self.logo_path_var.set("")
		self._on_param_change()

	def _on_param_change(self) -> None:
		"""参数变化时触发预览更新（带防抖）"""
		# 取消之前的定时器
		if self._update_timer:
			self.after_cancel(self._update_timer)
		
		# 设置新的定时器，500ms后更新预览
		self._update_timer = self.after(500, self._auto_update_preview)

	def _auto_update_preview(self) -> None:
		"""自动更新预览"""
		try:
			# 检查是否有内容
			content = self.input_text.get("1.0", tk.END).strip()
			if not content:
				return
			
			# 更新预览
			self._on_generate_preview()
		except Exception:
			# 静默处理错误，避免影响用户体验
			pass

	def _on_load_from_file(self) -> None:
		path = filedialog.askopenfilename(title="选择文本文件", filetypes=[
			("文本", ".txt .md .csv .json .xml .yml .yaml"),
			("所有文件", "*.*"),
		])
		if not path:
			return
		try:
			with open(path, "r", encoding="utf-8") as f:
				data = f.read()
			self.input_text.delete("1.0", tk.END)
			self.input_text.insert("1.0", data)
		except Exception as exc:
			messagebox.showerror("读取失败", str(exc))



	def _on_clear_input(self) -> None:
		self.input_text.delete("1.0", tk.END)

	def _get_qr(self, for_preview: bool = False) -> Union[Image.Image, bytes]:
		content = self.input_text.get("1.0", tk.END).strip()
		if not content:
			raise ValueError("请输入内容")

		version_value: Optional[int]
		if self.version_var.get() == "自动":
			version_value = None
			fit_value = True
		else:
			version_value = int(self.version_var.get())
			fit_value = False

		error_correction_value = ERROR_CORRECTION_MAP[self.error_correction_var.get()]
		box_size_value = max(1, int(self.box_size_var.get()))
		border_value = max(0, int(self.border_var.get()))

		qr = qrcode.QRCode(
			version=version_value,
			error_correction=error_correction_value,
			box_size=box_size_value,
			border=border_value,
		)
		qr.add_data(content)
		qr.make(fit=fit_value)

		fmt = self.format_var.get().upper()
		fill_color = self.fill_color_var.get()
		back_color = self.back_color_var.get()

		if fmt == "SVG" and not for_preview:
			# 返回SVG字节
			img = qr.make_image(image_factory=SvgImage, fill_color=fill_color, back_color=back_color)
			with io.BytesIO() as buf:
				img.save(buf)
				return buf.getvalue()

		# PNG / 预览
		img = qr.make_image(fill_color=fill_color, back_color=back_color).convert("RGBA")

		logo_path = self.logo_path_var.get()
		if logo_path and os.path.isfile(logo_path):
			try:
				img = self._embed_logo(img, logo_path)
			except Exception as exc:
				if not for_preview:
					raise
				# 预览出错则忽略logo

		return img

	def _embed_logo(self, qr_image: Image.Image, logo_path: str) -> Image.Image:
		qr_w, qr_h = qr_image.size
		logo = Image.open(logo_path).convert("RGBA")
		max_side = min(qr_w, qr_h)
		scale = max(5, min(40, int(self.logo_scale_percent_var.get()))) / 100.0
		target_w = int(max_side * scale)
		# 保持比例缩放
		ratio = min(target_w / logo.width, target_w / logo.height)
		logo = logo.resize((max(1, int(logo.width * ratio)), max(1, int(logo.height * ratio))), Image.LANCZOS)

		x = (qr_w - logo.width) // 2
		y = (qr_h - logo.height) // 2
		composited = qr_image.copy()
		composited.alpha_composite(logo, (x, y))
		return composited

	def _on_generate_preview(self) -> None:
		try:
			img_or_bytes = self._get_qr(for_preview=True)
			if isinstance(img_or_bytes, bytes):
				# SVG 预览：转为位图以预览（简单起见，这里直接提示而不渲染SVG）
				self.preview_label.configure(text="SVG 已生成，预览以PNG参数显示。请保存到文件查看SVG。")
				self.preview_label.image = None
				return
			img: Image.Image = img_or_bytes
			preview = self._make_preview_image(img)
			self.preview_image_tk = ImageTk.PhotoImage(preview)
			self.preview_label.configure(image=self.preview_image_tk, text="")
			self.preview_label.image = self.preview_image_tk
		except Exception as exc:
			messagebox.showerror("生成失败", str(exc))

	def _make_preview_image(self, img: Image.Image) -> Image.Image:
		# 预览区目标大小
		max_w, max_h = 400, 400
		w, h = img.size
		ratio = min(max_w / w, max_h / h, 1.0)
		new_size = (max(1, int(w * ratio)), max(1, int(h * ratio)))
		return img.resize(new_size, Image.LANCZOS)

	def _on_save(self) -> None:
		fmt = self.format_var.get().upper()
		if fmt == "PNG":
			path = filedialog.asksaveasfilename(
				title="另存为PNG",
				defaultextension=".png",
				filetypes=[("PNG 图片", ".png"), ("所有文件", "*.*")],
			)
			if not path:
				return
			try:
				img = self._get_qr(for_preview=False)
				if isinstance(img, Image.Image):
					img.save(path, format="PNG")
				else:
					raise ValueError("PNG 导出异常")
				messagebox.showinfo("成功", f"已保存：\n{path}")
			except Exception as exc:
				messagebox.showerror("保存失败", str(exc))
			return

		# SVG
		path = filedialog.asksaveasfilename(
			title="另存为SVG",
			defaultextension=".svg",
			filetypes=[("SVG 矢量图", ".svg"), ("所有文件", "*.*")],
		)
		if not path:
			return
		try:
			data = self._get_qr(for_preview=False)
			if isinstance(data, bytes):
				with open(path, "wb") as f:
					f.write(data)
			else:
				raise ValueError("SVG 导出异常")
			messagebox.showinfo("成功", f"已保存：\n{path}")
		except Exception as exc:
			messagebox.showerror("保存失败", str(exc))


def main() -> None:
	app = QRCodeApp()
	app.mainloop()


if __name__ == "__main__":
	main()


