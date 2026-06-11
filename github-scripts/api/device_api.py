#!/usr/bin/env python3
"""
设备参数操作工具 - API 版本
基于 requests 直接调用后端 API
支持：登录、日志查询、参数查询、参数设置
"""

import requests
import json
import time
import sys
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, Tuple, List


@dataclass
class DeviceConfig:
    """设备配置"""
    base_url: str = "http://118.190.209.224:50044"
    device_id: str = "863499087071635"
    username: str = "tbit"
    password: str = "369852"


class DeviceAPI:
    """设备 API 客户端"""
    
    def __init__(self, config: DeviceConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': config.base_url,
            'Referer': f'{config.base_url}/',
        })
        
    def log(self, message: str):
        """打印日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        sys.stdout.flush()
    
    # ==================== 1. 登录 ====================
    def login(self) -> bool:
        """登录获取 Cookie"""
        try:
            self.log("正在登录...")
            login_url = f"{self.config.base_url}/account/login.do"
            data = {
                'userName': self.config.username,
                'userPsw': self.config.password
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Origin': self.config.base_url,
                'Referer': f'{self.config.base_url}/',
                'X-Requested-With': 'XMLHttpRequest',
            }
            response = self.session.post(login_url, data=data, headers=headers, timeout=10)
            result = response.json()
            
            if result.get('code') == 0 or result.get('code') == '0' or result.get('success'):
                self.log("登录成功")
                return True
            else:
                self.log(f"登录失败: {result}")
                return False
                
        except Exception as e:
            self.log(f"登录异常: {e}")
            return False
    
    # ==================== 2. 日志查询 ====================
    def query_logs(self, hours: int = 3) -> Tuple[bool, List[dict]]:
        """
        查询设备日志
        hours: 查询最近多少小时的日志
        返回: (成功/失败, 日志列表)
        """
        try:
            url = f"{self.config.base_url}/terpkg/queryHis.do"
            
            now = datetime.now()
            start = (now - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
            end = (now + timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')
            
            params = {'t': int(time.time() * 1000)}
            data = {
                'machineNO': self.config.device_id,
                'start': start,
                'end': end,
                'page': '0',
                'limit': '100'
            }
            
            response = self.session.post(url, params=params, data=data, timeout=10)
            result = response.json()
            
            rows = []
            if result.get('code') == 0 and 'data' in result:
                data_wrapper = result['data']
                if isinstance(data_wrapper, dict) and 'data' in data_wrapper:
                    rows = data_wrapper['data']
                elif isinstance(data_wrapper, list):
                    rows = data_wrapper
            
            self.log(f"查询到 {len(rows)} 条日志记录")
            return True, rows
                
        except Exception as e:
            self.log(f"查询日志异常: {e}")
            return False, []
    
    def print_logs(self, rows: List[dict]):
        """格式化打印日志"""
        if not rows:
            self.log("无日志数据")
            return
        
        print("\n" + "=" * 80)
        for i, log in enumerate(rows[:20], 1):  # 最多显示20条
            msg = log.get('msg', '')[:80]
            ex_msg = log.get('exMsg', '')[:60]
            time_str = log.get('createTime', log.get('receiveTime', '--'))
            print(f"  [{i}] {time_str}")
            print(f"      msg: {msg}")
            if ex_msg and ex_msg != msg:
                print(f"      exMsg: {ex_msg}")
            print()
        
        if len(rows) > 20:
            self.log(f"... 共 {len(rows)} 条，仅显示前 20 条")
        print("=" * 80 + "\n")
    
    # ==================== 3. 参数查询 ====================
    def query_params(self, param_name: str = None) -> Tuple[bool, dict]:
        """
        查询设备参数
        接口: POST tercontrol/queryParam.do (表单格式)
        返回的是日志列表，需要从报文/查询结果中提取参数值
        
        param_name: 要查的参数名，如 "gpsttff"。不传则查所有
        返回: (成功/失败, 参数字典)
        """
        import re
        
        try:
            self.log(f"正在查询设备参数... (param={param_name or '全部'})")
            url = f"{self.config.base_url}/tercontrol/queryParam.do"
            
            params_t = {'t': int(time.time() * 1000)}
            data = {
                'machineNO': self.config.device_id,
                'paramName': param_name or ''
            }
            
            response = self.session.post(url, params=params_t, data=data, timeout=15)
            result = response.json()
            
            # 解析响应：从日志数据的 查询结果={KEY=VALUE} 中提取参数
            out = {}
            raw_text = str(result)
            
            # 尝试从多个位置提取数据
            # 位置1: result.data 是日志列表
            logs_data = result.get('data', [])
            if isinstance(logs_data, list):
                for log_entry in logs_data:
                    if not isinstance(log_entry, dict):
                        continue
                    # 从 exMsg 或 msg 中找 查询结果={...}
                    for field in ['exMsg', 'msg', 'content', 'message']:
                        text = str(log_entry.get(field, ''))
                        # 匹配 查询结果={GPSTTFF=12082} 或类似模式
                        matches = re.findall(r'查询结果=\{([^}]+)\}', text)
                        for m in matches:
                            # 解析 key=value 对
                            for pair in m.split(','):
                                if '=' in pair:
                                    k, v = pair.split('=', 1)
                                    out[k.strip()] = v.strip()
                        # 也匹配直接出现的 KEY=VALUE（不带查询结果包裹）
                        if param_name:
                            direct_match = re.search(rf'{param_name}\s*=\s*(\S+)', text, re.IGNORECASE)
                            if direct_match:
                                out[param_name] = direct_match.group(1)
                    
                    # 也检查报文内容字段
                    content = str(log_entry.get('报文内容', log_entry.get('msg', '')))
                    if param_name:
                        dm = re.search(rf'{param_name}\s*=\s*(\d+)', content, re.IGNORECASE)
                        if dm:
                            out[param_name] = dm.group(1)

            # 位置2: 直接在原始响应文本中搜索
            if not out and param_name:
                all_matches = re.findall(rf'{param_name}\s*[:=]\s*(\S+)', raw_text, re.IGNORECASE)
                if all_matches:
                    out[param_name] = all_matches[0]

            # 位置3: result.data 本身就是简单值
            if not out and isinstance(result.get('data'), str):
                simple_val = result['data'].strip()
                if simple_val and len(simple_val) < 100:
                    out['raw'] = simple_val
            
            if out:
                self.log(f"查询到参数: {out}")
                return True, out
            else:
                # 返回原始响应用于调试
                self.log(f"未解析到参数值, 原始响应前200字: {raw_text[:200]}")
                return True, {'_raw_response': raw_text[:500]}
                
        except Exception as e:
            self.log(f"查询参数异常: {e}")
            return False, {}
    
    def print_params(self, params: dict):
        """格式化打印参数"""
        if not params:
            self.log("无参数数据")
            return
        
        print("\n" + "=" * 60)
        print(f"  设备编号: {self.config.device_id}")
        print(f"  参数数量: {len(params)}")
        print("=" * 60)
        
        for key, value in params.items():
            value_str = str(value)[:100]  # 截断过长值
            print(f"  {key:<30s} : {value_str}")
        
        print("=" * 60 + "\n")
    
    # ==================== 4. 参数设置 ====================
    def set_param(self, param_name: str, param_value: str) -> Tuple[bool, str]:
        """
        设置单个设备参数（远程设置）
        接口: POST setParam.do (表单格式)
        param_name: 参数名（如 reboot、DFTSLEEP、gpsTff）
        param_value: 参数值（如 0、1）
        返回: (成功/失败, 响应消息)
        """
        try:
            self.log(f"设置参数: {param_name} = {param_value}")
            
            # 实际接口: tercontrol/setParam.do，表单格式
            url = f"{self.config.base_url}/tercontrol/setParam.do"
            
            params = {'t': int(time.time() * 1000)}
            # paramKV 格式: key=value;
            data = {
                'machineNO': self.config.device_id,
                'paramKV': f'{param_name}={param_value};'
            }
            
            response = self.session.post(url, params=params, data=data, timeout=15)
            result = response.json()
            
            if result.get('code') == 0 or result.get('success') or result.get('result') == 'success':
                self.log(f"[OK] 设置成功: {param_name} = {param_value}")
                return True, result.get('message', result.get('msg', '设置成功'))
            else:
                msg = result.get('message', result.get('msg', result.get('codeStr', str(result))))
                self.log(f"[FAIL] 设置失败: {msg}")
                return False, msg
                
        except Exception as e:
            self.log(f"设置异常: {e}")
            return False, str(e)
    
    def set_params_batch(self, params: dict) -> List[Tuple[str, bool, str]]:
        """
        批量设置参数
        params: {参数名: 参数值} 字典
        返回: [(参数名, 成功/失败, 消息), ...]
        """
        results = []
        for name, value in params.items():
            ok, msg = self.set_param(name, str(value))
            results.append((name, ok, msg))
            time.sleep(0.5)  # 避免请求过快
        return results

    # ==================== 5. 实时消息轮询 (getmsg.do) ====================
    _msg_ver = 0  # 消息流水号

    def query_msg(self) -> Optional[dict]:
        """
        轮询实时消息 (usermsg/getmsg.do)
        参考 common_api.py 中的 query() 方法
        返回: 消息JSON 或 None
        """
        try:
            url = f"{self.config.base_url}/usermsg/getmsg.do"
            data = {'ver': str(self._msg_ver)}
            
            response = self.session.post(url, data=data, timeout=15)
            result = response.json()
            
            # 更新消息流水号
            if 'data' in result and 'ver' in result.get('data', {}):
                self._msg_ver = result['data']['ver']
            
            return result
            
        except Exception as e:
            self.log(f"查询消息异常: {e}")
            return None

    def check_online(self) -> bool:
        """
        轻量检测设备是否在线 (不下发任何有副作用的参数查询)
        只发 queryParam 空参数, 通过响应中是否包含"终端不在线"来判断
        返回: True=在线, False=离线
        """
        try:
            url = f"{self.config.base_url}/tercontrol/queryParam.do"
            data = {
                'machineNO': self.config.device_id,
                'paramName': ''  # 空参数名, 不触发现场设备查询
            }
            response = self.session.post(url, data=data, timeout=10)
            result = response.json()
            result_str = str(result)
            if "终端不在线" in result_str or "未登录" in result_str:
                return False
            return True
        except Exception as e:
            self.log(f"检测在线状态异常: {e}")
            return False

    def query_param_wait(self, param_name: str, timeout: int = 60) -> Tuple[Optional[dict], Optional[dict]]:
        """
        下发查询 + 等待设备回复 (参考 agps_280.py 的逻辑)

        流程:
          1. queryParam 下发查询指令
          2. 循环调用 getmsg.do 轮询, 从整个响应中搜索 param_name
          3. 匹配到则提取值返回

        注意: 不做flush! 避免时序竞争把设备回复吃掉。
              用全文本匹配 + serNO校验来确保拿到本次回复。
        返回: (结果字典, 原始响应) 或 (None, None)超时/错误
        """
        try:
            # Step 1: 下发查询指令
            self.log(f"正在查询设备参数... (param={param_name})")
            query_url = f"{self.config.base_url}/tercontrol/queryParam.do"
            data = {
                'machineNO': self.config.device_id,
                'paramName': param_name,
            }
            response = self.session.post(query_url, data=data, timeout=15)
            result = response.json()

            # 检查是否在线
            result_str = str(result)
            if "终端不在线" in result_str or "未登录" in result_str:
                self.log(f"设备不在线或未登录")
                return None, None

            # 获取 serNO (任务ID)
            ser_no = result.get('data', '')
            if not ser_no:
                self.log(f"下发查询失败: {result}")
                return None, None

            # Step 2: 循环等待回复 — 不flush! 直接开始轮询
            start_time = time.time()
            while True:
                time.sleep(1)

                msg_result = self.query_msg()
                if not msg_result:
                    continue

                # ★ 参考 agps_280.py: 在整个响应文本中搜索参数名
                response_text = str(msg_result)
                if param_name not in response_text and param_name.upper() not in response_text.upper():
                    # 不包含目标参数的消息, 跳过 (心跳/定位数据等无关消息)
                    continue

                # 包含目标参数了, 尝试从 tRsp 中提取精确值
                try:
                    tRsp_list = msg_result.get('data', {}).get('tRsp', [])
                    for item in tRsp_list:
                        if not isinstance(item, dict):
                            continue
                        param_ret = item.get('paramRet', '')
                        if param_ret and param_name.upper() in param_ret.upper():
                            val_match = re.search(rf'{param_name}\s*=\s*(-?\d+)', param_ret, re.IGNORECASE)
                            if val_match:
                                self.log(f"查询成功: {param_ret}")
                                return {'paramRet': param_ret, 'serNO': ser_no,
                                        'value': val_match.group(1)}, msg_result
                except Exception as e:
                    # tRsp 解析失败但全文本匹配到了, 也尝试直接提取
                    direct_match = re.search(rf'{param_name}\s*=\s*(-?\d+)', response_text, re.IGNORECASE)
                    if direct_match:
                        raw_val = f"{param_name}={direct_match.group(1)}"
                        self.log(f"查询成功(全文匹配): {raw_val}")
                        return {'paramRet': raw_val, 'serNO': ser_no,
                                'value': direct_match.group(1)}, msg_result

                # 检查超时
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    self.log(f"查询超时 ({timeout}s): serNO={ser_no}")
                    return None, None
                    
        except Exception as e:
            self.log(f"查询异常: {e}")
            return None, None


def main():
    config = DeviceConfig()
    api = DeviceAPI(config)
    
    print("=" * 50)
    print("  设备参数操作工具")
    print(f"  地址: {config.base_url}")
    print(f"  设备: {config.device_id}")
    print("=" * 50 + "\n")
    
    # 1. 登录
    if not api.login():
        print("\n登录失败，退出")
        input("\n按回车键退出...")
        return
    
    # 交互式菜单
    while True:
        print("\n" + "-" * 40)
        print("  [1] 查询设备参数")
        print("  [2] 查看最近日志")
        print("  [3] 设置单个参数")
        print("  [4] 批量设置参数")
        print("  [q] 退出")
        print("-" * 40)
        
        choice = input("\n请选择操作: ").strip()
        
        if choice == '1':
            # 查询参数
            ok, params = api.query_params()
            if ok:
                api.print_params(params)
            else:
                print("查询参数失败\n")
        
        elif choice == '2':
            # 查询日志
            h = input("  查询最近几小时日志(默认3): ").strip() or "3"
            ok, logs = api.query_logs(hours=int(h))
            if ok:
                api.print_logs(logs)
        
        elif choice == '3':
            # 单个参数设置
            name = input("  参数名(如 DFTSLEEP): ").strip()
            value = input("  参数值(如 1): ").strip()
            if name and value:
                ok, msg = api.set_param(name, value)
                print(f"\n结果: {'✅ 成功' if ok else '❌ 失败'} - {msg}\n")
        
        elif choice == '4':
            # 批量设置
            print("\n  格式: 参数名=参数值，多个用逗号分隔")
            print("  示例: DFTSLEEP=1,DFTNEWPOWEROFF=1-2-0-0-5")
            raw = input("  输入: ").strip()
            if raw:
                params_dict = {}
                for item in raw.split(','):
                    item = item.strip()
                    if '=' in item:
                        k, v = item.split('=', 1)
                        params_dict[k.strip()] = v.strip()
                
                if params_dict:
                    results = api.set_params_batch(params_dict)
                    print("\n批量设置结果:")
                    for name, ok, msg in results:
                        status = "✅" if ok else "❌"
                        print(f"  {status} {name}: {msg}")
                    print()
        
        elif choice.lower() == 'q':
            print("\n再见！\n")
            break
        
        else:
            print("\n无效选择\n")


if __name__ == "__main__":
    main()
