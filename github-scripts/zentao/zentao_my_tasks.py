import requests
import json
import warnings
warnings.filterwarnings("ignore")

base_url = "https://zentao.tbitiot.com/zentao"
token = "1d3ff2769178390361c4ba843a4b86c6"
headers = {"Token": token, "Content-Type": "application/json"}

def get(path, params=None):
    r = requests.get(f"{base_url}/api.php/v1{path}", headers=headers, params=params, verify=False, timeout=15)
    try:
        return r.json()
    except:
        return {}

# 获取所有测试版本（多页）
all_testtasks = []
for page in range(1, 5):
    d = get("/testtasks", {"page": page, "limit": 50})
    tasks = d.get("testtasks", [])
    if not tasks:
        break
    all_testtasks.extend(tasks)
    total = d.get("total", 0)
    if len(all_testtasks) >= total:
        break

print(f"共获取 {len(all_testtasks)} 个测试版本")

# 只保留雷投参与的
my_tasks = []
for t in all_testtasks:
    owner = t.get("owner", {})
    members = t.get("members", "")
    owner_name = owner.get("realname", "") if owner else ""
    if "雷投" in members or owner_name == "雷投":
        my_tasks.append(t)

print(f"雷投参与的测试版本: {len(my_tasks)} 个")

# 按状态分组
status_groups = {}
for t in my_tasks:
    s = t.get("status", "未知")
    if s not in status_groups:
        status_groups[s] = []
    status_groups[s].append(t)

print()
for status, tasks in sorted(status_groups.items()):
    print(f"【{status}】{len(tasks)}个")
    for t in tasks:
        owner = t.get("owner", {})
        owner_name = owner.get("realname", "") if owner else ""
        is_owner = " (我负责)" if owner_name == "雷投" else ""
        print(f"  [{t['id']}] {t['name']}{is_owner}")
        print(f"       产品:{t.get('productName','')}  项目:{t.get('projectName','')}  {t.get('begin','')}~{t.get('end','')}")

# 保存
with open("D:/110/zentao_my_tasks.json", "w", encoding="utf-8") as f:
    json.dump(my_tasks, f, ensure_ascii=False, indent=2)
print(f"\n已保存到 D:/110/zentao_my_tasks.json")

# 近期未完成的
print()
print("=" * 60)
print("【进行中 / 未开始 的测试版本（雷投）】")
print("=" * 60)
active = [t for t in my_tasks if t.get("status") in ["进行中", "未开始"]]
for t in active:
    owner = t.get("owner", {})
    owner_name = owner.get("realname", "") if owner else ""
    is_owner = " 【我负责】" if owner_name == "雷投" else ""
    print(f"  [{t['id']}] {t['name']}{is_owner}")
    print(f"       产品:{t.get('productName','')} | 时间:{t.get('begin','')}~{t.get('end','')}")
