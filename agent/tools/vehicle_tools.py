"""车辆维修专用工具集"""
import json
import random
from datetime import datetime
from typing import Optional
from utils.logger_handler import logger

# ─── 工具注册装饰器（轻量版） ───


class Tool:
    registry: dict[str, "Tool"] = {}

    def __init__(self, name: str, description: str, func, parameters: dict):
        self.name = name
        self.description = description
        self.func = func
        self.parameters = parameters
        Tool.registry[name] = self

    def run(self, **kwargs) -> str:
        logger.info(f"[Tool] {self.name}({kwargs})")
        return self.func(**kwargs)

    def to_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


def tool(name: str, description: str, parameters: dict):
    def decorator(func):
        Tool(name, description, func, parameters)
        return func
    return decorator


# ─── 基础组件信息库（模拟数据） ─────────────────


PARTS_DB: dict[str, dict] = {
    "氧传感器": {
        "oe": "89465-0D040",
        "price": "¥380-650",
        "location": "排气管前段",
        "common_faults": ["信号电压不变化", "加热器断路", "响应迟缓"],
    },
    "火花塞": {
        "oe": "90919-01239",
        "price": "¥40-120/支",
        "replace_cycle": "4-6万公里",
        "torque": "25-30 N·m",
    },
    "节温器": {
        "oe": "90916-03100",
        "price": "¥120-300",
        "location": "发动机出水口",
        "common_faults": ["卡滞常开", "卡滞常闭", "密封圈老化"],
    },
    "刹车片（前）": {
        "oe": "04465-0E070",
        "price": "¥180-450/套",
        "common_faults": ["摩擦材料开裂", "背板变形", "磨损报警线断裂"],
    },
    "发电机": {
        "oe": "27060-0Y020",
        "price": "¥600-1500",
        "common_faults": ["电刷磨损", "整流器击穿", "轴承异响"],
    },
    "空调压缩机": {
        "oe": "88310-0E140",
        "price": "¥1200-2800",
        "common_faults": ["电磁离合器打滑", "内部拉缸", "泄漏"],
    },
}

TROUBLE_CODES: dict[str, str] = {
    "P0011": "进气凸轮轴位置-正时过度提前（机油压力不足或VVT执行器卡滞）",
    "P0030": "氧传感器加热器控制电路故障（前）",
    "P0101": "质量空气流量传感器电路/性能故障",
    "P0113": "进气温度传感器电路高电压",
    "P0171": "系统过稀（燃油修正）",
    "P0300": "检测到随机/多缸失火",
    "P0340": "凸轮轴位置传感器电路故障",
    "P0420": "催化转换器效率低于阈值",
    "P0442": "蒸发排放控制系统泄漏（小泄漏）",
    "P0500": "车速传感器故障",
    "P0562": "系统电压低",
    "P0620": "发电机控制电路故障",
    "P0700": "变速箱控制系统故障",
    "P0846": "变速箱油压传感器/开关电路范围/性能",
}


# ─── 工具定义 ──────────────────────────────


@tool(
    name="search_trouble_code",
    description="查询故障码（DTC）含义和维修建议，输入故障码编号",
    parameters={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "故障码编号，如 P0300"},
        },
        "required": ["code"],
    },
)
def search_trouble_code(code: str) -> str:
    code_upper = code.upper()
    if code_upper in TROUBLE_CODES:
        desc = TROUBLE_CODES[code_upper]
        return f"故障码 {code_upper}：{desc}\n建议：读取数据流确认条件，参照维修手册检修。"
    return f"故障码 {code_upper}：未在知识库中找到该码，请连接诊断仪读取故障码详情。"


@tool(
    name="search_part_info",
    description="查询汽车零配件信息（OE号、价格、位置、常见故障）",
    parameters={
        "type": "object",
        "properties": {
            "part_name": {"type": "string", "description": "配件名称，如 氧传感器"},
        },
        "required": ["part_name"],
    },
)
def search_part_info(part_name: str) -> str:
    if part_name in PARTS_DB:
        info = PARTS_DB[part_name]
        lines = [f"【{part_name}】"]
        for k, v in info.items():
            if isinstance(v, list):
                lines.append(f"  • {k}：{', '.join(v)}")
            else:
                lines.append(f"  • {k}：{v}")
        return "\n".join(lines)
    matches = [k for k in PARTS_DB if part_name in k or k in part_name]
    if matches:
        return f"未精确匹配「{part_name}」，相关配件：{', '.join(matches[:5])}"
    return f"未找到「{part_name}」的信息。"


@tool(
    name="get_current_time",
    description="获取当前日期和时间",
    parameters={
        "type": "object",
        "properties": {},
    },
)
def get_current_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@tool(
    name="get_safety_warning",
    description="获取特定维修操作的安全警告",
    parameters={
        "type": "object",
        "properties": {
            "operation": {"type": "string", "description": "维修操作，如 拆卸燃油泵"},
        },
        "required": ["operation"],
    },
)
def get_safety_warning(operation: str) -> str:
    warnings = {
        "燃油": "⚠️ 安全警告：在燃油系统附近作业时，必须断开蓄电池负极。保持工作区域通风，禁止明火。建议佩戴护目镜。",
        "制动": "⚠️ 安全警告：拆卸制动管路后必须排气。不可混用不同规格的制动液（DOT3/DOT4/DOT5.1）。试车时先低俗测试制动效果。",
        "气囊": "⚠️ 安全警告：操作安全气囊系统前必须断开蓄电池并等待至少3分钟（电容放电时间）。不要用万用表测量气囊引爆管电阻。",
        "空调": "⚠️ 安全警告：空调制冷剂回收必须使用专用设备，不可排入大气。维修高压侧（＞15bar）时必须佩戴护目镜和手套。",
        "高压": "⚠️ 安全警告：高压电系统作业需穿戴绝缘手套和护目镜，使用绝缘工具。拆卸前确认高压互锁已断开并等待5分钟电容放电。",
    }
    for kw, w in warnings.items():
        if kw in operation:
            return w
    return "⚠️ 请查阅该车型维修手册的安全注意事项，佩戴个人防护装备。"


@tool(
    name="estimate_repair_time",
    description="估算常见维修项目的工时",
    parameters={
        "type": "object",
        "properties": {
            "repair_item": {"type": "string", "description": "维修项目，如 更换刹车片"},
            "vehicle_type": {"type": "string", "description": "车型类别：轿车/SUV/MPV"},
        },
        "required": ["repair_item"],
    },
)
def estimate_repair_time(repair_item: str, vehicle_type: str = "轿车") -> str:
    labor_times = {
        "更换刹车片": {"轿车": 0.8, "SUV": 1.0, "MPV": 1.2},
        "更换刹车盘": {"轿车": 1.0, "SUV": 1.2, "MPV": 1.5},
        "更换机油机滤": {"轿车": 0.5, "SUV": 0.6, "MPV": 0.6},
        "更换火花塞": {"轿车": 0.8, "SUV": 1.0, "MPV": 1.2},
        "更换正时皮带": {"轿车": 2.5, "SUV": 3.0, "MPV": 3.5},
        "更换空调滤芯": {"轿车": 0.3, "SUV": 0.4, "MPV": 0.5},
        "更换氧传感器": {"轿车": 0.6, "SUV": 0.8, "MPV": 0.8},
    }
    for key, times in labor_times.items():
        if key in repair_item or repair_item in key:
            hrs = times.get(vehicle_type, times.get("轿车", 1.0))
            return f"「{key}」在{vehicle_type}上预估 {hrs} 工时（约 {hrs*60:.0f} 分钟）"
    return f"未找到「{repair_item}」的标准工时数据，建议查阅维修手册。"


def get_all_tools() -> list[Tool]:
    return list(Tool.registry.values())
