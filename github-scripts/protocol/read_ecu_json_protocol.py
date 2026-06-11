import json
import sys

# 设置输出编码
sys.stdout.reconfigure(encoding='utf-8')

# 读取协议文档
with open('D:/110/wiki_protocols.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 找到JSON版本的协议 (页面ID: 167804944)
protocol = data.get('167804944', {})

if protocol:
    print(f"标题: {protocol.get('title', 'N/A')}")
    print(f"字数: {len(protocol.get('content', ''))}")
    print('\n' + '='*80 + '\n')
    print(protocol.get('content', ''))
else:
    print("未找到协议文档")
