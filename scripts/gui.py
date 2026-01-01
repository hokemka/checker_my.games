import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import time
import os
from .checker import AccountChecker

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("MY.GAMES Account Checker")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        self.input_file = tk.StringVar()
        self.delay = tk.DoubleVar(value=1.0)
        self.debug_mode = tk.BooleanVar(value=False)
        self.save_logs = tk.BooleanVar(value=False)
        self.checker = None
        self.check_thread = None
        
        self.create_interface()
    
    def create_interface(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        title_label = ttk.Label(main_frame, text="MY.GAMES Account Checker", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        ttk.Label(main_frame, text="Файл с аккаунтами:").grid(row=1, column=0, sticky=tk.W, pady=5)
        file_entry = ttk.Entry(main_frame, textvariable=self.input_file, width=50)
        file_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        browse_btn = ttk.Button(main_frame, text="Обзор...", command=self.select_file)
        browse_btn.grid(row=1, column=2, pady=5)
        
        ttk.Label(main_frame, text="Задержка (сек):").grid(row=2, column=0, sticky=tk.W, pady=5)
        delay_spinbox = ttk.Spinbox(main_frame, from_=0.1, to=10.0, increment=0.1, 
                                    textvariable=self.delay, width=10)
        delay_spinbox.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        debug_check = ttk.Checkbutton(main_frame, text="Подробные логи (для отладки)", 
                                      variable=self.debug_mode)
        debug_check.grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        save_logs_check = ttk.Checkbutton(main_frame, text="Сохранять логи в файл", 
                                          variable=self.save_logs)
        save_logs_check.grid(row=4, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=20)
        
        self.start_btn = ttk.Button(button_frame, text="Начать проверку", 
                                    command=self.start_check, state=tk.NORMAL)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="Остановить", 
                                   command=self.stop_check, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.progress_var = tk.StringVar(value="Готов к работе")
        progress_label = ttk.Label(main_frame, textvariable=self.progress_var)
        progress_label.grid(row=6, column=0, columnspan=3, pady=5)
        
        self.progress_bar = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress_bar.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(main_frame, text="Лог проверки:").grid(row=8, column=0, sticky=tk.W, pady=(10, 5))
        
        log_frame = ttk.Frame(main_frame)
        log_frame.grid(row=9, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(9, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        result_frame = ttk.Frame(main_frame)
        result_frame.grid(row=10, column=0, columnspan=3, pady=10)
        
        self.open_valid_btn = ttk.Button(result_frame, text="Открыть валидные", 
                                        command=self.open_valid_file, state=tk.DISABLED)
        self.open_valid_btn.pack(side=tk.LEFT, padx=5)
        
        self.open_invalid_btn = ttk.Button(result_frame, text="Открыть невалидные", 
                                          command=self.open_invalid_file, state=tk.DISABLED)
        self.open_invalid_btn.pack(side=tk.LEFT, padx=5)
        
        self.valid_file_path = None
        self.invalid_file_path = None
    
    def select_file(self):
        filename = filedialog.askopenfilename(
            title="Выберите файл с аккаунтами",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            self.input_file.set(filename)
            self.add_log_message(f"Выбран файл: {filename}")
    
    def add_log_message(self, message, status="info"):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        
        if status == "success":
            self.log_text.tag_add("success", "end-2c", "end-1c")
            self.log_text.tag_config("success", foreground="green")
        elif status == "error":
            self.log_text.tag_add("error", "end-2c", "end-1c")
            self.log_text.tag_config("error", foreground="red")
        elif status == "warning":
            self.log_text.tag_add("warning", "end-2c", "end-1c")
            self.log_text.tag_config("warning", foreground="orange")
    
    def update_status(self, message, status="info"):
        self.root.after(0, self.add_log_message, message, status)
        self.root.after(0, lambda: self.progress_var.set(message))
    
    def start_check(self):
        input_file = self.input_file.get()
        
        if not input_file or not os.path.exists(input_file):
            messagebox.showerror("Ошибка", "Выберите файл с аккаунтами!")
            return
        
        accounts = []
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and ':' in line:
                        accounts.append(line)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать файл: {e}")
            return
        
        if not accounts:
            messagebox.showerror("Ошибка", "Файл не содержит аккаунтов!")
            return
        
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        dir_name = os.path.dirname(input_file) or '.'
        self.valid_file_path = os.path.join(dir_name, f"{base_name}_valid.txt")
        self.invalid_file_path = os.path.join(dir_name, f"{base_name}_invalid.txt")
        
        self.log_text.delete(1.0, tk.END)
        self.add_log_message(f"Найдено {len(accounts)} аккаунтов для проверки", "info")
        self.add_log_message("=" * 50, "info")
        
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.progress_bar.start(10)
        self.open_valid_btn.config(state=tk.DISABLED)
        self.open_invalid_btn.config(state=tk.DISABLED)
        
        log_file_path = None
        if self.save_logs.get():
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            dir_name = os.path.dirname(input_file) or '.'
            log_file_path = os.path.join(dir_name, f"{base_name}_debug_log.txt")
            try:
                with open(log_file_path, 'w', encoding='utf-8') as f:
                    f.write(f"=== Лог проверки аккаунтов my.games ===\n")
                    f.write(f"Время начала: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Файл с аккаунтами: {input_file}\n")
                    f.write(f"Задержка: {self.delay.get()} сек\n")
                    f.write(f"Подробные логи: {self.debug_mode.get()}\n")
                    f.write("=" * 50 + "\n\n")
                self.add_log_message(f"Логи будут сохранены в: {log_file_path}", "info")
            except Exception as e:
                self.add_log_message(f"Не удалось создать файл логов: {e}", "error")
        
        self.checker = AccountChecker(
            delay=self.delay.get(),
            debug=self.debug_mode.get(),
            callback=self.update_status,
            log_file=log_file_path
        )
        
        self.check_thread = threading.Thread(
            target=self.checker.check_accounts_list,
            args=(accounts, self.valid_file_path, self.invalid_file_path),
            daemon=True
        )
        self.check_thread.start()
        
        threading.Thread(target=self.wait_for_completion, daemon=True).start()
    
    def wait_for_completion(self):
        if self.check_thread:
            self.check_thread.join()
        self.root.after(0, self.check_complete)
    
    def check_complete(self):
        self.progress_bar.stop()
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.progress_var.set("Проверка завершена")
        
        if os.path.exists(self.valid_file_path):
            self.open_valid_btn.config(state=tk.NORMAL)
        if os.path.exists(self.invalid_file_path):
            self.open_invalid_btn.config(state=tk.NORMAL)
        
        messagebox.showinfo("Готово", "Проверка завершена!")
    
    def stop_check(self):
        if self.checker:
            self.checker.stop()
            self.add_log_message("Остановка проверки...", "warning")
        self.check_complete()
    
    def open_valid_file(self):
        if self.valid_file_path and os.path.exists(self.valid_file_path):
            os.startfile(self.valid_file_path)
    
    def open_invalid_file(self):
        if self.invalid_file_path and os.path.exists(self.invalid_file_path):
            os.startfile(self.invalid_file_path)

