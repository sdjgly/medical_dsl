import sqlite3
import re
from typing import Dict, List, Any, Optional
from llm_client import DeepSeekClient

class DSLInterpreter:
    """DSL解释器"""
    
    def __init__(self, script_ast: Dict[str, Any], llm_client: DeepSeekClient = None, db_path: str = None):
        """初始化解释器"""
        self.script = script_ast
        self.llm_client = llm_client
        self.current_step = "welcome"
        self.conversation_history: List[Dict[str, str]] = []
        self.variables: Dict[str, Any] = {}
        self.locks: Dict[str, bool] = {}
        self.is_running = True
        self.input_function = input

        # 初始化数据库连接
        self.db_conn = None
        if db_path:
            try:
                self.db_conn = sqlite3.connect(db_path)
                print(f"数据库连接成功: {db_path}")
            except Exception as e:
                print(f"数据库连接失败: {e}")
    
    def __del__(self):
        """清理资源"""
        if self.db_conn:
            self.db_conn.close()
    
    def run(self):
        """运行解释器"""
        module_name = self.script.get('module', '通用机器人')
        print(f"\n {module_name} 已启动")
        print("输入 '退出' 结束对话")
        print("=" * 50)
        
        while self.is_running and self.current_step:
            self._execute_current_step()
    
    def _execute_current_step(self):
        """执行当前步骤"""
        step_name = self.current_step
        step_data = self.script['steps'].get(step_name)
        
        if not step_data:
            print(f"错误：找不到步骤 '{step_name}'")
            self.is_running = False
            return
        
        print(f"\n[步骤: {step_name}]")
        
        # 执行步骤中的所有动作
        for action in step_data['actions']:
            if not self.is_running:
                break
                
            result = self._execute_action(action)
            
            # 如果有跳转结果，立即跳转
            if result and "next_step" in result:
                self.current_step = result["next_step"]
                return
                
            # 如果有用户输入需要处理
            if result and "user_input" in result:
                self._handle_user_input(step_data, result["user_input"])
                return
    
    def _execute_action(self, action: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """执行单个动作"""
        try:
            action_type = action['type']
            
            if action_type == "Speak":
                return self._execute_speak(action['message'])
            elif action_type == "Listen":
                return self._execute_listen()
            elif action_type == "ListenAssign":
                return self._execute_listen_assign(action['variable'])
            elif action_type == "AIReply":
                return self._execute_ai_reply()
            elif action_type == "Exit":
                return self._execute_exit()
            elif action_type == "Goto":
                return {"next_step": action['target']}
            elif action_type == "Lock":
                return self._execute_lock(action['resource'])
            elif action_type == "Unlock":
                return self._execute_unlock(action['resource'])
            elif action_type == "DBQuery":
                return self._execute_db_query(action['query'], action['variable'], action['target'])
            elif action_type == "DBExec":
                return self._execute_db_exec(action['query'])
            elif action_type == "If":
                return self._execute_if(action['condition'], action['target'])
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
        # 替换变量
        formatted_message = self._replace_variables(message)
        print(f"机器人: {formatted_message}")
        self.conversation_history.append({
            "role": "assistant",
            "content": formatted_message
        })
        return None
    
    def _execute_listen(self) -> Dict[str, Any]:
        """执行监听动作"""
        user_input = self.input_function("用户: ").strip()
        
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
    
    def _execute_listen_assign(self, variable: str) -> Dict[str, Any]:
        """执行带赋值的监听动作"""
        user_input = self.input_function("用户: ").strip()
        
        if not user_input:
            return {"next_step": self.current_step}
            
        # 存储用户输入到变量
        self.variables[variable] = user_input
        print(f"已存储用户输入到变量 '{variable}': {user_input}")
        
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
            print("AI功能未启用")
            return None
            
        print("正在思考中...")
        
        context = {
            "conversation_history": self.conversation_history,
            "current_step": self.current_step,
            "script_module": self.script.get('module', ''),
            "variables": self.variables
        }
        
        try:
            reply = self.llm_client.generate_reply(user_input, context)
            print(f"机器人: {reply}")
            
            self.conversation_history.append({
                "role": "assistant",
                "content": reply
            })
            
        except Exception as e:
            print(f"机器人: 抱歉，AI服务暂时不可用: {e}")
        
        return None
    
    def _execute_exit(self) -> Dict[str, Any]:
        """执行退出动作"""
        self.is_running = False
        return {}
    
    def _execute_lock(self, resource: str) -> None:
        """执行锁定动作"""
        if resource in self.locks and self.locks[resource]:
            print(f"资源 '{resource}' 已被锁定")
        else:
            self.locks[resource] = True
            print(f"已锁定资源: {resource}")
        return None
    
    def _execute_unlock(self, resource: str) -> None:
        """执行解锁动作"""
        if resource in self.locks:
            self.locks[resource] = False
            print(f"已解锁资源: {resource}")
        else:
            print(f"资源 '{resource}' 未被锁定")
        return None
    
    def _execute_db_query(self, query: str, variable: str, target: str) -> Dict[str, Any]:
        """执行数据库查询动作"""
        if not self.db_conn:
            print("错误：数据库未连接")
            return {"next_step": target}
        
        try:
            # 替换查询中的变量
            formatted_query = self._replace_variables(query)
            cursor = self.db_conn.cursor()
            cursor.execute(formatted_query)
            result = cursor.fetchone()
            
            if result:
                # 存储查询结果到变量
                self.variables[variable] = result[0] if len(result) == 1 else result
                print(f"数据库查询结果存储到变量 '{variable}': {self.variables[variable]}")
            else:
                self.variables[variable] = None
                print(f"数据库查询无结果，变量 '{variable}' 设为 None")
            
            return {"next_step": target}
            
        except Exception as e:
            print(f"数据库查询错误: {e}")
            return {"next_step": target}
    
    def _execute_db_exec(self, query: str) -> None:
        """执行数据库更新动作"""
        if not self.db_conn:
            print("错误：数据库未连接")
            return None
        
        try:
            # 替换查询中的变量
            formatted_query = self._replace_variables(query)
            cursor = self.db_conn.cursor()
            cursor.execute(formatted_query)
            self.db_conn.commit()
            print(f"数据库更新成功: {formatted_query}")
        except Exception as e:
            print(f"数据库更新错误: {e}")
        
        return None
    
    def _execute_if(self, condition: Dict[str, Any], target: str) -> Optional[Dict[str, Any]]:
        """执行条件判断动作"""
        left = condition['left']
        operator = condition['operator']
        right = condition['right']
        
        # 获取左值（可能是变量或字面量）
        left_value = self.variables.get(left, left)
        
        # 获取右值（可能是变量或字面量）
        if isinstance(right, str) and right in self.variables:
            right_value = self.variables[right]
        else:
            right_value = right
        
        # 类型转换
        try:
            if isinstance(left_value, str) and isinstance(right_value, (int, float)):
                left_value = float(left_value) if '.' in str(left_value) else int(left_value)
            elif isinstance(right_value, str) and isinstance(left_value, (int, float)):
                right_value = float(right_value) if '.' in str(right_value) else int(right_value)
        except ValueError:
            pass
        
        # 执行比较
        result = False
        if operator == '==':
            result = left_value == right_value
        elif operator == '!=':
            result = left_value != right_value
        elif operator == '<':
            result = left_value < right_value
        elif operator == '<=':
            result = left_value <= right_value
        elif operator == '>':
            result = left_value > right_value
        elif operator == '>=':
            result = left_value >= right_value
        
        print(f"条件判断: {left_value} {operator} {right_value} = {result}")
        
        if result:
            return {"next_step": target}
        
        return None
    
    def _handle_user_input(self, step_data: Dict[str, Any], user_input: str):
        """处理用户输入并决定下一个步骤"""
        # 收集所有Case和Default动作
        cases = []
        default_target = None
        
        for action in step_data['actions']:
            if action['type'] == "Case":
                cases.append((action['pattern'], action['target']))
            elif action['type'] == "Default":
                default_target = action['target']
        
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
            
            try:
                recognized_intent = self.llm_client.recognize_intent(user_input, candidate_intents)
                
                # 匹配识别的意图
                for pattern, target in cases:
                    if pattern == recognized_intent:
                        self.current_step = target
                        return
            except Exception as e:
                print(f"意图识别失败: {e}")
        
        # 使用默认跳转
        self.current_step = default_target or "fallback"
    
    def _replace_variables(self, text: str) -> str:
        """替换文本中的变量占位符"""
        def replace_match(match):
            var_name = match.group(1)
            return str(self.variables.get(var_name, f"{{{var_name}}}"))
        
        return re.sub(r'\{(\w+)\}', replace_match, text)