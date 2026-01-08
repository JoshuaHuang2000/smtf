#!/bin/bash

# 1. 进入项目目录 (请修改为你实际的绝对路径！)
cd /Users/jiaqihuang/smtf_project

# 2. 激活虚拟环境
source venv/bin/activate

# 3. 运行 Python (带上 --cron 参数)
# >> smtf.log 2>&1 表示把所有输出(包括报错)都记在日志文件里
python main.py --cron >> smtf.log 2>&1

# 4. 打印结束时间
echo "Run finished at $(date)" >> smtf.log