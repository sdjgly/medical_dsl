import re
from typing import Dict, List, Any, Tuple

def parse_script(text: str) -> Dict[str, Any]:
    lines = text.splitlines()
    module = None
    steps = {}
    current_step = None
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        
        # 跳过空行和注释
        if not line or line.startswith('#'):
            continue
            
        # 模块定义
        if line.lower().startswith('module'):
            m = re.match(r'module\s+"([^"]+)"', line, re.IGNORECASE)
            if m:
                module = m.group(1)
            else:
                raise SyntaxError(f"Invalid module line: {line}")
            continue
            
        # 步骤定义
        if line.lower().startswith('step'):
            m = re.match(r'Step\s+([A-Za-z0-9_]+)', line, re.IGNORECASE)
            if not m:
                raise SyntaxError(f"Invalid Step line: {line}")
            current_step = m.group(1)
            steps[current_step] = {"actions": []}
            continue
            
        if current_step is None:
            raise SyntaxError("Action outside of a Step")
            
        # 解析各种动作
        if line.lower().startswith('speak'):
            m = re.match(r'Speak\s+"(.*)"', line, re.IGNORECASE)
            if not m:
                raise SyntaxError(f"Invalid Speak: {line}")
            steps[current_step]["actions"].append(("Speak", m.group(1)))
            continue
            
        if line.lower().startswith('listen'):
            steps[current_step]["actions"].append(("Listen", None))
            continue
            
        if line.lower().startswith('aireply'):
            steps[current_step]["actions"].append(("AIReply", None))
            continue
            
        if line.lower().startswith('exit'):
            steps[current_step]["actions"].append(("Exit", None))
            continue
            
        if line.lower().startswith('goto'):
            m = re.match(r'goto\s+([A-Za-z0-9_]+)', line, re.IGNORECASE)
            if not m:
                raise SyntaxError(f"Invalid goto: {line}")
            steps[current_step]["actions"].append(("goto", m.group(1)))
            continue
            
        if line.lower().startswith('case'):
            m = re.match(r'Case\s+"([^"]+)"\s*->\s*goto\s+([A-Za-z0-9_]+)', line, re.IGNORECASE)
            if not m:
                raise SyntaxError(f"Invalid Case: {line}")
            label = m.group(1)
            target = m.group(2)
            steps[current_step]["actions"].append(("Case", (label, target)))
            continue
            
        if line.lower().startswith('default'):
            m = re.match(r'Default\s*->\s*goto\s+([A-Za-z0-9_]+)', line, re.IGNORECASE)
            if not m:
                raise SyntaxError(f"Invalid Default: {line}")
            target = m.group(1)
            steps[current_step]["actions"].append(("Default", target))
            continue
            
        raise SyntaxError(f"Unknown line: {line}")
    
    return {"module": module, "steps": steps}