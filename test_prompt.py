import subprocess
import time

# 创建一个临时文件来保存输出
with open('prompt_test_output.txt', 'w', encoding='utf-8') as f:
    # 启动交互式终端
    p = subprocess.Popen(
        ['python', 'python_terminal.py'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # 等待一段时间让终端初始化并显示提示符
    time.sleep(2)
    
    # 终止进程
    p.terminate()
    
    # 尝试获取输出
    try:
        out, err = p.communicate(timeout=1)
        f.write("STDOUT:\n")
        f.write(out)
        f.write("\n\nSTDERR:\n")
        f.write(err)
        print("测试输出已保存到 prompt_test_output.txt")
    except Exception as e:
        f.write(f"错误: {e}")
        print(f"发生错误: {e}")

# 读取并显示结果
try:
    with open('prompt_test_output.txt', 'r', encoding='utf-8') as f:
        content = f.read()
        print("\n测试结果:")
        print(content)
except Exception as e:
    print(f"无法读取输出文件: {e}")