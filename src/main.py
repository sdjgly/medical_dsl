import os
import sys
from dsl_parser import parse_script
from interpreter import DSLInterpreter
from llm_client import DeepSeekClient

def load_script(file_path: str) -> str:
    """加载脚本文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"错误：找不到文件 {file_path}")
        sys.exit(1)

def main():
    SCRIPT_FILE = "medical.txt"
    API_KEY = os.getenv("DEEPSEEK_API_KEY")
    
    # 加载和解析脚本
    print("正在加载DSL脚本...")
    script_content = load_script(SCRIPT_FILE)
    
    try:
        script_ast = parse_script(script_content)
        print(f"脚本解析成功，共 {len(script_ast['steps'])} 个步骤")
    except Exception as e:
        print(f"脚本解析失败: {e}")
        sys.exit(1)
    
    # 初始化LLM客户端
    llm_client = None
    if API_KEY:
        llm_client = DeepSeekClient(API_KEY)
        print("LLM客户端已初始化")
    else:
        print("警告：未设置DEEPSEEK_API_KEY，AI功能将不可用")
    
    # 创建并运行解释器
    interpreter = DSLInterpreter(script_ast, llm_client)
    
    try:
        interpreter.run()
    except KeyboardInterrupt:
        print("\n\n程序结束")
    except Exception as e:
        print(f"\n程序出错: {e}")

if __name__ == "__main__":
    main()