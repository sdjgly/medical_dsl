import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import os
import sys
import sqlite3
from typing import Dict, Any

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from src.dsl_parser import load_script_from_file
from src.interpreter import DSLInterpreter
from src.llm_client import ZhipuAIClient
from database.init_db import init_db

class ThreadSafeDSLInterpreter(DSLInterpreter):
    """线程安全的DSL解释器"""
    
    def __init__(self, script_ast: Dict[str, Any], llm_client: ZhipuAIClient = None, db_path: str = None):
        super().__init__(script_ast, llm_client, db_path)
        # 不在初始化时连接数据库，在运行线程中连接
        self.db_path = db_path
        self.db_conn = None
        self.gui_output_callback = None  # 添加GUI输出回调
    
    def set_gui_output_callback(self, callback):
        """设置GUI输出回调函数"""
        self.gui_output_callback = callback
    
    def run(self):
        """运行解释器 - 在线程中连接数据库"""
        # 在线程中连接数据库
        if self.db_path and not self.db_conn:
            try:
                self.db_conn = sqlite3.connect(self.db_path)
                print(f"数据库连接成功: {self.db_path}")
            except Exception as e:
                print(f"数据库连接失败: {e}")
        
        super().run()
    
    def _execute_speak(self, message: str) -> None:
        """重写说话动作，使用GUI输出并替换变量"""
        # 替换变量
        formatted_message = self._replace_variables(message)
        
        if self.gui_output_callback:
            self.gui_output_callback(formatted_message)
        
        self.conversation_history.append({
            "role": "assistant",
            "content": formatted_message
        })
        return None
    
    def _execute_ai_reply(self) -> None:
        """重写AI回复方法，使用GUI输出"""
        if not self.conversation_history or self.conversation_history[-1]["role"] != "user":
            if self.gui_output_callback:
                self.gui_output_callback("错误：AI回复前需要用户输入")
            return None
            
        user_input = self.conversation_history[-1]["content"]
        
        if not self.llm_client:
            if self.gui_output_callback:
                self.gui_output_callback("AI功能未启用")
            return None
            
        if self.gui_output_callback:
            self.gui_output_callback("正在思考中...")
        
        context = {
            "conversation_history": self.conversation_history,
            "current_step": self.current_step,
            "script_module": self.script.get('module', ''),
            "variables": self.variables
        }
        
        try:
            reply = self.llm_client.generate_reply(user_input, context)
            if self.gui_output_callback:
                self.gui_output_callback(reply)
            
            self.conversation_history.append({
                "role": "assistant",
                "content": reply
            })
            
        except Exception as e:
            if self.gui_output_callback:
                self.gui_output_callback(f"抱歉，AI服务暂时不可用: {e}")
        
        return None
    
    def __del__(self):
        """清理资源"""
        if self.db_conn:
            try:
                self.db_conn.close()
            except:
                pass

class DSLChatbotGUI:
    """DSL智能客服图形界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("DSL智能客服系统")
        self.root.geometry("800x600")
        
        # 聊天机器人实例
        self.chatbot = None
        self.current_module = None
        
        # 线程通信队列
        self.input_queue = queue.Queue()
        self.output_queue = queue.Queue()
        
        # 创建界面
        self.create_widgets()
        self.setup_module_selection()
        
        # 启动输出监听线程
        self.running = True
        self.output_thread = threading.Thread(target=self.process_output, daemon=True)
        self.output_thread.start()
        
        # 定期检查输出队列
        self.root.after(100, self.check_output_queue)
    
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # 模块选择区域
        ttk.Label(main_frame, text="选择业务模块:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.module_var = tk.StringVar()
        module_combo = ttk.Combobox(main_frame, textvariable=self.module_var, 
                                   values=["医疗客服", "电商客服"], state="readonly")
        module_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        module_combo.bind('<<ComboboxSelected>>', self.on_module_selected)
        
        # AI 功能开关
        self.ai_var = tk.BooleanVar(value=True)
        ai_check = ttk.Checkbutton(main_frame, text="启用AI功能", variable=self.ai_var)
        ai_check.grid(row=0, column=2, padx=10, pady=5)
        
        # 启动按钮
        self.start_btn = ttk.Button(main_frame, text="启动客服", command=self.start_chatbot)
        self.start_btn.grid(row=0, column=3, padx=5, pady=5)
        
        # 对话显示区域
        ttk.Label(main_frame, text="对话记录:").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        
        self.chat_display = scrolledtext.ScrolledText(main_frame, width=80, height=25, 
                                                     state=tk.DISABLED, wrap=tk.WORD)
        self.chat_display.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # 输入区域
        input_frame = ttk.Frame(main_frame)
        input_frame.grid(row=3, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=10)
        input_frame.columnconfigure(0, weight=1)
        
        ttk.Label(input_frame, text="输入消息:").grid(row=0, column=0, sticky=tk.W)
        
        self.input_entry = ttk.Entry(input_frame)
        self.input_entry.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        self.input_entry.bind('<Return>', self.send_message)
        
        self.send_btn = ttk.Button(input_frame, text="发送", command=self.send_message)
        self.send_btn.grid(row=1, column=1, padx=5, pady=5)
        
        # 状态栏
        self.status_var = tk.StringVar(value="请选择业务模块并启动客服")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=4, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(5, 0))
    
    def setup_module_selection(self):
        """设置模块选择"""
        # 初始禁用输入
        self.input_entry.config(state=tk.DISABLED)
        self.send_btn.config(state=tk.DISABLED)
    
    def on_module_selected(self, event):
        """模块选择事件"""
        self.current_module = self.module_var.get()
        self.status_var.set(f"已选择: {self.current_module} - 点击'启动客服'开始对话")
    
    def start_chatbot(self):
        """启动聊天机器人"""
        if not self.current_module:
            messagebox.showwarning("警告", "请先选择业务模块")
            return
        
        # 确定模块类型和脚本路径
        if self.current_module == "医疗客服":
            module_type = "medical"
        else:
            module_type = "ecommerce"
        
        script_path = os.path.join(project_root, "scripts", f"{module_type}.txt")
        
        # 检查脚本文件是否存在
        if not os.path.exists(script_path):
            messagebox.showerror("错误", f"找不到脚本文件: {script_path}")
            return
        
        # 确定数据库路径
        db_path = None
        if module_type == "ecommerce":
            db_path = os.path.join(project_root, "database", "ecommerce.db")
        
        # 创建聊天机器人实例
        try:
            self.chatbot = DSLChatbot(
                script_path=script_path,
                use_ai=self.ai_var.get(),
                db_path=db_path
            )
            
            # 初始化聊天机器人
            if not self.chatbot.initialize():
                messagebox.showerror("错误", "聊天机器人初始化失败，请检查控制台输出")
                return
            
            # 设置GUI输出回调
            self.chatbot.interpreter.set_gui_output_callback(self.gui_output)
            
            # 在单独的线程中运行聊天机器人
            self.chat_thread = threading.Thread(target=self.run_chatbot, daemon=True)
            self.chat_thread.start()
            
            # 更新界面状态
            self.start_btn.config(state=tk.DISABLED)
            self.input_entry.config(state=tk.NORMAL)
            self.send_btn.config(state=tk.NORMAL)
            self.input_entry.focus()
            
            self.status_var.set(f"{self.current_module}已启动 - 请输入消息")
            
        except Exception as e:
            messagebox.showerror("错误", f"启动客服失败: {e}")
    
    def run_chatbot(self):
        """在单独线程中运行聊天机器人"""
        try:
            # 检查聊天机器人是否初始化成功
            if not self.chatbot or not self.chatbot.interpreter:
                self.output_queue.put(("error", "聊天机器人初始化失败，请检查脚本和数据库配置"))
                return
                
            # 重写解释器的输入函数，使用队列
            original_input = self.chatbot.interpreter.input_function
            self.chatbot.interpreter.input_function = self.get_user_input
            
            # 设置GUI输出回调
            self.chatbot.interpreter.set_gui_output_callback(self.gui_output)
            
            # 运行解释器
            self.chatbot.interpreter.run()
            
        except Exception as e:
            self.output_queue.put(("error", f"系统运行出错: {e}"))
    
    def gui_output(self, message):
        """GUI输出回调函数"""
        self.output_queue.put(("message", f"机器人: {message}"))
    
    def get_user_input(self, prompt=None):
        """获取用户输入（在线程中调用）"""
        # 等待用户输入
        user_input = self.input_queue.get()
        return user_input
    
    def send_message(self, event=None):
        """发送用户消息"""
        message = self.input_entry.get().strip()
        if not message:
            return
        
        # 显示用户消息
        self.display_message(f"用户: {message}")
        
        # 清空输入框
        self.input_entry.delete(0, tk.END)
        
        # 将消息发送到输入队列
        self.input_queue.put(message)
        
        # 特殊命令处理
        if message.lower() in ['退出', 'exit', 'quit']:
            self.stop_chatbot()
    
    def display_message(self, message):
        """在对话显示区域显示消息"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, message + "\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
    
    def process_output(self):
        """处理输出队列（在线程中运行）"""
        while self.running:
            try:
                item_type, content = self.output_queue.get(timeout=0.1)
                if item_type == "message":
                    self.root.after(0, self.display_message, content)
                elif item_type == "error":
                    self.root.after(0, messagebox.showerror, "错误", content)
            except queue.Empty:
                continue
    
    def check_output_queue(self):
        """定期检查输出队列"""
        try:
            while True:
                item_type, content = self.output_queue.get_nowait()
                if item_type == "message":
                    self.display_message(content)
                elif item_type == "error":
                    messagebox.showerror("错误", content)
        except queue.Empty:
            pass
        
        # 继续定期检查
        if self.running:
            self.root.after(100, self.check_output_queue)
    
    def stop_chatbot(self):
        """停止聊天机器人"""
        self.running = False
        if self.chatbot and self.chatbot.interpreter:
            self.chatbot.interpreter.is_running = False
        
        # 重置界面
        self.start_btn.config(state=tk.NORMAL)
        self.input_entry.config(state=tk.DISABLED)
        self.send_btn.config(state=tk.DISABLED)
        
        self.status_var.set("客服已停止 - 请重新选择模块启动")
        self.display_message("=== 对话结束 ===")

class DSLChatbot:
    """DSL智能客服主类（适配GUI版本）"""
    
    def __init__(self, script_path: str, use_ai: bool = True, db_path: str = None):
        self.script_path = script_path
        self.use_ai = use_ai
        self.db_path = db_path
        self.llm_client = None
        self.interpreter = None
        
    def initialize(self):
        """初始化系统"""
        try:
            # 加载DSL脚本
            if not os.path.exists(self.script_path):
                raise FileNotFoundError(f"脚本文件不存在: {self.script_path}")
                
            script_ast = load_script_from_file(self.script_path)
            module_name = script_ast.get('module', '未知模块')
            print(f"脚本加载成功 - 模块: {module_name}")
            
            # 初始化LLM客户端
            if self.use_ai:
                self.llm_client = ZhipuAIClient()
                # 测试AI连接
                try:
                    test_result = self.llm_client.recognize_intent("测试", ["测试"])
                    if "错误" in test_result or "未启用" in test_result:
                        print("AI服务不可用，将使用规则模式")
                        self.llm_client = None
                    else:
                        print("AI服务初始化成功")
                except Exception as e:
                    print(f"AI服务初始化失败: {e}")
                    self.llm_client = None
            
            # 初始化数据库（如果需要）
            if self.db_path:
                try:
                    db_dir = os.path.dirname(self.db_path)
                    if db_dir and not os.path.exists(db_dir):
                        os.makedirs(db_dir)
                    init_db(self.db_path)
                    print("数据库初始化成功")
                except Exception as e:
                    print(f"数据库初始化失败: {e}")
                    self.db_path = None
            
            # 创建线程安全的解释器
            self.interpreter = ThreadSafeDSLInterpreter(
                script_ast=script_ast,
                llm_client=self.llm_client,
                db_path=self.db_path
            )
            print("解释器初始化成功")
            return True
            
        except Exception as e:
            print(f"初始化失败: {e}")
            return False

def main():
    """主函数"""
    root = tk.Tk()
    app = DSLChatbotGUI(root)
    
    # 处理窗口关闭事件
    def on_closing():
        app.running = False
        if app.chatbot and app.chatbot.interpreter:
            app.chatbot.interpreter.is_running = False
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()