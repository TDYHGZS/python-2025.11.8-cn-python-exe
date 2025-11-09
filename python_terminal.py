import os
import sys
import subprocess
import platform
import shlex
import argparse
import datetime
import time
import stat
import json
import pathlib
import configparser
from typing import List, Dict, Any, Optional, Callable

# 尝试自动安装并导入readline或pyreadline3模块
def try_install_readline(should_restart=True):
    """尝试自动安装readline或pyreadline3模块，并在安装成功后自动重启程序"""
    import subprocess
    import sys
    
    print("尝试自动安装readline或pyreadline3模块...")
    
    try:
        # 根据平台选择安装的包
        if platform.system() == "Windows":
            # Windows上安装pyreadline3
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyreadline3"])
            print("已成功安装pyreadline3模块。")
            
            # 如果需要重启且在Windows系统上
            if should_restart and platform.system() == "Windows":
                print("正在重启程序以应用模块...")
                # 使用sys.executable重新运行当前脚本
                os.execv(sys.executable, [sys.executable] + sys.argv)
            
            return True
        else:
            # Linux/macOS上安装readline
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "readline"])
                print("已成功安装readline模块。")
                
                # 如果需要重启
                if should_restart:
                    print("正在重启程序以应用模块...")
                    os.execv(sys.executable, [sys.executable] + sys.argv)
                
                return True
            except subprocess.CalledProcessError:
                # 有些Linux发行版需要系统包管理器安装libreadline-dev
                print("在Linux上安装readline可能需要先安装系统依赖。")
                print("Ubuntu/Debian: sudo apt-get install libreadline-dev")
                print("CentOS/RHEL: sudo yum install readline-devel")
                return False
    except Exception as e:
        print(f"安装模块时出错: {e}")
        return False

# 尝试导入readline或pyreadline3，失败则尝试自动安装
READLINE_AVAILABLE = False
try:
    import readline
    READLINE_AVAILABLE = True
except ImportError:
    try:
        # Windows系统上的替代方案
        import pyreadline3 as readline
        READLINE_AVAILABLE = True
    except ImportError:
        # 检查是否已经尝试过安装（通过环境变量标记）
        if os.environ.get('PYTERMINAL_MODULE_INSTALLED') != '1':
            # 设置环境变量标记已经尝试安装
            os.environ['PYTERMINAL_MODULE_INSTALLED'] = '1'
            
            # 尝试自动安装（会在安装成功后自动重启）
            try_install_readline(should_restart=True)
        else:
            # 已经尝试过安装但仍然失败
            READLINE_AVAILABLE = False
            print("警告: 未找到readline或pyreadline3模块，命令历史和补全功能将不可用。")
            print("您可以手动安装: pip install pyreadline3 (Windows) 或 pip install readline (Linux/macOS)")
            print("安装完成后，请重新启动程序。")

# 命令注册器（插件化架构核心）
COMMAND_REGISTRY = {}

def register_command(cmd_name: str, handler=None) -> Callable:
    """装饰器：注册命令处理器"""
    # 如果handler为None，这是作为装饰器使用的情况
    if handler is None:
        def decorator(func):
            COMMAND_REGISTRY[cmd_name.lower()] = func
            return func
        return decorator
    # 否则直接注册handler
    COMMAND_REGISTRY[cmd_name.lower()] = handler
    return handler

# 获取配置文件路径（跨平台）
def get_config_path() -> str:
    """获取配置文件的正确路径（跨平台）"""
    if platform.system() == "Windows":
        return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming")), 
                           "PyTerminal", "config.ini")
    else:
        return os.path.join(os.path.expanduser("~"), ".pyterminal_config.ini")

# 获取历史记录文件路径（跨平台）
def get_history_path() -> str:
    """获取历史记录文件的正确路径（跨平台）"""
    if platform.system() == "Windows":
        return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming")), 
                           "PyTerminal", "command_history.txt")
    else:
        return os.path.join(os.path.expanduser("~"), ".python_terminal_history")

# 默认配置
DEFAULT_CONFIG = {
    'prompt': 'PS %dir%> ',  # PowerShell风格提示符
    'cmd_timeout': 15,  # 命令超时时间（秒）
    'save_history': True,  # 是否保存命令历史
    'high_risk_commands': ['rm -rf /', 'format c:', 'del *.* /q'],  # 高危命令列表
    'max_history_size': 1000  # 最大历史记录数
}

# 配置数据
config = DEFAULT_CONFIG.copy()
# 命令历史记录
command_history = []
# 配置文件路径
CONFIG_FILE = get_config_path()
# 历史记录文件路径
HISTORY_FILE = get_history_path()

# 高危命令检查
def is_high_risk_command(cmd: str) -> bool:
    """检查是否为高危命令"""
    cmd_lower = cmd.lower().strip()
    # 内置高危命令模式
    high_risk_patterns = [
        # Linux/macOS高危命令
        "rm -rf", "rm -r *", "sudo rm", "dd if=", "mkfs.",
        # Windows高危命令
        "del *", "rd /s /q", "format ", "rmdir /s /q",
        # 其他危险操作
        ">:"  # 防止重定向覆盖重要文件
    ]
    
    # 检查内置模式
    if any(pattern in cmd_lower for pattern in high_risk_patterns):
        return True
    
    # 检查配置文件中的自定义高危命令
    for risk_cmd in config.get('high_risk_commands', []):
        if risk_cmd.lower() in cmd_lower:
            return True
    return False

# 获取文件大小的易读格式
def get_readable_size(size_bytes: int) -> str:
    """将字节大小转换为人类可读格式"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

# 清屏功能
def clear_screen():
    """清屏功能"""
    if platform.system() == 'Windows':
        os.system('cls')
    else:
        os.system('clear')

# 显示帮助信息
def display_help():
    """显示帮助信息"""
    help_text = """

主题
python cn 2025.11.8 帮助系统

简短说明
显示有关 python cn 2025.11.8 的命令及概念的帮助。

详细说明
    "python cn 2025.11.8 帮助"介绍了本终端的内置命令、
    功能特性、配置选项，并解释了
    常用操作的使用方法等概念。

    可用命令:
      cd <目录>     - 切换目录
      pwd           - 显示当前路径
      dir           - 列出当前目录内容（增强版）
      mkdir <目录>  - 创建新目录
      rm <文件/目录> - 删除文件或目录
      cls/clear     - 清屏
      exit/quit     - 退出终端
      help          - 显示此帮助信息
      其他命令将作为系统命令执行

    功能特性:
      - 命令历史记录（上下箭头键调用）
      - 命令补全（Tab键）
      - PowerShell风格提示符
      - 命令超时控制
      - 高危命令保护

    配置选项:
      通过配置文件来自定义设置

联机帮助
    你可以在微软网站上找到有关 PowerShell 的联机帮助，
网址为 `http://go.microsoft.com/fwlink/?LinkID=108518`。

    若要了解更多 PowerShell 相关知识，请访问：
    `https://aka.ms/pscore6`

-- 按 Enter 键继续 --
"""
    print(help_text)
    # 只有在交互式模式下才等待用户按Enter键继续
    if ARGS is None or not (ARGS.command or ARGS.quiet):
        input()

# 执行命令
def execute_command(cmd: str):
    """执行命令，支持超时控制和高危命令检查"""
    # 检查高危命令
    if is_high_risk_command(cmd):
        confirm = input(f"⚠️  检测到高危命令：'{cmd}'，执行后可能导致数据丢失或系统损害，确认继续？(y/N) ")
        if confirm.lower() != 'y':
            print("命令已取消执行")
            return
    
    try:
        timeout = config.get('cmd_timeout', 15)  # 从配置中读取超时时间
        # 在Windows上使用shell=True以支持内部命令
        if platform.system() == 'Windows':
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        else:
            # 在Unix系统上使用shlex.split来正确处理参数
            try:
                cmd_parts = shlex.split(cmd)
                result = subprocess.run(cmd_parts, capture_output=True, text=True, timeout=timeout)
            except ValueError:
                # 如果shlex.split失败（可能是特殊字符问题），尝试直接执行
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
            
    except subprocess.TimeoutExpired:
        print(f"错误: 命令 '{cmd}' 执行超时（已超过{timeout}秒），可能是无限循环命令，请检查参数", file=sys.stderr)
    except PermissionError:
        print(f"错误: 权限不足，无法执行命令 '{cmd}'（请尝试以管理员/root身份运行）", file=sys.stderr)
    except FileNotFoundError:
        print(f"错误: 命令 '{cmd}' 未找到（检查命令是否拼写正确或已安装）", file=sys.stderr)
    except OSError as e:
        print(f"系统错误: {e.strerror}（执行'{cmd}'时发生）", file=sys.stderr)
    except Exception as e:
        print(f"执行命令时出错: {str(e)}（详细错误信息）", file=sys.stderr)
    """执行命令，支持超时控制和高危命令检查"""
    # 检查高危命令
    if is_high_risk_command(cmd):
        confirm = input(f"⚠️  检测到高危命令：'{cmd}'，执行后可能导致数据丢失或系统损害，确认继续？(y/N) ")
        if confirm.lower() != 'y':
            print("命令已取消执行")
            return
    
    try:
        timeout = config.get('command_timeout', 15)  # 增加默认超时时间到15秒
        # 在Windows上使用shell=True以支持内部命令
        if platform.system() == 'Windows':
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        else:
            # 在Unix系统上使用shlex.split来正确处理参数
            try:
                cmd_parts = shlex.split(cmd)
                result = subprocess.run(cmd_parts, capture_output=True, text=True, timeout=timeout)
            except ValueError:
                # 如果shlex.split失败（可能是特殊字符问题），尝试直接执行
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
            
    except subprocess.TimeoutExpired:
        print(f"错误: 命令 '{cmd}' 执行超时（已超过{timeout}秒），可能是无限循环命令，请检查参数", file=sys.stderr)
    except PermissionError:
        print(f"错误: 权限不足，无法执行命令 '{cmd}'（请尝试以管理员/root身份运行）", file=sys.stderr)
    except FileNotFoundError:
        print(f"错误: 命令 '{cmd}' 未找到（检查命令是否拼写正确或已安装）", file=sys.stderr)
    except OSError as e:
        print(f"系统错误: {e.strerror}（执行'{cmd}'时发生）", file=sys.stderr)
    except Exception as e:
        print(f"执行命令时出错: {str(e)}（详细错误信息）", file=sys.stderr)

# 增强版目录列表功能
def enhanced_dir(args=""):
    """增强版dir命令，跨平台显示详细信息"""
    try:
        if platform.system() == "Windows":
            # Windows下调用系统dir命令，带参数显示详细信息
            cmd = f"dir {args} /A /W" if args else "dir /A /W"  # /A显示所有文件，/W宽格式
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        else:  # macOS/Linux
            # Unix下用ls -l，显示权限、所有者、大小、时间
            cmd = f"ls -la {args}" if args else "ls -la"
            cmd_parts = shlex.split(cmd)
            result = subprocess.run(cmd_parts, capture_output=True, text=True)
        
        # 打印结果
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
    except Exception as e:
        # 如果系统命令失败，回退到Python实现
        try:
            items = os.listdir('.')
            # 分离目录和文件
            dirs = []
            files = []
            
            for item in items:
                try:
                    stat_info = os.stat(item)
                    # 获取修改时间
                    mtime = datetime.datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    
                    # 获取文件权限信息（跨平台）
                    if platform.system() == "Windows":
                        # Windows简单权限标识
                        if os.access(item, os.W_OK):
                            perm = "RW"
                        elif os.access(item, os.R_OK):
                            perm = "R-"
                        else:
                            perm = "--"
                    else:
                        # Unix权限字符串
                        perm = ''.join([
                            'd' if os.path.isdir(item) else '-',
                            'r' if stat.S_IRUSR & stat_info.st_mode else '-',
                            'w' if stat.S_IWUSR & stat_info.st_mode else '-',
                            'x' if stat.S_IXUSR & stat_info.st_mode else '-',
                            'r' if stat.S_IRGRP & stat_info.st_mode else '-',
                            'w' if stat.S_IWGRP & stat_info.st_mode else '-',
                            'x' if stat.S_IXGRP & stat_info.st_mode else '-',
                            'r' if stat.S_IROTH & stat_info.st_mode else '-',
                            'w' if stat.S_IWOTH & stat_info.st_mode else '-',
                            'x' if stat.S_IXOTH & stat_info.st_mode else '-'
                        ])
                    
                    if os.path.isdir(item):
                        dirs.append((item, mtime, 'DIR', 0, perm))
                    else:
                        files.append((item, mtime, 'FILE', stat_info.st_size, perm))
                except Exception:
                    # 如果无法获取文件信息，仍然显示
                    if os.path.isdir(item):
                        dirs.append((item, 'N/A', 'DIR', 0, '--'))
                    else:
                        files.append((item, 'N/A', 'FILE', 0, '--'))
            
            # 按名称排序
            dirs.sort(key=lambda x: x[0].lower())
            files.sort(key=lambda x: x[0].lower())
            
            # 打印结果（增加权限列）
            print("\n目录:")
            print(f"{'权限':<10} {'修改时间':<20} {'名称':<40}")
            print("-" * 70)
            for item, mtime, type_, _, perm in dirs:
                print(f"{perm:<10} {mtime:<20} {item:<40}")
            
            print("\n文件:")
            print(f"{'权限':<10} {'修改时间':<20} {'大小':<10} {'名称':<40}")
            print("-" * 80)
            for item, mtime, type_, size, perm in files:
                print(f"{perm:<10} {mtime:<20} {get_readable_size(size):<10} {item:<40}")
            
            print(f"\n总计: {len(dirs)} 个目录, {len(files)} 个文件")
        except Exception as fallback_error:
            print(f"列出目录失败：{str(fallback_error)}（系统命令和Python实现均失败）", file=sys.stderr)

# 加载配置
def load_config():
    """加载配置文件（优先用户配置，其次默认配置）"""
    global config
    try:
        config_path = get_config_path()
        
        # 检查配置文件是否存在
        if os.path.exists(config_path):
            try:
                # 尝试以JSON格式读取配置文件
                with open(config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                
                # 合并配置（用户配置覆盖默认）
                for key, value in DEFAULT_CONFIG.items():
                    if key in user_config:
                        config[key] = user_config[key]
            except json.JSONDecodeError:
                # 如果不是有效的JSON，尝试使用configparser读取（向后兼容）
                try:
                    parser = configparser.ConfigParser()
                    parser.read(config_path)
                    if 'terminal' in parser.sections():
                        for key, value in DEFAULT_CONFIG.items():
                            if key in parser['terminal']:
                                if key == 'cmd_timeout' or key == 'max_history_size':
                                    config[key] = parser.getint('terminal', key)
                                elif key == 'save_history':
                                    config[key] = parser.getboolean('terminal', key)
                                elif key == 'high_risk_commands':
                                    commands_str = parser.get('terminal', key, fallback='')
                                    config[key] = [cmd.strip() for cmd in commands_str.split(';') if cmd.strip()]
                                else:
                                    config[key] = parser.get('terminal', key, fallback=value)
                    else:
                        # 配置文件存在但格式不对，使用默认配置并重新生成
                        generate_default_config(config_path)
                except Exception:
                    # 如果两种方式都失败，重新生成配置文件
                    print(f"警告: 配置文件格式错误，重新生成默认配置。", file=sys.stderr)
                    generate_default_config(config_path)
        else:
            # 首次运行，生成默认配置文件
            generate_default_config(config_path)
            
    except Exception as e:
        print(f"警告: 加载配置文件失败: {e}，使用默认配置。", file=sys.stderr)

def generate_default_config(config_path: str):
    """生成默认配置文件（使用JSON格式）"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # 使用JSON格式保存配置
        config_data = DEFAULT_CONFIG.copy()
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        
        print(f"默认配置文件已创建: {config_path}")
        print("您可以编辑此文件来自定义终端设置。")
    except Exception as e:
        print(f"生成默认配置文件失败: {e}", file=sys.stderr)

# 保存配置
def save_config(config_data=None, config_path=None):
    """保存配置到文件（使用JSON格式）"""
    # 如果没有提供配置，使用当前全局配置
    if config_data is None:
        config_data = config
    # 如果没有提供路径，使用默认配置路径
    if config_path is None:
        config_path = get_config_path()
    
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # 使用JSON格式保存配置
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"保存配置文件失败: {e}", file=sys.stderr)
        return False
    
    if config_path is None:
        config_path = CONFIG_FILE
    
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # 保存配置
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
        
        print(f"配置已保存到: {config_path}")
        return True
    except Exception as e:
        print(f"警告: 保存配置文件失败: {e}", file=sys.stderr)
        return False

# 命令补全功能（仅在readline可用时使用）
if READLINE_AVAILABLE:
    def command_completer(text: str, state: int) -> Optional[str]:
        """命令补全函数"""
        # 内置命令列表
        commands = ['cd', 'pwd', 'dir', 'mkdir', 'rm', 'cls', 'clear', 'exit', 'quit', 'help']
        
        # 获取当前目录下的文件和目录
        try:
            current_dir = os.getcwd()
            items = os.listdir(current_dir)
            # 如果text包含路径分隔符，获取路径部分
            if os.sep in text or '/' in text:
                # 统一路径分隔符
                text = text.replace('/', os.sep)
                # 获取基本路径和文件名部分
                base_dir = os.path.dirname(text)
                if not base_dir:
                    base_dir = '.'
                # 确保路径是绝对路径
                if not os.path.isabs(base_dir):
                    base_dir = os.path.join(current_dir, base_dir)
                # 获取文件名前缀
                prefix = os.path.basename(text)
                # 获取目录下的所有项
                try:
                    dir_items = os.listdir(base_dir)
                    # 过滤出匹配前缀的项
                    matches = [os.path.join(base_dir, item) for item in dir_items if item.startswith(prefix)]
                    # 转换为相对路径
                    matches = [os.path.relpath(item, current_dir) for item in matches]
                    # 如果只有一个匹配项且是目录，添加路径分隔符
                    if len(matches) == 1 and os.path.isdir(matches[0]):
                        matches[0] += os.sep
                    # 返回第state个匹配项
                    if state < len(matches):
                        return matches[state]
                except Exception:
                    pass
            else:
                # 补全命令
                matches = [cmd for cmd in commands if cmd.startswith(text)]
                # 如果没有命令匹配，尝试补全文件/目录名
                if not matches:
                    matches = [item for item in items if item.startswith(text)]
                    # 如果只有一个匹配项且是目录，添加路径分隔符
                    if len(matches) == 1 and os.path.isdir(matches[0]):
                        matches[0] += os.sep
                # 返回第state个匹配项
                if state < len(matches):
                    return matches[state]
        except Exception:
            pass
        
        return None

# 加载命令历史（仅在readline可用时使用）
if READLINE_AVAILABLE:
    def load_history():
        """从历史文件加载命令历史"""
        try:
            if os.path.exists(HISTORY_FILE):
                readline.read_history_file(HISTORY_FILE)
                # 设置最大历史记录数
                readline.set_history_length(config.get('max_history_size', 1000))
        except Exception as e:
            print(f"警告: 加载历史记录失败: {e}", file=sys.stderr)

# 保存命令历史（仅在readline可用时使用）
if READLINE_AVAILABLE:
    def save_history():
        """保存命令历史到文件"""
        try:
            readline.write_history_file(HISTORY_FILE)
        except Exception as e:
            print(f"警告: 保存历史记录失败: {e}", file=sys.stderr)

# 处理cd命令
def handle_cd(command):
    new_dir = command[3:].strip() or os.path.expanduser("~")  # 无参数切主目录
    try:
        # 处理特殊字符（引号包围的路径）
        if (new_dir.startswith('"') and new_dir.endswith('"')) or \
           (new_dir.startswith("'") and new_dir.endswith("'")):
            new_dir = new_dir[1:-1]
        os.chdir(new_dir)
    except FileNotFoundError:
        print(f"错误：目录 '{new_dir}' 不存在（请检查路径是否正确，注意空格和大小写）", file=sys.stderr)
    except PermissionError:
        print(f"错误：无权限访问目录 '{new_dir}'（请以管理员/root身份运行终端）", file=sys.stderr)
    except NotADirectoryError:
        print(f"错误：'{new_dir}' 不是一个目录（请确认目标是文件夹而非文件）", file=sys.stderr)
    except Exception as e:
        print(f"切换目录失败：{str(e)}（其他错误，请检查路径格式是否正确）", file=sys.stderr)
    return True

# 处理dir命令
def handle_dir(command):
    """优化dir命令：跨平台显示详细信息"""
    # 提取参数（如dir *.txt，支持通配符）
    args = command[4:].strip()
    enhanced_dir(args)
    return True

# 处理mkdir命令（创建目录）
def handle_mkdir(command):
    try:
        dir_name = command[6:].strip()
        if not dir_name:
            print("错误：请指定要创建的目录名（示例：mkdir test_dir）")
            return True
        # 处理特殊字符
        if (dir_name.startswith('"') and dir_name.endswith('"')) or \
           (dir_name.startswith("'") and dir_name.endswith("'")):
            dir_name = dir_name[1:-1]
        os.makedirs(dir_name, exist_ok=True)  # exist_ok=True避免"目录已存在"报错
        print(f"目录 '{dir_name}' 创建成功（若已存在则忽略）")
    except PermissionError:
        print(f"错误：权限不足，无法创建目录 '{dir_name}'")
    except Exception as e:
        print(f"创建目录失败：{e}")
    return True

# 处理rm命令（删除文件/目录，需区分系统适配）
# 全局变量存储命令行参数
ARGS = None
def handle_rm(command, auto_confirm=False):
    import shutil
    target = command[3:].strip()
    if not target:
        print("错误：请指定要删除的文件/目录（示例：rm test.txt 或 rm -r test_dir）", file=sys.stderr)
        return True
    
    # 检查是否为高危命令（例如 rm -rf, rm -r *）
    full_command = command.lower()
    if "-rf" in full_command or "-r *" in full_command or \
       "rd /s" in full_command or "rmdir /s" in full_command:
        # 触发高危命令二次确认，即使auto_confirm为True也需要确认
        confirm = 'y' if auto_confirm or (ARGS and ARGS.yes) else input(f"⚠️  检测到高危删除命令：'{command}'，执行后数据将无法恢复，确认继续？(y/N) ")
        if confirm.lower() != 'y':
            print("删除命令已取消")
            return True
    
    # 处理目录删除（需带-r参数，模仿Unix逻辑，Windows下兼容）
    is_dir = os.path.isdir(target) or "-r" in command
    if is_dir:
        target = target.replace("-r", "").strip()  # 移除-r参数，提取目录名
        if not os.path.exists(target):
            print(f"错误：目录 '{target}' 不存在（请检查路径是否正确，注意大小写）", file=sys.stderr)
            return True
        # 高危操作二次确认（PC端防误删关键）
        if auto_confirm or (ARGS and ARGS.yes):
            confirm = 'y'
            print(f"自动确认删除: '{target}'")
        else:
            confirm = input(f"警告：将永久删除目录 '{target}' 及所有内容，确认？(y/n) ")
        if confirm.lower() != "y":
            print("删除操作已取消")
            return True
        try:
            shutil.rmtree(target)
            print(f"目录 '{target}' 删除成功")
        except PermissionError:
            print(f"错误：权限不足，无法删除目录 '{target}'（请以管理员/root身份运行）", file=sys.stderr)
        except Exception as e:
            print(f"删除目录失败：{str(e)}（可能是文件被占用或其他系统限制）", file=sys.stderr)
    else:
        if not os.path.isfile(target):
            print(f"错误：文件 '{target}' 不存在（请检查路径是否正确，注意大小写）", file=sys.stderr)
            return True
        # 二次确认
        if auto_confirm or (ARGS and ARGS.yes):
            confirm = 'y'
            print(f"自动确认删除: '{target}'")
        else:
            confirm = input(f"确认删除文件 '{target}'？(y/n) ")
        if confirm.lower() != "y":
            print("删除操作已取消")
            return True
        try:
            os.remove(target)
            print(f"文件 '{target}' 删除成功")
        except PermissionError:
            print(f"错误：权限不足，无法删除文件 '{target}'（请以管理员/root身份运行）", file=sys.stderr)
        except Exception as e:
            print(f"删除文件失败：{str(e)}（可能是文件被占用或其他系统限制）", file=sys.stderr)
    return True

# 处理cp命令（复制文件，跨平台适配）
def handle_cp(command):
    import shutil
    parts = command.split(maxsplit=2)  # 支持目标路径含空格（如cp a.txt "我的文档"）
    if len(parts) < 3:
        print("错误：请指定源文件和目标路径（示例：cp test.txt ./backup/）")
        return True
    src, dst = parts[1], parts[2]
    # 处理特殊字符（引号包围的路径）
    if (src.startswith('"') and src.endswith('"')) or \
       (src.startswith("'") and src.endswith("'")):
        src = src[1:-1]
    if (dst.startswith('"') and dst.endswith('"')) or \
       (dst.startswith("'") and dst.endswith("'")):
        dst = dst[1:-1]
    
    if not os.path.isfile(src):
        print(f"错误：源文件 '{src}' 不存在")
        return True
    # 处理目标路径为目录的情况（自动拼接文件名）
    if os.path.isdir(dst):
        dst = os.path.join(dst, os.path.basename(src))
    try:
        shutil.copy2(src, dst)  # copy2保留文件元信息（修改时间等，比copy更实用）
        print(f"文件从 '{src}' 复制到 '{dst}' 成功")
    except PermissionError:
        print(f"错误：权限不足，无法复制文件")
    except Exception as e:
        print(f"复制文件失败：{e}")
    return True

# 处理单个命令

# 重新实现命令注册
# 清空注册表
COMMAND_REGISTRY.clear()

# 直接注册命令
# 模拟Kali Linux工具的处理函数
def handle_kali_tool(command):
    """处理模拟的Kali Linux工具命令"""
    tool_name = command.split()[0] if command else ''
    
    # 基础信息字典，包含常用Kali工具的描述
    kali_tools = {
        'nmap': "Nmap - 网络扫描和安全评估工具\n\n用途: 扫描网络、检测开放端口、识别运行的服务和操作系统\n\n示例: nmap -sV 192.168.1.1\n",
        'metasploit': "Metasploit Framework - 渗透测试和漏洞利用平台\n\n用途: 执行渗透测试、利用漏洞、管理会话\n\n示例: 启动msfconsole并使用search命令查找漏洞\n",
        'burpsuite': "Burp Suite - Web应用程序安全测试工具\n\n用途: 拦截代理、扫描漏洞、测试Web应用安全\n\n示例: 配置浏览器代理并访问目标网站\n",
        'wireshark': "Wireshark - 网络协议分析器\n\n用途: 捕获和分析网络流量、检查数据包内容\n\n示例: 启动后选择网络接口开始捕获\n",
        'john': "John the Ripper - 密码破解工具\n\n用途: 破解各种加密的密码哈希\n\n示例: john --wordlist=rockyou.txt hashes.txt\n",
        'aircrack-ng': "Aircrack-ng - 无线网络安全工具套件\n\n用途: 破解WiFi密码、监控网络、捕获数据包\n\n示例: aircrack-ng -w wordlist.txt capture.cap\n",
        'sqlmap': "SQLMap - SQL注入漏洞检测和利用工具\n\n用途: 自动检测和利用SQL注入漏洞\n\n示例: sqlmap -u 'http://example.com/vulnerable.php?id=1'\n",
        'hydra': "Hydra - 在线密码破解工具\n\n用途: 对各种服务执行暴力破解攻击\n\n示例: hydra -l admin -P passlist.txt ssh://192.168.1.1\n",
        'nikto': "Nikto - Web服务器漏洞扫描器\n\n用途: 扫描Web服务器的各种安全问题\n\n示例: nikto -h http://example.com\n",
        'gobuster': "Gobuster - 目录和文件暴力破解工具\n\n用途: 发现隐藏的目录、文件和子域名\n\n示例: gobuster dir -u http://example.com -w /usr/share/wordlists/dirb/common.txt\n"
    }
    
    # 处理kali_tools命令，显示所有可用工具
    if tool_name == 'kali_tools':
        print("=== 可用的Kali Linux工具模拟 ===\n")
        for tool in sorted(kali_tools.keys()):
            print(f"  - {tool}")
        print("\n输入工具名称获取详细信息，例如: nmap")
        return True
    
    # 如果是已知的Kali工具，显示信息
    if tool_name in kali_tools:
        print(kali_tools[tool_name])
        print("注意: 这是工具的模拟版本，实际功能需要安装完整的Kali Linux环境。")
        return True
    
    return False

def register_all_commands():
    """注册所有命令"""
    # 注册cd命令
    def cmd_cd(command):
        return handle_cd(command)
    COMMAND_REGISTRY["cd"] = cmd_cd
    
    # 注册dir命令
    def cmd_dir(command):
        return handle_dir(command)
    COMMAND_REGISTRY["dir"] = cmd_dir
    
    # 注册mkdir命令
    def cmd_mkdir(command):
        return handle_mkdir(command)
    COMMAND_REGISTRY["mkdir"] = cmd_mkdir
    
    # 注册rm命令
    def cmd_rm(command):
        return handle_rm(command, auto_confirm=False)
    COMMAND_REGISTRY["rm"] = cmd_rm
    
    # 注册cp命令
    def cmd_cp(command):
        return handle_cp(command)
    COMMAND_REGISTRY["cp"] = cmd_cp
    
    # 注册其他命令
    COMMAND_REGISTRY["exit"] = lambda _: False
    COMMAND_REGISTRY["quit"] = lambda _: False
    COMMAND_REGISTRY["help"] = lambda _: (display_help(), True)[1]
    COMMAND_REGISTRY["cls"] = lambda _: (clear_screen(), True)[1]
    COMMAND_REGISTRY["clear"] = lambda _: (clear_screen(), True)[1]
    COMMAND_REGISTRY["pwd"] = lambda _: (print(os.getcwd()), True)[1]
    
    # 注册Kali工具命令
    COMMAND_REGISTRY["kali_tools"] = handle_kali_tool
    COMMAND_REGISTRY["nmap"] = handle_kali_tool
    COMMAND_REGISTRY["metasploit"] = handle_kali_tool
    COMMAND_REGISTRY["burpsuite"] = handle_kali_tool
    COMMAND_REGISTRY["wireshark"] = handle_kali_tool
    COMMAND_REGISTRY["john"] = handle_kali_tool
    COMMAND_REGISTRY["aircrack-ng"] = handle_kali_tool
    COMMAND_REGISTRY["sqlmap"] = handle_kali_tool
    COMMAND_REGISTRY["hydra"] = handle_kali_tool
    COMMAND_REGISTRY["nikto"] = handle_kali_tool
    COMMAND_REGISTRY["gobuster"] = handle_kali_tool

# 调用注册函数
register_all_commands()

def process_single_command(command: str, auto_confirm: bool = False) -> bool:
    """处理单个命令（插件化架构）"""
    # 保存命令到历史记录（非空命令）
    if command.strip():
        command_history.append(command)
        # 避免重复的连续命令
        if len(command_history) > 1 and command_history[-1] == command_history[-2]:
            command_history.pop()
    
    # 获取命令名称（第一个词）
    cmd_parts = command.lower().strip().split()
    cmd_key = cmd_parts[0] if cmd_parts else ""
    
    # 处理退出命令
    if cmd_key in ["exit", "quit"]:
        # 保存历史记录
        if config.get('save_history', True):
            save_history()
        return False
    
    # 处理空命令
    if not cmd_key:
        return True
    
    # 从命令注册器中查找并执行命令（插件化核心）
    if cmd_key in COMMAND_REGISTRY:
        # 特殊处理rm命令，传递auto_confirm参数或使用全局ARGS中的yes选项
        if cmd_key == "rm":
            # 使用auto_confirm参数或全局ARGS中的yes选项
            final_auto_confirm = auto_confirm or (ARGS and ARGS.yes)
            return COMMAND_REGISTRY[cmd_key](command, final_auto_confirm)
        else:
            return COMMAND_REGISTRY[cmd_key](command)
    
    # 其他命令作为系统命令执行
    else:
        execute_command(command)
        return True

# 获取自定义提示符
def get_custom_prompt() -> str:
    """根据配置文件生成自定义提示符"""
    try:
        # 强制使用PowerShell风格提示符
        prompt_format = 'PS %dir%> '
        
        # 获取当前目录
        current_dir = os.getcwd()
        
        # Windows系统特殊处理 - 显示完整路径，不使用波浪号替换
        if platform.system() == "Windows":
            # 保持Windows的完整路径格式，例如: C:\Users\xxx
            pass
        else:
            # 非Windows系统特殊处理家目录
            home_dir = os.path.expanduser("~")
            if current_dir.startswith(home_dir):
                current_dir = current_dir.replace(home_dir, "~", 1)
            
            # 非Windows系统限制目录显示长度
            dir_parts = current_dir.split(os.sep)
            if len(dir_parts) > 2:
                current_dir = os.sep.join([".."] + dir_parts[-2:]) if len(dir_parts) > 3 else os.sep.join(dir_parts[-2:])
        
        # 替换变量
        formatted_prompt = prompt_format.replace("%dir%", current_dir)
        
        return formatted_prompt
    except Exception:
        # 如果出错，返回简单提示符作为后备
        try:
            return f"{os.getcwd()}> "
        except:
            return "> "


# 主函数
# Tab补全逻辑：补全目录和文件
def complete_path(text, state):
    """Tab补全逻辑：补全目录和文件"""
    # 获取当前目录下所有匹配text的项目
    matches = []
    try:
        for item in os.listdir(os.getcwd()):
            if item.startswith(text):
                # 若为目录，末尾加/（符合PC终端习惯）
                if os.path.isdir(os.path.join(os.getcwd(), item)):
                    item += "/"
                matches.append(item)
        return matches[state] if state < len(matches) else None
    except Exception:
        return None

# 命令补全函数（整合命令和路径补全）
def command_completer(text, state):
    """命令补全函数"""
    # 检查是否有空格，判断是在补全命令还是路径
    if ' ' in text:
        # 在补全路径
        command_part, path_part = text.rsplit(' ', 1)
        matches = []
        try:
            # 获取基础目录
            base_dir = os.path.dirname(path_part) if os.path.dirname(path_part) else '.'
            search_term = os.path.basename(path_part)
            
            # 遍历目录内容
            for item in os.listdir(base_dir):
                if item.startswith(search_term):
                    full_path = os.path.join(base_dir, item)
                    display_path = os.path.join(path_part, item)
                    # 处理空格
                    if ' ' in item:
                        display_path = f'"{display_path}"'
                    # 目录末尾加/（符合PC终端习惯）
                    if os.path.isdir(full_path):
                        display_path += "/"
                    matches.append(command_part + ' ' + display_path)
            return matches[state] if state < len(matches) else None
        except Exception:
            return None
    else:
        # 在补全命令
        commands = ['exit', 'quit', 'help', 'cls', 'clear', 'pwd', 'cd', 'dir', 'mkdir', 'rm', 'cp']
        matches = [cmd for cmd in commands if cmd.startswith(text)]
        return matches[state] if state < len(matches) else None

# 加载历史记录函数
def load_history():
    """加载命令历史记录"""
    global command_history
    
    # 初始化命令历史（保存到PC端默认路径，避免重启丢失）
    hist_path = ""
    if platform.system() == "Windows":
        hist_path = os.path.join(os.environ["APPDATA"], "PyTerminal", "cmd_history")
    else:  # macOS/Linux
        hist_path = os.path.join(os.environ["HOME"], ".pyterminal_cmd_history")
    
    # 创建历史文件目录（确保路径存在）
    try:
        os.makedirs(os.path.dirname(hist_path), exist_ok=True)
        
        # 从文件加载历史记录
        if os.path.exists(hist_path):
            with open(hist_path, 'r', encoding='utf-8') as f:
                command_history = [line.strip() for line in f.readlines()]
    except Exception as e:
        print(f"警告: 加载历史记录失败: {e}")

# 保存历史记录函数
def save_history():
    """保存命令历史记录"""
    # 获取历史文件路径
    hist_path = ""
    if platform.system() == "Windows":
        hist_path = os.path.join(os.environ["APPDATA"], "PyTerminal", "cmd_history")
    else:  # macOS/Linux
        hist_path = os.path.join(os.environ["HOME"], ".pyterminal_cmd_history")
    
    # 创建目录（如果不存在）
    try:
        os.makedirs(os.path.dirname(hist_path), exist_ok=True)
        
        # 保存历史记录到文件（限制条数，避免文件过大）
        with open(hist_path, 'w', encoding='utf-8') as f:
            # 保存最近500条命令
            for cmd in command_history[-500:]:
                f.write(f"{cmd}\n")
    except Exception as e:
        print(f"警告: 保存历史记录失败: {e}")

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='python cn 2025.11.8')
    parser.add_argument('-c', '--command', help='执行单个命令后退出')
    parser.add_argument('--prompt', help='自定义提示符样式')
    parser.add_argument('--yes', '-y', action='store_true', help='自动确认删除等操作')
    parser.add_argument('-q', '--quiet', action='store_true', help='安静模式，减少输出')
    parser.add_argument('--no-history', action='store_true', help='不保存命令历史')
    args = parser.parse_args()
    
    # 全局变量保存参数，供其他函数使用
    global ARGS
    ARGS = args
    
    # 注册命令（先注册再加载配置）
    register_all_commands()
    
    # 首次运行时生成默认配置文件（确保在任何模式下都会生成）
    if not os.path.exists(CONFIG_FILE):
        print("首次运行，生成默认配置文件...")
        # 确保目录存在并保存配置
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        save_config()
    
    # 加载配置
    load_config()
    
    # 加载历史记录
    load_history()
    
    # 注册命令补全函数（如果readline可用）
    if READLINE_AVAILABLE:
        try:
            readline.set_completer_delims(' \t\n;')
            readline.parse_and_bind("tab: complete")
            readline.set_completer(command_completer)
            
            # 初始化命令历史（保存到PC端默认路径，避免重启丢失）
            hist_path = ""
            if platform.system() == "Windows":
                hist_path = os.path.join(os.environ["APPDATA"], "PyTerminal", "cmd_history")
            else:  # macOS/Linux
                hist_path = os.path.join(os.environ["HOME"], ".pyterminal_cmd_history")
            
            # 创建历史文件目录（确保路径存在）
            os.makedirs(os.path.dirname(hist_path), exist_ok=True)
            
            # 加载历史记录（启动时读取过往命令）
            try:
                if os.path.exists(hist_path):
                    readline.read_history_file(hist_path)
            except FileNotFoundError:
                pass  # 首次运行无历史文件，忽略
            except Exception as e:
                print(f"警告: 无法加载命令历史: {e}")
        except Exception as e:
            print(f"警告: 无法设置命令补全或历史记录功能: {e}")
    else:
        print("提示: 命令历史和补全功能当前不可用。")
    
    # 如果指定了提示符样式，更新配置
    if args.prompt:
        config['prompt_style'] = args.prompt
        save_config()
    
    # 如果指定了命令，执行单个命令后退出
    if args.command:
        process_single_command(args.command, auto_confirm=args.yes)
        # 保存历史记录（尊重no-history参数和配置）
        if not args.no_history and config.get('save_history', True):
            save_history()
        return
    
    # 否则进入交互式模式
    if not args.quiet:
        print("版权所有 (C) python cn 2025.11.8。保留所有权利。")
        print()
        print("尝试新的跨平台 Python终端 `https://aka.ms/python-terminal`")
        print()
    
    try:
        while True:
            try:
                # 获取自定义提示符
                prompt = get_custom_prompt()
                
                # 获取用户输入
                command = input(prompt).strip()
                
                # 保存到命令历史（非空命令）
                if command and not args.no_history:
                    # 通过readline添加到历史（如果可用）
                    if READLINE_AVAILABLE:
                        readline.add_history(command)
                        # 实时保存历史到文件
                        try:
                            hist_path = ""
                            if platform.system() == "Windows":
                                hist_path = os.path.join(os.environ["APPDATA"], "PyTerminal", "cmd_history")
                            else:
                                hist_path = os.path.join(os.environ["HOME"], ".pyterminal_cmd_history")
                            readline.write_history_file(hist_path)
                        except Exception as e:
                            print(f"警告: 保存命令历史失败: {e}")
                
                # 处理命令，如果返回False则退出循环
                if not process_single_command(command):
                    print("再见！")
                    break
                    
            except KeyboardInterrupt:
                # 处理Ctrl+C
                print("\n输入 'exit' 或 'quit' 退出终端。")
                # 处理Ctrl+C时，保存历史
                if not args.no_history:
                    save_history()
            except EOFError:
                # 处理Ctrl+D
                print("\n再见！")
                break
            except Exception as e:
                print(f"发生错误: {e}", file=sys.stderr)
    finally:
        # 确保保存历史记录（尊重no-history参数和配置）
        if not args.no_history and config.get('save_history', True):
            save_history()


if __name__ == "__main__":
    main()