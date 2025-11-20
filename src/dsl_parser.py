import ply.lex as lex
import ply.yacc as yacc
from typing import Dict, List, Any, Optional

# 词法分析器 
tokens = (
    'MODULE', 'STEP', 'SPEAK', 'LISTEN', 'CASE', 'DEFAULT', 'GOTO', 
    'AIREPLY', 'EXIT', 'LOCK', 'UNLOCK', 'DBQUERY', 'DBEXEC', 'IF', 
    'ASSIGN', 'STRING', 'ID', 'ARROW', 'COMPARE', 'NUMBER'
)

# 保留字
reserved = {
    'module': 'MODULE',
    'Step': 'STEP',
    'Speak': 'SPEAK',
    'Listen': 'LISTEN',
    'Case': 'CASE',
    'Default': 'DEFAULT',
    'goto': 'GOTO',
    'AIReply': 'AIREPLY',
    'Exit': 'EXIT',
    'Lock': 'LOCK',
    'Unlock': 'UNLOCK',
    'DBQuery': 'DBQUERY',
    'DBExec': 'DBEXEC',
    'If': 'IF',
    'assign': 'ASSIGN',
}

# 运算符
t_ARROW = r'->'
t_COMPARE = r'<=|>=|==|!=|<|>'

# 忽略字符
t_ignore = ' \t'

def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = reserved.get(t.value, 'ID')
    return t

def t_STRING(t):
    r'\"([^\\\n]|(\\.))*?\"'
    t.value = t.value[1:-1]  # 去除引号
    return t

def t_NUMBER(t):
    r'\d+'
    t.value = int(t.value)
    return t

def t_COMMENT(t):
    r'\#.*'
    pass  # 忽略注释

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_error(t):
    print(f"非法字符 '{t.value[0]}'")
    t.lexer.skip(1)

# --- 语法分析器 ---
def p_script(p):
    '''script : module_def steps'''
    p[0] = {
        'module': p[1],
        'steps': p[2]
    }

def p_module_def(p):
    '''module_def : MODULE STRING'''
    p[0] = p[2]

def p_steps(p):
    '''steps : step steps
             | step'''
    if len(p) == 2:
        p[0] = {p[1]['name']: p[1]}
    else:
        p[0] = {p[1]['name']: p[1]}
        p[0].update(p[2])

def p_step(p):
    '''step : STEP ID actions'''
    p[0] = {
        'name': p[2],
        'actions': p[3]
    }

def p_actions(p):
    '''actions : action actions
               | action'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = [p[1]] + p[2]

def p_action(p):
    '''action : speak_action
              | listen_action
              | case_action
              | default_action
              | goto_action
              | aireply_action
              | exit_action
              | lock_action
              | unlock_action
              | dbquery_action
              | dbexec_action
              | if_action
              | listen_assign_action'''
    p[0] = p[1]

def p_speak_action(p):
    '''speak_action : SPEAK STRING'''
    p[0] = {'type': 'Speak', 'message': p[2]}

def p_listen_action(p):
    '''listen_action : LISTEN'''
    p[0] = {'type': 'Listen'}

def p_listen_assign_action(p):
    '''listen_assign_action : LISTEN ASSIGN ID'''
    p[0] = {'type': 'ListenAssign', 'variable': p[3]}

def p_case_action(p):
    '''case_action : CASE STRING ARROW GOTO ID'''
    p[0] = {'type': 'Case', 'pattern': p[2], 'target': p[5]}

def p_default_action(p):
    '''default_action : DEFAULT ARROW GOTO ID'''
    p[0] = {'type': 'Default', 'target': p[4]}

def p_goto_action(p):
    '''goto_action : GOTO ID'''
    p[0] = {'type': 'Goto', 'target': p[2]}

def p_aireply_action(p):
    '''aireply_action : AIREPLY'''
    p[0] = {'type': 'AIReply'}

def p_exit_action(p):
    '''exit_action : EXIT'''
    p[0] = {'type': 'Exit'}

def p_lock_action(p):
    '''lock_action : LOCK STRING'''
    p[0] = {'type': 'Lock', 'resource': p[2]}

def p_unlock_action(p):
    '''unlock_action : UNLOCK STRING'''
    p[0] = {'type': 'Unlock', 'resource': p[2]}

def p_dbquery_action(p):
    '''dbquery_action : DBQUERY STRING ARROW GOTO ID ID'''
    p[0] = {'type': 'DBQuery', 'query': p[2], 'variable': p[6], 'target': p[5]}

def p_dbexec_action(p):
    '''dbexec_action : DBEXEC STRING'''
    p[0] = {'type': 'DBExec', 'query': p[2]}

def p_if_action(p):
    '''if_action : IF condition ARROW GOTO ID'''
    p[0] = {'type': 'If', 'condition': p[2], 'target': p[5]}

def p_condition(p):
    '''condition : ID COMPARE NUMBER
                 | ID COMPARE ID
                 | ID COMPARE STRING'''
    p[0] = {
        'left': p[1],
        'operator': p[2],
        'right': p[3]
    }

def p_error(p):
    if p:
        print(f"语法错误在第 {p.lineno} 行: 遇到意外的符号 '{p.value}'")
    else:
        print("语法错误: 意外的文件结束")

# --- 构建解析器 ---
lexer = lex.lex()
parser = yacc.yacc()

def parse_script(text: str) -> Dict[str, Any]:
    try:
        return parser.parse(text, lexer=lexer)
    except Exception as e:
        raise SyntaxError(f"解析失败: {e}")

def load_script_from_file(file_path: str) -> Dict[str, Any]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return parse_script(content)
    except FileNotFoundError:
        raise FileNotFoundError(f"找不到脚本文件: {file_path}")
    except Exception as e:
        raise Exception(f"加载脚本失败: {e}")

"""
if __name__ == "__main__":
    # 测试解析器
    test_script = '''
module "test"
Step test
    Speak "测试消息"
    Listen assign var1
    If var1 == 10 -> goto next
    DBQuery "SELECT * FROM table" -> goto process result_var
    Lock "resource1"
    Exit
'''
    try:
        result = parse_script(test_script)
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"测试失败: {e}")
"""