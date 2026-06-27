"""HaS 脱敏工具主界面"""
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

# 将 src 加入路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.desensitizer import HaSDesensitizer
from core.file_handler import FileHandler


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class DesensitizerApp(ctk.CTk):
    """HaS 本地文档脱敏工具"""

    def __init__(self):
        super().__init__()

        self.title("🔒 HaS 本地文档脱敏工具")
        self.geometry("1300x850")
        self.minsize(1100, 700)

        self.desensitizer: HaSDesensitizer | None = None
        self.model_loaded = False
        self.current_file: Path | None = None

        self._build_ui()
        self._try_load_model()

    def _build_ui(self):
        """构建界面"""
        # 顶部工具栏
        self.toolbar = ctk.CTkFrame(self, height=55, fg_color=("gray85", "gray17"))
        self.toolbar.pack(fill="x", padx=12, pady=(12, 0))

        self.title_label = ctk.CTkLabel(
            self.toolbar,
            text="🔒 HaS 本地文档脱敏工具",
            font=("Microsoft YaHei", 16, "bold"),
        )
        self.title_label.pack(side="left", padx=15, pady=8)

        self.model_status = ctk.CTkLabel(
            self.toolbar,
            text="🔄 正在加载模型...",
            font=("Microsoft YaHei", 12),
            text_color="gray",
        )
        self.model_status.pack(side="right", padx=15, pady=8)

        # 主体框架
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=12, pady=12)

        # 左侧面板（输入）
        self.input_frame = ctk.CTkFrame(self.main_frame)
        self.input_frame.pack(side="left", fill="both", expand=True, padx=(0, 6))

        ctk.CTkLabel(
            self.input_frame,
            text="📄 输入文档",
            font=("Microsoft YaHei", 14, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 5))

        self.input_text = ctk.CTkTextbox(
            self.input_frame,
            wrap="word",
            font=("Consolas", 12),
            corner_radius=8,
        )
        self.input_text.pack(fill="both", expand=True, padx=12, pady=5)

        self.input_btn_frame = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        self.input_btn_frame.pack(fill="x", padx=12, pady=(5, 10))

        ctk.CTkButton(
            self.input_btn_frame,
            text="📂 打开文件",
            width=100,
            command=self._load_file,
        ).pack(side="left", padx=3)
        ctk.CTkButton(
            self.input_btn_frame,
            text="📋 粘贴示例",
            width=100,
            command=self._paste_sample,
        ).pack(side="left", padx=3)
        ctk.CTkButton(
            self.input_btn_frame,
            text="🗑️ 清空",
            width=80,
            fg_color=("#c0392b", "#922b21"),
            hover_color=("#a93226", "#7b241c"),
            command=self._clear_input,
        ).pack(side="left", padx=3)

        # 中间控制面板
        self.control_frame = ctk.CTkFrame(self.main_frame, width=220)
        self.control_frame.pack(side="left", fill="y", padx=6)
        self.control_frame.pack_propagate(False)

        ctk.CTkLabel(
            self.control_frame,
            text="⚙️ 脱敏选项",
            font=("Microsoft YaHei", 14, "bold"),
        ).pack(pady=(15, 10))

        # 实体类型选择
        self.entity_vars = {}
        for key, label in HaSDesensitizer.ENTITY_TYPES.items():
            var = ctk.BooleanVar(value=True)
            self.entity_vars[key] = var
            ctk.CTkCheckBox(
                self.control_frame,
                text=label,
                variable=var,
                font=("Microsoft YaHei", 12),
            ).pack(anchor="w", padx=20, pady=4)

        # 全选/反选
        self.select_all_btn = ctk.CTkButton(
            self.control_frame,
            text="☑ 全选",
            width=100,
            height=28,
            command=self._select_all,
        )
        self.select_all_btn.pack(pady=(10, 5))

        # 进度条
        self.progress = ctk.CTkProgressBar(self.control_frame, width=180)
        self.progress.pack(pady=20)
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(
            self.control_frame,
            text="就绪",
            font=("Microsoft YaHei", 11),
            wraplength=180,
        )
        self.status_label.pack(pady=5)

        # 开始脱敏按钮
        self.desensitize_btn = ctk.CTkButton(
            self.control_frame,
            text="🔒 开始脱敏",
            height=45,
            font=("Microsoft YaHei", 15, "bold"),
            command=self._start_desensitize,
        )
        self.desensitize_btn.pack(pady=20)

        # 模型配置按钮
        ctk.CTkButton(
            self.control_frame,
            text="⚙️ 模型配置",
            height=35,
            command=self._show_model_config,
        ).pack(pady=10)

        # 右侧面板（输出）
        self.output_frame = ctk.CTkFrame(self.main_frame)
        self.output_frame.pack(side="left", fill="both", expand=True, padx=(6, 0))

        ctk.CTkLabel(
            self.output_frame,
            text="✅ 脱敏结果",
            font=("Microsoft YaHei", 14, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 5))

        self.output_text = ctk.CTkTextbox(
            self.output_frame,
            wrap="word",
            font=("Consolas", 12),
            corner_radius=8,
        )
        self.output_text.pack(fill="both", expand=True, padx=12, pady=5)

        self.output_btn_frame = ctk.CTkFrame(self.output_frame, fg_color="transparent")
        self.output_btn_frame.pack(fill="x", padx=12, pady=(5, 10))

        ctk.CTkButton(
            self.output_btn_frame,
            text="📋 复制",
            width=80,
            command=self._copy_output,
        ).pack(side="left", padx=3)
        ctk.CTkButton(
            self.output_btn_frame,
            text="💾 导出文件",
            width=100,
            command=self._save_file,
        ).pack(side="left", padx=3)
        ctk.CTkButton(
            self.output_btn_frame,
            text="📊 对比模式",
            width=100,
            command=self._compare_mode,
        ).pack(side="left", padx=3)

    def _try_load_model(self):
        """启动时尝试加载模型"""
        try:
            self.desensitizer = HaSDesensitizer()
            self.model_loaded = True
            self.model_status.configure(
                text="✅ 模型已加载 (HaS 0.6B)",
                text_color="green",
            )
        except FileNotFoundError as e:
            self.model_status.configure(
                text=f"❌ 模型未找到: {e}",
                text_color="red",
            )
            self.desensitize_btn.configure(state="disabled")
        except Exception as e:
            self.model_status.configure(
                text=f"❌ 模型加载失败: {e}",
                text_color="red",
            )
            self.desensitize_btn.configure(state="disabled")

    def _start_desensitize(self):
        """执行脱敏"""
        if not self.model_loaded or self.desensitizer is None:
            messagebox.showwarning("提示", "模型未加载，请先配置模型")
            return

        text = self.input_text.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("提示", "请输入待脱敏内容")
            return

        selected_types = [k for k, v in self.entity_vars.items() if v.get()]
        if not selected_types:
            messagebox.showwarning("提示", "请至少选择一种实体类型")
            return

        self.desensitize_btn.configure(state="disabled")
        self.progress.set(0.1)
        self.status_label.configure(text="正在脱敏...")
        self.update()

        try:
            result = self.desensitizer.desensitize(
                text,
                entity_types=selected_types,
                progress_callback=self._update_progress,
            )
            self.output_text.delete("1.0", "end")
            self.output_text.insert("1.0", result)
            self.status_label.configure(
                text=f"完成 | 脱敏实体: {len(selected_types)} 类"
            )
        except Exception as e:
            messagebox.showerror("脱敏失败", str(e))
            self.status_label.configure(text=f"失败: {e}")
        finally:
            self.desensitize_btn.configure(state="normal")
            self.progress.set(1.0)

    def _update_progress(self, msg: str, pct: int):
        self.status_label.configure(text=msg)
        self.progress.set(pct / 100)
        self.update()

    def _load_file(self):
        """打开文件"""
        path = filedialog.askopenfilename(
            title="选择待脱敏文件",
            filetypes=[
                ("文本文件", "*.txt *.md *.csv *.json *.xml"),
                ("代码文件", "*.py *.js *.java *.c *.cpp *.go *.rs *.ts *.html *.css *.sql"),
                ("Word 文档", "*.docx"),
                ("日志文件", "*.log"),
                ("所有文件", "*.*"),
            ],
        )
        if path:
            try:
                content = FileHandler.read(path)
                self.input_text.delete("1.0", "end")
                self.input_text.insert("1.0", content)
                self.current_file = Path(path)
                self.status_label.configure(text=f"已加载: {Path(path).name}")
            except Exception as e:
                messagebox.showerror("读取失败", str(e))

    def _save_file(self):
        """保存结果"""
        content = self.output_text.get("1.0", "end").strip()
        if not content:
            messagebox.showwarning("提示", "没有可导出的内容")
            return

        if self.current_file:
            default_name = FileHandler.suggest_output_path(self.current_file).name
        else:
            default_name = "desensitized_output.txt"

        path = filedialog.asksaveasfilename(
            title="保存脱敏结果",
            defaultextension=".txt",
            initialfile=default_name,
            filetypes=[
                ("文本文件", "*.txt"),
                ("Markdown", "*.md"),
                ("Word 文档", "*.docx"),
                ("所有文件", "*.*"),
            ],
        )
        if path:
            try:
                FileHandler.write(path, content)
                self.status_label.configure(text=f"已保存: {Path(path).name}")
            except Exception as e:
                messagebox.showerror("保存失败", str(e))

    def _copy_output(self):
        """复制结果到剪贴板"""
        content = self.output_text.get("1.0", "end").strip()
        if content:
            try:
                import pyperclip
                pyperclip.copy(content)
                self.status_label.configure(text="✅ 已复制到剪贴板")
            except ImportError:
                self.clipboard_clear()
                self.clipboard_append(content)
                self.status_label.configure(text="✅ 已复制到剪贴板")
        else:
            messagebox.showwarning("提示", "没有可复制的内容")

    def _paste_sample(self):
        """粘贴示例文本"""
        sample = """甲方：张三，身份证号：110101199001011234，联系电话：13800138000，
电子邮箱：zhangsan@example.com，任职于北京神州数码科技有限公司，
住址：北京市海淀区中关村大街100号。本次合同金额为人民币伍拾万元整（¥500,000.00）。
乙方：李四，电话：13912345678，公司地址：上海市浦东新区陆家嘴环路1000号。"""
        self.input_text.delete("1.0", "end")
        self.input_text.insert("1.0", sample)
        self.status_label.configure(text="已加载示例文本")

    def _clear_input(self):
        """清空输入"""
        self.input_text.delete("1.0", "end")
        self.output_text.delete("1.0", "end")
        self.current_file = None
        self.status_label.configure(text="已清空")
        self.progress.set(0)

    def _select_all(self):
        """全选/反选实体类型"""
        all_selected = all(v.get() for v in self.entity_vars.values())
        for var in self.entity_vars.values():
            var.set(not all_selected)
        self.select_all_btn.configure(
            text="☐ 全不选" if not all_selected else "☑ 全选"
        )

    def _compare_mode(self):
        """对比模式 - 显示原文和脱敏结果并排"""
        input_text = self.input_text.get("1.0", "end").strip()
        output_text = self.output_text.get("1.0", "end").strip()

        if not input_text or not output_text:
            messagebox.showwarning("提示", "需要同时有输入和输出内容")
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("📊 对比模式")
        dialog.geometry("1200x700")

        ctk.CTkLabel(dialog, text="原文", font=("Microsoft YaHei", 14, "bold")).pack(
            side="left", padx=10, pady=5
        )
        left = ctk.CTkTextbox(dialog, wrap="word", font=("Consolas", 11))
        left.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        left.insert("1.0", input_text)
        left.configure(state="disabled")

        ctk.CTkLabel(dialog, text="脱敏结果", font=("Microsoft YaHei", 14, "bold")).pack(
            side="left", padx=10, pady=5
        )
        right = ctk.CTkTextbox(dialog, wrap="word", font=("Consolas", 11))
        right.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        right.insert("1.0", output_text)
        right.configure(state="disabled")

    def _show_model_config(self):
        """显示模型配置对话框"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("⚙️ 模型配置")
        dialog.geometry("500x300")

        ctk.CTkLabel(
            dialog,
            text="模型配置",
            font=("Microsoft YaHei", 16, "bold"),
        ).pack(pady=15)

        info = f"""当前模型: HaS_Text_0209_0.6B_Q8
模型路径: {self.desensitizer.model_path if self.desensitizer else '未加载'}
上下文长度: 8192 tokens
量化格式: Q8_0

模型特性:
- 本地推理，数据不出设备
- 支持 10 种敏感实体类型识别
- 语义化标签替换（非简单遮蔽）
- 可逆还原（需保留映射关系）
"""
        ctk.CTkLabel(dialog, text=info, font=("Consolas", 11), justify="left").pack(
            padx=20, pady=10
        )

        ctk.CTkButton(dialog, text="关闭", command=dialog.destroy).pack(pady=15)


def main():
    app = DesensitizerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
