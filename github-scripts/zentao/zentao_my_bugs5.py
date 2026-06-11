import requests
import json
import warnings
warnings.filterwarnings('ignore')

BASE = "https://zentao.tbitiot.com/zentao"

def get_token():
    r = requests.post(f"{BASE}/api.php/v1/tokens",
                      json={"account": "lei.tou", "password": "Aa17376460623.."},
                      verify=False, timeout=15)
    return r.json().get("token")

token = get_token()
headers = {"Token": token, "Content-Type": "application/json"}

def api_get(path, params=None):
    r = requests.get(f"{BASE}/api.php/v1/{path}", headers=headers,
                     params=params, verify=False, timeout=15)
    try:
        return r.json()
    except:
        return {}

def get_all_bugs(product_id):
    all_bugs = []
    page = 1
    while True:
        data = api_get(f"products/{product_id}/bugs", {
            "page": page, "limit": 100, "status": "all"
        })
        bugs = data.get("bugs", [])
        total = data.get("total", 0)
        if not bugs:
            break
        all_bugs.extend(bugs)
        if len(all_bugs) >= total:
            break
        page += 1
    return all_bugs

def get_my_account(b):
    ob = b.get("openedBy", "")
    if isinstance(ob, dict):
        return ob.get("account", "")
    return str(ob)

products = {
    47: "WD-300",
    61: "WD-110",
    120: "WD-110B",
}

result = {}
for pid, pname in products.items():
    bugs = get_all_bugs(pid)
    my_bugs = [b for b in bugs if get_my_account(b) == "lei.tou"]
    result[pname] = my_bugs

# WD-300 和 WD-110 合并分析
for pname, my_bugs in result.items():
    print(f"\n{'='*60}")
    print(f"【{pname}】我提交的Bug总数：{len(my_bugs)} 个")
    
    status_map = {
        "active": "未解决",
        "resolved": "已解决",
        "closed": "已关闭",
    }
    status_count = {}
    for b in my_bugs:
        st = b.get("status", "unknown")
        status_count[st] = status_count.get(st, 0) + 1
    print("  按状态统计：")
    for st, cnt in sorted(status_count.items(), key=lambda x: -x[1]):
        label = status_map.get(st, st)
        print(f"    {label}({st}): {cnt} 个")
    
    sev_count = {}
    for b in my_bugs:
        sv = b.get("severity", "?")
        sev_count[sv] = sev_count.get(sv, 0) + 1
    print("  按严重程度：")
    for sv in sorted(sev_count.keys()):
        print(f"    严重{sv}: {sev_count[sv]} 个")
    
    print(f"\n  -- 全部Bug列表（按ID倒序）--")
    for b in sorted(my_bugs, key=lambda x: -int(x.get("id", 0))):
        bid = b.get("id")
        title = b.get("title", "")
        status = b.get("status", "")
        sl = status_map.get(status, status)
        severity = b.get("severity", "")
        opened = b.get("openedDate", "")[:10] if b.get("openedDate") else ""
        resolution = b.get("resolution", "")
        res_label = f" [{resolution}]" if resolution else ""
        print(f"  [{bid}] [{sl}]{res_label} 严重{severity} {opened}  {title[:60]}")

# 汇总
total_300 = len(result.get("WD-300", []))
total_110 = len(result.get("WD-110", [])) + len(result.get("WD-110B", []))
print(f"\n{'='*60}")
print(f"最终汇总：")
print(f"  WD-300 项目：共 {total_300} 个Bug")
print(f"  WD-110 项目：共 {total_110} 个Bug（含WD-110B）")
print(f"  两个项目合计：{total_300 + total_110} 个")
