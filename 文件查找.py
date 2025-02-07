import os
from pathlib import Path
import humanize
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from threading import Thread
import sys
import subprocess

class LargeFileFinder(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("大文件查找器")
        self.geometry("800x600")
        
        # 创建主框架
        self.main_frame = ttk.Frame(self, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 目录选择部分
        self.dir_frame = ttk.Frame(self.main_frame)
        self.dir_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        self.dir_label = ttk.Label(self.dir_frame, text="目录路径:")
        self.dir_label.grid(row=0, column=0, padx=5)
        
        self.dir_var = tk.StringVar()
        self.dir_entry = ttk.Entry(self.dir_frame, textvariable=self.dir_var, width=50)
        self.dir_entry.grid(row=0, column=1, padx=5)
        
        self.browse_btn = ttk.Button(self.dir_frame, text="浏览", command=self.browse_directory)
        self.browse_btn.grid(row=0, column=2, padx=5)
        
        # 文件大小限制部分
        self.size_frame = ttk.Frame(self.main_frame)
        self.size_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        self.size_label = ttk.Label(self.size_frame, text="大小限制(MB):")
        self.size_label.grid(row=0, column=0, padx=5)
        
        self.size_var = tk.StringVar(value="100")
        self.size_entry = ttk.Entry(self.size_frame, textvariable=self.size_var, width=10)
        self.size_entry.grid(row=0, column=1, padx=5)
        
        # 搜索按钮
        self.search_btn = ttk.Button(self.main_frame, text="开始搜索", command=self.start_search)
        self.search_btn.grid(row=2, column=0, columnspan=3, pady=10)
        
        # 进度条
        self.progress_var = tk.StringVar(value="准备就绪")
        self.progress_label = ttk.Label(self.main_frame, textvariable=self.progress_var)
        self.progress_label.grid(row=3, column=0, columnspan=3, pady=5)
        
        # 结果显示区域
        self.result_frame = ttk.Frame(self.main_frame)
        self.result_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # 创建树形视图
        self.tree = ttk.Treeview(self.result_frame, columns=("size", "path"), show="headings")
        self.tree.heading("size", text="文件大小")
        self.tree.heading("path", text="文件路径")
        self.tree.column("size", width=100)
        self.tree.column("path", width=680)
        
        # 添加滚动条
        self.scrollbar = ttk.Scrollbar(self.result_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 配置网格权重
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(4, weight=1)
        self.result_frame.grid_columnconfigure(0, weight=1)
        self.result_frame.grid_rowconfigure(0, weight=1)
        
        # 在按钮框架中添加批量选择功能
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.grid(row=5, column=0, columnspan=3, pady=5)
        
        # 添加全选/取消全选按钮
        self.select_all_btn = ttk.Button(
            self.button_frame,
            text="全选",
            command=self.toggle_select_all
        )
        self.select_all_btn.pack(side=tk.LEFT, padx=5)
        
        # 添加按大小选择的框架
        self.size_select_frame = ttk.LabelFrame(self.button_frame, text="按大小选择")
        self.size_select_frame.pack(side=tk.LEFT, padx=5)
        
        self.size_from_var = tk.StringVar()
        self.size_to_var = tk.StringVar()
        
        ttk.Label(self.size_select_frame, text="从").pack(side=tk.LEFT, padx=2)
        self.size_from_entry = ttk.Entry(self.size_select_frame, textvariable=self.size_from_var, width=8)
        self.size_from_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(self.size_select_frame, text="到").pack(side=tk.LEFT, padx=2)
        self.size_to_entry = ttk.Entry(self.size_select_frame, textvariable=self.size_to_var, width=8)
        self.size_to_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(self.size_select_frame, text="MB").pack(side=tk.LEFT, padx=2)
        
        self.apply_size_filter_btn = ttk.Button(
            self.size_select_frame,
            text="应用",
            command=self.select_by_size_range
        )
        self.apply_size_filter_btn.pack(side=tk.LEFT, padx=5)
        
        # 创建删除按钮和选择计数（修复：先创建这些组件）
        self.selection_var = tk.StringVar(value="已选择: 0 个文件")
        self.selection_label = ttk.Label(self.button_frame, textvariable=self.selection_var)
        
        self.delete_btn = ttk.Button(
            self.button_frame, 
            text="删除选中文件", 
            command=self.delete_selected_files,
            state='disabled'
        )
        
        # 添加打开文件夹按钮（放在删除按钮之前）
        self.open_folder_btn = ttk.Button(
            self.button_frame,
            text="打开所在文件夹",
            command=self.open_selected_folder,
            state='disabled'  # 初始状态为禁用
        )
        self.open_folder_btn.pack(side=tk.LEFT, padx=5)
        
        # 然后再进行布局
        self.delete_btn.pack(side=tk.LEFT, padx=20)
        self.selection_label.pack(side=tk.LEFT, padx=5)
        
        # 添加是否选择状态标记
        self.all_selected = False
        
        # 绑定选择事件
        self.tree.bind('<<TreeviewSelect>>', self.on_select)

    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.dir_var.set(directory)

    def find_large_files(self, directory, size_limit_mb=100):
        size_limit = size_limit_mb * 1024 * 1024
        large_files = []
        
        total_files = sum([len(files) for _, _, files in os.walk(directory)])
        processed_files = 0
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                processed_files += 1
                self.progress_var.set(f"正在搜索... ({processed_files}/{total_files})")
                
                file_path = os.path.join(root, file)
                try:
                    file_size = os.path.getsize(file_path)
                    if file_size > size_limit:
                        large_files.append({
                            'path': file_path,
                            'size': file_size
                        })
                except OSError:
                    continue
        
        large_files.sort(key=lambda x: x['size'], reverse=True)
        return large_files

    def start_search(self):
        # 清空现有结果
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        directory = self.dir_var.get()
        try:
            size_limit = float(self.size_var.get())
        except ValueError:
            messagebox.showerror("错误", "请输入有效的文件大小限制")
            return
            
        if not os.path.exists(directory):
            messagebox.showerror("错误", "目录不存在")
            return
            
        self.search_btn.configure(state='disabled')
        
        # 在新线程中执行搜索
        def search_thread():
            large_files = self.find_large_files(directory, size_limit)
            
            # 更新界面必须在主线程中进行
            self.after(0, lambda: self.update_results(large_files))
            
        Thread(target=search_thread).start()

    def update_results(self, large_files):
        for file in large_files:
            size_human = humanize.naturalsize(file['size'])
            self.tree.insert('', 'end', values=(size_human, file['path']))
            
        self.progress_var.set(f"搜索完成，共找到 {len(large_files)} 个文件")
        self.search_btn.configure(state='normal')
        
        # 重置选择计数
        self.selection_var.set("已选择: 0 个文件")
        self.delete_btn.configure(state='disabled')
        
        # 重置选择状态
        self.all_selected = False
        self.select_all_btn.configure(text="全选")
        self.size_from_var.set("")
        self.size_to_var.set("")
        
        # 重置按钮状态
        self.open_folder_btn.configure(state='disabled')

    def on_select(self, event):
        """当选择改变时更新按钮状态和选择计数"""
        selected = len(self.tree.selection())
        self.selection_var.set(f"已选择: {selected} 个文件")
        # 更新两个按钮的状态
        state = 'normal' if selected > 0 else 'disabled'
        self.delete_btn.configure(state=state)
        self.open_folder_btn.configure(state=state)

    def delete_selected_files(self):
        """删除选中的文件"""
        selected_items = self.tree.selection()
        if not selected_items:
            return
            
        # 确认删除
        count = len(selected_items)
        if not messagebox.askyesno("确认删除", 
            f"确定要删除选中的 {count} 个文件吗？\n此操作不可撤销！"):
            return
            
        deleted_count = 0
        failed_files = []
        
        for item in selected_items:
            values = self.tree.item(item)['values']
            file_path = values[1]  # 文件路径在第二列
            
            try:
                os.remove(file_path)
                self.tree.delete(item)
                deleted_count += 1
            except OSError as e:
                failed_files.append(f"{file_path}: {str(e)}")
                
        # 显示删除结果
        if failed_files:
            error_message = "\n".join(failed_files)
            messagebox.showerror("删除失败", 
                f"成功删除 {deleted_count} 个文件\n"
                f"失败 {len(failed_files)} 个文件:\n{error_message}")
        else:
            messagebox.showinfo("删除成功", 
                f"成功删除 {deleted_count} 个文件")
            
        # 更新选择计数
        self.selection_var.set("已选择: 0 个文件")
        self.delete_btn.configure(state='disabled')

    def toggle_select_all(self):
        """切换全选/取消全选状态"""
        if self.all_selected:
            self.tree.selection_remove(*self.tree.selection())
            self.select_all_btn.configure(text="全选")
        else:
            self.tree.selection_set(*self.tree.get_children())
            self.select_all_btn.configure(text="取消全选")
        
        self.all_selected = not self.all_selected
        self.on_select(None)

    def select_by_size_range(self):
        """按文件大小范围选择"""
        try:
            size_from = float(self.size_from_var.get() or 0)
            size_to = float(self.size_to_var.get() or float('inf'))
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字范围")
            return
            
        # 转换为字节
        size_from *= 1024 * 1024  # MB to bytes
        size_to *= 1024 * 1024    # MB to bytes
        
        # 清除现有选择
        self.tree.selection_remove(*self.tree.selection())
        
        # 选择在范围内的文件
        for item in self.tree.get_children():
            size_str = self.tree.item(item)['values'][0]
            # 将人类可读的大小转换回字节
            size_bytes = self.parse_size(size_str)
            
            if size_from <= size_bytes <= size_to:
                self.tree.selection_add(item)
        
        self.on_select(None)

    def parse_size(self, size_str):
        """将人类可读的大小字符串转换为字节数"""
        units = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
        number = float(''.join(filter(lambda x: x.isdigit() or x == '.', size_str)))
        unit = ''.join(filter(lambda x: x.isalpha(), size_str)).upper()
        return int(number * units[unit])

    def open_selected_folder(self):
        """打开选中文件所在的文件夹"""
        selected_items = self.tree.selection()
        if not selected_items:
            return
            
        # 获取第一个选中项的路径
        file_path = self.tree.item(selected_items[0])['values'][1]
        folder_path = os.path.dirname(file_path)
        
        try:
            # Windows
            if os.name == 'nt':
                os.startfile(folder_path)
            # macOS
            elif os.name == 'posix' and sys.platform == 'darwin':
                subprocess.Popen(['open', folder_path])
            # Linux
            elif os.name == 'posix':
                subprocess.Popen(['xdg-open', folder_path])
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件夹：{str(e)}")

def main():
    app = LargeFileFinder()
    app.mainloop()

if __name__ == "__main__":
    main()
