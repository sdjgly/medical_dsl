import os
import sys
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from src.dsl_parser import load_script_from_file
from src.interpreter import DSLInterpreter
from src.llm_client import ZhipuAIClient
from database.init_db import init_db

class DSLChatbot:
    """DSL智能客服主类"""
    
    def __init__(self, script_path: str, use_ai: bool = True, db_path: str = None):
        self.script_path = script_path
        self.use_ai = use_ai
        self.db_path = db_path
        self.llm_client = None
        self.interpreter = None
        
    def initialize(self):
        """初始化系统"""
        print("初始化DSL智能客服系统...")
        
        # 1. 加载DSL脚本
        try:
            print(f"加载脚本: {self.script_path}")
            script_ast = load_script_from_file(self.script_path)
            module_name = script_ast.get('module', '未知模块')
            print(f"脚本加载成功 - 模块: {module_name}")
        except Exception as e:
            print(f"脚本加载失败: {e}")
            return False
        
        # 2. 初始化LLM客户端
        if self.use_ai:
            print("初始化AI服务...")
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
        else:
            print("使用纯规则模式（无AI）")
        
        # 3. 初始化数据库（如果需要）
        if self.db_path:
            print(f"初始化数据库: {self.db_path}")
            try:
                # 确保数据库目录存在
                db_dir = os.path.dirname(self.db_path)
                if db_dir and not os.path.exists(db_dir):
                    os.makedirs(db_dir)
                
                # 传递数据库路径给init_db
                init_db(self.db_path)
                print("数据库初始化成功")
            except Exception as e:
                print(f"数据库初始化失败: {e}")
                self.db_path = None
        
        # 4. 创建解释器
        try:
            self.interpreter = DSLInterpreter(
                script_ast=script_ast,
                llm_client=self.llm_client,
                db_path=self.db_path
            )
            print("解释器初始化成功")
        except Exception as e:
            print(f"解释器初始化失败: {e}")
            return False
            
        return True
    
    def run(self):
        """运行客服系统"""
        if not self.initialize():
            print("系统初始化失败，程序退出")
            return
        
        print("\n" + "="*60)
        print("DSL智能客服系统已就绪")
        print("输入 '退出', 'exit', 或 'quit' 结束对话")
        print("="*60)
        
        try:
            self.interpreter.run()
        except KeyboardInterrupt:
            print("\n\n用户中断对话，程序退出")
        except Exception as e:
            print(f"\n系统运行出错: {e}")
        finally:
            print("\n感谢使用DSL智能客服系统！")

def get_script_path(module_type: str) -> str:
    """根据模块类型获取脚本路径"""
    scripts_dir = os.path.join(project_root, "scripts")
    
    script_files = {
        "medical": "medical.txt",
        "ecommerce": "ecommerce.txt"
    }
    
    if module_type not in script_files:
        available = ", ".join(script_files.keys())
        raise ValueError(f"未知模块类型: {module_type}。可用模块: {available}")
    
    script_path = os.path.join(scripts_dir, script_files[module_type])
    
    if not os.path.exists(script_path):
        # 尝试在项目根目录查找
        alt_path = os.path.join(project_root, script_files[module_type])
        if os.path.exists(alt_path):
            return alt_path
        raise FileNotFoundError(f"找不到脚本文件: {script_path}")
    
    return script_path

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="DSL智能客服解释器")
    parser.add_argument(
        "module", 
        choices=["medical", "ecommerce"],
        help="业务模块类型: medical(医疗) 或 ecommerce(电商)"
    )
    parser.add_argument(
        "--db-path",
        help="数据库文件路径（电商模块需要）"
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="禁用AI功能，使用纯规则模式"
    )
    
    args = parser.parse_args()
    
    try:
        # 获取脚本路径
        script_path = get_script_path(args.module)
        
        # 确定数据库路径
        db_path = None
        if args.module == "ecommerce":
            if args.db_path:
                db_path = args.db_path
            else:
                # 使用相对项目根目录的路径
                db_path = os.path.join(project_root, "database", "ecommerce.db")
            print(f"使用数据库: {db_path}")
        
        # 创建并运行聊天机器人
        chatbot = DSLChatbot(
            script_path=script_path,
            use_ai=not args.no_ai,
            db_path=db_path
        )
        
        chatbot.run()
        
    except (ValueError, FileNotFoundError) as e:
        print(f"参数错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"程序运行出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()