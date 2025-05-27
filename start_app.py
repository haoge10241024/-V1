#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
期货持仓分析系统启动脚本
"""

import subprocess
import sys
import os

def main():
    print("🚀 启动期货持仓分析系统...")
    
    # 确保在正确的目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # 检查优化版本文件是否存在
    optimized_file = "app_streamlit_optimized.py"
    if not os.path.exists(optimized_file):
        print(f"❌ 错误：找不到文件 {optimized_file}")
        return
    
    print(f"✅ 找到优化版本文件: {optimized_file}")
    
    # 设置环境变量跳过Streamlit欢迎界面
    env = os.environ.copy()
    env['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'
    
    try:
        # 启动Streamlit应用
        cmd = [sys.executable, "-m", "streamlit", "run", optimized_file, "--server.port", "8502"]
        print(f"🔄 执行命令: {' '.join(cmd)}")
        
        subprocess.run(cmd, env=env)
        
    except KeyboardInterrupt:
        print("\n👋 应用已停止")
    except Exception as e:
        print(f"❌ 启动失败: {str(e)}")

if __name__ == "__main__":
    main() 