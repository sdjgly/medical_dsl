import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import os
import sys
import sqlite3
import uuid
import time
from datetime import datetime
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
        self.gui_output_callback = None  # GUI输出回调
    
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

class UserSession:
    """用户会话类"""
    
    def __init__(self, user_id: str, module_type: str, use_ai: bool = True):
        self.user_id = user_id
        self.module_type = module_type
        self.use_ai = use_ai
        self.interpreter = None
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.is_active = True
        self.input_queue = queue.Queue()  # 每个用户有自己的输入队列
        self.thread_running = True  # 添加线程运行标志
        
    def update_activity(self):
        """更新最后活动时间"""
        self.last_activity = datetime.now()
    
    def close(self):
        """关闭会话"""
        self.is_active = False
        self.thread_running = False  # 设置线程停止标志
        if self.interpreter:
            self.interpreter.is_running = False

class SessionManager:
    """会话管理器"""
    
    def __init__(self):
        self.sessions: Dict[str, UserSession] = {}
        self.lock = threading.Lock()
    
    def create_session(self, module_type: str, use_ai: bool = True) -> str:
        """创建新会话"""
        user_id = str(uuid.uuid4())[:8]  # 生成短用户ID
        session = UserSession(user_id, module_type, use_ai)
        
        with self.lock:
            self.sessions[user_id] = session
        
        return user_id
    
    def get_session(self, user_id: str) -> UserSession:
        """获取会话"""
        with self.lock:
            return self.sessions.get(user_id)
    
    def remove_session(self, user_id: str):
        """移除会话"""
        with self.lock:
            if user_id in self.sessions:
                self.sessions[user_id].close()
                del self.sessions[user_id]
    
    def get_all_sessions(self):
        """获取所有会话"""
        with self.lock:
            return list(self.sessions.values())
    
    def cleanup_inactive_sessions(self, timeout_minutes=30):
        """清理不活跃的会话"""
        with self.lock:
            current_time = datetime.now()
            inactive_sessions = []
            
            for user_id, session in self.sessions.items():
                if (current_time - session.last_activity).total_seconds() > timeout_minutes * 60:
                    inactive_sessions.append(user_id)
            
            for user_id in inactive_sessions:
                self.sessions[user_id].close()
                del self.sessions[user_id]
            
            return len(inactive_sessions)

class DSLChatbot:
    """DSL智能客服主类"""
    
    def __init__(self, script_path: str, use_ai: bool = True, db_path: str = None):
        self.script_path = script_path
        self.use_ai = use_ai
        self.db_path = db_path
        self.llm_client = None
        self.interpreter = None
        self.script_ast = None
        
    def initialize(self):
        """初始化系统"""
        try:
            # 加载DSL脚本
            if not os.path.exists(self.script_path):
                raise FileNotFoundError(f"脚本文件不存在: {self.script_path}")
                
            self.script_ast = load_script_from_file(self.script_path)
            module_name = self.script_ast.get('module', '未知模块')
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
            
            return True
            
        except Exception as e:
            print(f"初始化失败: {e}")
            return False

class MultiUserDSLChatbotGUI:
    """多用户DSL智能客服图形界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("多用户DSL智能客服系统")
        self.root.geometry("1000x700")
        
        # 会话管理
        self.session_manager = SessionManager()
        self.current_user_id = None
        
        # 输出队列映射：user_id -> output_queue
        self.output_queues: Dict[str, queue.Queue] = {}
        
        # 创建界面
        self.create_widgets()
        
        # 启动会话清理线程
        self.running = True
        self.cleanup_thread = threading.Thread(target=self.cleanup_sessions, daemon=True)
        self.cleanup_thread.start()
        
        # 定期检查输出队列
        self.root.after(100, self.check_output_queues)
    
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
        
        # 用户管理区域
        user_frame = ttk.LabelFrame(main_frame, text="用户管理", padding="5")
        user_frame.grid(row=0, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=5)
        user_frame.columnconfigure(1, weight=1)
        
        ttk.Label(user_frame, text="选择业务模块:").grid(row=0, column=0, sticky=tk.W, pady=2)
        
        self.module_var = tk.StringVar()
        module_combo = ttk.Combobox(user_frame, textvariable=self.module_var, 
                                   values=["医疗客服", "电商客服"], state="readonly", width=15)
        module_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        # AI 功能开关
        self.ai_var = tk.BooleanVar(value=True)
        ai_check = ttk.Checkbutton(user_frame, text="启用AI功能", variable=self.ai_var)
        ai_check.grid(row=0, column=2, padx=10, pady=2)
        
        # 创建用户按钮
        self.create_user_btn = ttk.Button(user_frame, text="创建新用户", command=self.create_user_session)
        self.create_user_btn.grid(row=0, column=3, padx=5, pady=2)
        
        # 用户列表
        ttk.Label(user_frame, text="当前用户:").grid(row=1, column=0, sticky=tk.W, pady=2)
        
        self.user_var = tk.StringVar()
        self.user_combo = ttk.Combobox(user_frame, textvariable=self.user_var, state="readonly", width=15)
        self.user_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        self.user_combo.bind('<<ComboboxSelected>>', self.on_user_selected)
        
        # 删除用户按钮
        self.delete_user_btn = ttk.Button(user_frame, text="删除用户", command=self.delete_user_session)
        self.delete_user_btn.grid(row=1, column=3, padx=5, pady=2)
        
        # 对话显示区域
        chat_frame = ttk.LabelFrame(main_frame, text="对话记录", padding="5")
        chat_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        chat_frame.columnconfigure(0, weight=1)
        chat_frame.rowconfigure(0, weight=1)
        
        self.chat_display = scrolledtext.ScrolledText(chat_frame, width=100, height=25, 
                                                     state=tk.DISABLED, wrap=tk.WORD)
        self.chat_display.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 输入区域
        input_frame = ttk.Frame(main_frame)
        input_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=10)
        input_frame.columnconfigure(0, weight=1)
        
        ttk.Label(input_frame, text="输入消息:").grid(row=0, column=0, sticky=tk.W)
        
        self.input_entry = ttk.Entry(input_frame)
        self.input_entry.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        self.input_entry.bind('<Return>', self.send_message)
        
        self.send_btn = ttk.Button(input_frame, text="发送", command=self.send_message)
        self.send_btn.grid(row=1, column=1, padx=5, pady=5)
        
        # 状态栏
        self.status_var = tk.StringVar(value="请创建新用户会话")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=3, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # 初始禁用输入
        self.input_entry.config(state=tk.DISABLED)
        self.send_btn.config(state=tk.DISABLED)
        self.delete_user_btn.config(state=tk.DISABLED)
    
    def create_user_session(self):
        """创建新用户会话"""
        if not self.module_var.get():
            messagebox.showwarning("警告", "请先选择业务模块")
            return
        
        # 确定模块类型
        if self.module_var.get() == "医疗客服":
            module_type = "medical"
        else:
            module_type = "ecommerce"
        
        # 创建新会话
        user_id = self.session_manager.create_session(module_type, self.ai_var.get())
        
        # 创建输出队列
        self.output_queues[user_id] = queue.Queue()
        
        # 启动用户会话线程
        session_thread = threading.Thread(
            target=self.run_user_session, 
            args=(user_id,),
            daemon=True
        )
        session_thread.start()
        
        # 更新用户列表
        self.update_user_list()
        
        # 自动选择新用户
        self.user_var.set(user_id)
        self.on_user_selected()
        
        self.status_var.set(f"已创建用户 {user_id} - 会话已启动")
    
    def run_user_session(self, user_id: str):
        """运行用户会话（在线程中）"""
        try:
            session = self.session_manager.get_session(user_id)
            if not session:
                return
            
            # 获取脚本路径
            script_path = os.path.join(project_root, "scripts", f"{session.module_type}.txt")
            
            # 确定数据库路径
            db_path = None
            if session.module_type == "ecommerce":
                db_path = os.path.join(project_root, "database", "ecommerce.db")
            
            # 创建聊天机器人实例
            chatbot = DSLChatbot(
                script_path=script_path,
                use_ai=session.use_ai,
                db_path=db_path
            )
            
            # 初始化聊天机器人
            if not chatbot.initialize():
                # 检查用户会话是否还存在
                if user_id in self.output_queues:
                    self.output_queues[user_id].put(("error", f"用户 {user_id} 初始化失败"))
                return
            
            # 创建线程安全的解释器
            interpreter = ThreadSafeDSLInterpreter(
                script_ast=chatbot.script_ast,
                llm_client=chatbot.llm_client,
                db_path=db_path
            )
            
            # 设置GUI输出回调
            interpreter.set_gui_output_callback(lambda msg: self.gui_output(user_id, msg))
            
            # 重写输入函数，使用用户的输入队列
            interpreter.input_function = lambda prompt: self.get_user_input(user_id, prompt)
            
            # 保存解释器到会话
            session.interpreter = interpreter
            
            # 发送欢迎消息 - 检查会话是否还存在
            if user_id in self.output_queues:
                self.output_queues[user_id].put(("message", f"=== 用户 {user_id} 会话开始 ==="))
                self.output_queues[user_id].put(("message", f"模块: {session.module_type}"))
                self.output_queues[user_id].put(("message", f"AI功能: {'启用' if session.use_ai else '禁用'}"))
                self.output_queues[user_id].put(("message", "=" * 50))
            
            # 运行解释器
            interpreter.run()
            
            # 会话结束 - 检查会话是否还存在
            if user_id in self.output_queues:
                self.output_queues[user_id].put(("message", f"=== 用户 {user_id} 会话结束 ==="))
                
        except Exception as e:
            # 检查会话是否还存在
            if user_id in self.output_queues:
                self.output_queues[user_id].put(("error", f"用户 {user_id} 会话错误: {e}"))
    
    def get_user_input(self, user_id: str, prompt=None):
        """获取用户输入（在线程中调用）"""
        # 检查会话是否还存在
        session = self.session_manager.get_session(user_id)
        if not session or not session.thread_running:
            return "退出"  # 如果会话已关闭，返回退出命令
        
        # 更新会话活动时间
        session.update_activity()
        
        # 等待用户输入
        if user_id == self.current_user_id:
            # 当前活跃用户，等待输入
            try:
                user_input = session.input_queue.get(timeout=0.5)  # 添加超时，定期检查会话状态
                return user_input
            except queue.Empty:
                # 超时，检查会话是否仍然活跃
                if session and session.thread_running:
                    return self.get_user_input(user_id, prompt)  # 继续等待
                else:
                    return "退出"
        else:
            # 非活跃用户，返回退出命令
            return "退出"
    
    def gui_output(self, user_id: str, message: str):
        """GUI输出回调函数"""
        # 检查输出队列是否还存在
        if user_id in self.output_queues:
            try:
                self.output_queues[user_id].put(("message", f"机器人: {message}"))
            except:
                pass  # 如果队列已关闭，忽略错误
    
    def on_user_selected(self, event=None):
        """用户选择事件"""
        user_id = self.user_var.get()
        if not user_id:
            return
        
        self.current_user_id = user_id
        session = self.session_manager.get_session(user_id)
        
        if session:
            self.status_var.set(f"当前用户: {user_id} - 模块: {session.module_type}")
            self.input_entry.config(state=tk.NORMAL)
            self.send_btn.config(state=tk.NORMAL)
            self.delete_user_btn.config(state=tk.NORMAL)
            self.input_entry.focus()
            
            # 清空对话显示，准备显示当前用户的对话
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete(1.0, tk.END)
            self.chat_display.config(state=tk.DISABLED)
    
    def delete_user_session(self):
        """删除用户会话"""
        user_id = self.user_var.get()
        if not user_id:
            return
        
        # 结束会话
        session = self.session_manager.get_session(user_id)
        if session:
            session.close()  # 先关闭会话
        
        # 移除输出队列
        if user_id in self.output_queues:
            # 清空队列并移除
            try:
                while True:
                    self.output_queues[user_id].get_nowait()
            except queue.Empty:
                pass
            del self.output_queues[user_id]
        
        # 从会话管理器移除
        self.session_manager.remove_session(user_id)
        
        # 更新界面
        self.update_user_list()
        self.input_entry.config(state=tk.DISABLED)
        self.send_btn.config(state=tk.DISABLED)
        self.delete_user_btn.config(state=tk.DISABLED)
        self.status_var.set(f"已删除用户 {user_id}")
        
        # 清空对话显示
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.config(state=tk.DISABLED)
        
        self.current_user_id = None
    
    def update_user_list(self):
        """更新用户列表"""
        users = list(self.session_manager.sessions.keys())
        self.user_combo['values'] = users
        
        if not users:
            self.user_var.set("")
            self.current_user_id = None
    
    def send_message(self, event=None):
        """发送用户消息"""
        if not self.current_user_id:
            messagebox.showwarning("警告", "请先选择用户")
            return
        
        message = self.input_entry.get().strip()
        if not message:
            return
        
        # 显示用户消息
        self.display_message(f"用户 {self.current_user_id}: {message}")
        
        # 清空输入框
        self.input_entry.delete(0, tk.END)
        
        # 将消息发送到当前用户的输入队列
        session = self.session_manager.get_session(self.current_user_id)
        if session and session.thread_running:
            try:
                session.input_queue.put(message)
                session.update_activity()
            except:
                pass  # 如果队列已关闭，忽略错误
        
        # 特殊命令处理
        if message.lower() in ['退出', 'exit', 'quit']:
            self.delete_user_session()
    
    def display_message(self, message):
        """在对话显示区域显示消息"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, message + "\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
    
    def check_output_queues(self):
        """定期检查所有用户的输出队列"""
        for user_id, output_queue in list(self.output_queues.items()):  # 创建副本避免修改时迭代
            try:
                while True:
                    item_type, content = output_queue.get_nowait()
                    if item_type == "message":
                        # 只在当前用户是活跃用户时显示消息
                        if user_id == self.current_user_id:
                            self.display_message(content)
                    elif item_type == "error":
                        messagebox.showerror("错误", content)
            except queue.Empty:
                pass
        
        # 继续定期检查
        if self.running:
            self.root.after(100, self.check_output_queues)
    
    def cleanup_sessions(self):
        """清理不活跃会话"""
        while self.running:
            time.sleep(60)  # 每分钟检查一次
            if self.running:
                cleaned_count = self.session_manager.cleanup_inactive_sessions()
                if cleaned_count > 0:
                    print(f"清理了 {cleaned_count} 个不活跃会话")
                    # 同时清理输出队列
                    for user_id in list(self.output_queues.keys()):
                        if not self.session_manager.get_session(user_id):
                            del self.output_queues[user_id]
                    self.update_user_list()
    
    def stop_all_sessions(self):
        """停止所有会话"""
        self.running = False
        for user_id in list(self.session_manager.sessions.keys()):
            self.session_manager.remove_session(user_id)
        self.output_queues.clear()

def main():
    """主函数"""
    root = tk.Tk()
    app = MultiUserDSLChatbotGUI(root)
    
    # 处理窗口关闭事件
    def on_closing():
        app.stop_all_sessions()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()