from typing import Dict, List, Any, Tuple
from llm_client import DeepSeekClient

class DSLInterpreter:
    """基于元组的DSL解释器"""
    
    def __init__(self, script_ast: Dict[str, Any], llm_client: DeepSeekClient = None):
        self.script = script_ast
        self.llm_client = llm_client
        self.current_step = "welcome"
        self.conversation_history: List[Dict[str, str]] = []
        self.is_running = True
        
    def run(self):
        """运行解释器"""
        print(f"\n{self.script.get('module', '机器人')} 已启动")
        print("输入 '退出' 结束对话\n")
        
        while self.is_running and self.current_step:
            self._execute_current_step()
    
    def _execute_current_step(self):
        """执行当前步骤"""
        step_name = self.current_step
        step = self.script["steps"].get(step_name)
        
        if not step:
            print(f"错误：找不到步骤 '{step_name}'")
            self.is_running = False
            return
        
        print(f"[步骤: {step_name}]")
        
        # 执行步骤中的所有动作
        for action_type, action_value in step["actions"]:
            if not self.is_running:
                break
                
            result = self._execute_action(action_type, action_value)
            
            # 如果有跳转结果，立即跳转
            if result and "next_step" in result:
                self.current_step = result["next_step"]
                return
                
            # 如果有用户输入需要处理
            if result and "user_input" in result:
                self._handle_user_input(step, result["user_input"])
                return
    
    def _execute_action(self, action_type: str, action_value: Any) -> Dict[str, Any]:
        """执行单个动作"""
        try:
            if action_type == "Speak":
                return self._execute_speak(action_value)
            elif action_type == "Listen":
                return self._execute_listen()
            elif action_type == "AIReply":
                return self._execute_ai_reply()
            elif action_type == "Exit":
                return self._execute_exit()
            elif action_type == "goto":
                return {"next_step": action_value}
            elif action_type in ["Case", "Default"]:
                # Case和Default在handle_user_input中处理
                return None
            else:
                print(f"未知动作类型: {action_type}")
                return None
                
        except Exception as e:
            print(f"执行动作出错: {e}")
            return {"next_step": "fallback"}
    
    def _execute_speak(self, message: str) -> None:
        """执行说话动作"""
        print(f"机器人: {message}")
        self.conversation_history.append({
            "role": "assistant",
            "content": message
        })
        return None
    
    def _execute_listen(self) -> Dict[str, Any]:
        """执行监听动作"""
        user_input = input("用户: ").strip()
        
        if not user_input:
            return {"next_step": self.current_step}
            
        self.conversation_history.append({
            "role": "user", 
            "content": user_input
        })
        
        # 特殊命令处理
        if user_input.lower() in ['退出', 'exit', 'quit']:
            return {"next_step": "goodbye"}
            
        return {"user_input": user_input}
    
    def _execute_ai_reply(self) -> None:
        """执行AI回复动作"""
        if not self.conversation_history or self.conversation_history[-1]["role"] != "user":
            print("错误：AI回复前需要用户输入")
            return None
            
        user_input = self.conversation_history[-1]["content"]
        
        if not self.llm_client:
            print("机器人: AI功能未启用")
            return None
            
        print("机器人: 正在思考中...")
        
        context = {
            "conversation_history": self.conversation_history,
            "current_step": self.current_step
        }
        
        reply = self.llm_client.generate_reply(user_input, context)
        print(f"机器人: {reply}")
        
        self.conversation_history.append({
            "role": "assistant",
            "content": reply
        })
        
        return None
    
    def _execute_exit(self) -> Dict[str, Any]:
        """执行退出动作"""
        self.is_running = False
        return {}
    
    def _handle_user_input(self, step: Dict[str, Any], user_input: str):
        """处理用户输入并决定下一个步骤"""
        # 收集所有Case和Default
        cases = []
        default_target = None
        
        for action_type, action_value in step["actions"]:
            if action_type == "Case":
                cases.append(action_value)  # (pattern, target)
            elif action_type == "Default":
                default_target = action_value
        
        # 如果没有Case，直接使用默认跳转
        if not cases:
            self.current_step = default_target or "welcome"
            return
        
        # 尝试精确匹配
        for pattern, target in cases:
            if user_input == pattern:
                self.current_step = target
                return
        
        # 使用LLM进行意图识别
        if self.llm_client:
            candidate_intents = [pattern for pattern, _ in cases]
            recognized_intent = self.llm_client.recognize_intent(user_input, candidate_intents)
            
            # 匹配识别的意图
            for pattern, target in cases:
                if pattern == recognized_intent:
                    self.current_step = target
                    return
        
        # 使用默认跳转
        self.current_step = default_target or "fallback"