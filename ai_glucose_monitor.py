from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from statistics import mean, stdev
from typing import Iterable, List, Optional


@dataclass
class HealthRecord:
    """健康记录数据结构，包含单次监测的所有指标"""
    timestamp: datetime  # 记录时间戳
    heart_rate: float    # 心率（bpm）
    spo2: float          # 血氧饱和度（%）
    glucose: float       # 血糖水平（mg/dL）
    activity_level: float  # 活动水平（0-2，0=静息，2=高强度）
    device_connected: bool = True  # 设备是否连接/佩戴


@dataclass
class Baseline:
    """用户个性化基线数据，基于历史数据计算"""
    heart_rate_min: float  # 心率下限
    heart_rate_max: float  # 心率上限
    spo2_min: float        # 血氧下限
    spo2_max: float        # 血氧上限
    glucose_min: float     # 血糖下限
    glucose_max: float     # 血糖上限


@dataclass
class Alert:
    """异常告警信息"""
    level: str             # 告警级别：normal/info/warning/critical
    message: str           # 告警消息
    metric: str            # 异常指标名称
    value: float           # 异常值
    threshold: Optional[str] = None  # 阈值描述


class HealthMonitor:
    """健康监测器，负责基线计算和异常检测"""

    ALERT_PRIORITY = {
        "normal": 0,
        "info": 1,
        "warning": 2,
        "critical": 3,
    }

    def __init__(self, history: Optional[List[HealthRecord]] = None):
        """初始化监测器
        Args:
            history: 历史健康记录列表
        """
        self.history: List[HealthRecord] = history or []
        self.baseline: Optional[Baseline] = None
        self.update_baseline()

    def add_record(self, record: HealthRecord) -> None:
        """添加新记录并更新基线
        Args:
            record: 新健康记录
        """
        self.history.append(record)
        self.update_baseline()

    def update_baseline(self) -> None:
        """基于历史数据更新个性化基线"""
        if len(self.history) < 5:
            # 数据不足时使用默认基线
            self.baseline = Baseline(
                heart_rate_min=50,
                heart_rate_max=110,
                spo2_min=92,
                spo2_max=100,
                glucose_min=70,
                glucose_max=180,
            )
            return

        # 计算各指标的历史均值和标准差
        hr_values = [r.heart_rate for r in self.history]
        spo2_values = [r.spo2 for r in self.history]
        glucose_values = [r.glucose for r in self.history]

        # 使用均值±1.5倍标准差作为基线范围
        self.baseline = Baseline(
            heart_rate_min=max(40, mean(hr_values) - 1.5 * stdev(hr_values)),
            heart_rate_max=min(140, mean(hr_values) + 1.5 * stdev(hr_values)),
            spo2_min=max(88, mean(spo2_values) - 1.5 * stdev(spo2_values)),
            spo2_max=100,
            glucose_min=max(60, mean(glucose_values) - 1.5 * stdev(glucose_values)),
            glucose_max=min(250, mean(glucose_values) + 1.5 * stdev(glucose_values)),
        )

    def assess_record(self, record: HealthRecord) -> List[Alert]:
        """评估单条记录的异常情况
        Args:
            record: 要评估的健康记录
        Returns:
            异常告警列表
        """
        alerts: List[Alert] = []
        baseline = self.baseline
        if baseline is None:
            return alerts

        # 检查设备连接状态
        if not record.device_connected:
            alerts.append(Alert(
                level="warning",
                message="设备未连接或未佩戴，无法获取可靠数据。",
                metric="device_connected",
                value=0.0,
            ))
            return alerts

        # 判断是否处于静息状态
        is_resting = record.activity_level <= 1.0

        # 血糖异常检测
        if record.glucose < baseline.glucose_min:
            level = "critical" if record.glucose < 55 else "warning"  # 严重低血糖
            alerts.append(Alert(
                level=level,
                message="血糖低于正常基线，建议立即复测并补充碳水化合物。",
                metric="glucose",
                value=record.glucose,
                threshold=f"<{baseline.glucose_min:.1f}",
            ))
        elif record.glucose > baseline.glucose_max:
            level = "critical" if record.glucose > 240 else "warning"  # 严重高血糖
            alerts.append(Alert(
                level=level,
                message="血糖高于正常基线，可能存在高血糖风险。",
                metric="glucose",
                value=record.glucose,
                threshold=f">{baseline.glucose_max:.1f}",
            ))

        # 心率异常检测
        if record.heart_rate < baseline.heart_rate_min:
            alerts.append(Alert(
                level="warning",
                message="心率偏低，需注意是否有头晕或疲劳。",
                metric="heart_rate",
                value=record.heart_rate,
                threshold=f"<{baseline.heart_rate_min:.1f}",
            ))
        elif record.heart_rate > baseline.heart_rate_max:
            level = "critical" if is_resting and record.heart_rate > baseline.heart_rate_max + 10 else "warning"
            alerts.append(Alert(
                level=level,
                message="心率偏高，建议观察休息状态。" if level == "warning" else "静息状态下心率显著偏高，需尽快检查。",
                metric="heart_rate",
                value=record.heart_rate,
                threshold=f">{baseline.heart_rate_max:.1f}",
            ))

        # 血氧异常检测
        if record.spo2 < baseline.spo2_min:
            level = "critical" if record.spo2 < 90 else "warning"  # 严重低氧
            alerts.append(Alert(
                level=level,
                message="血氧低于正常范围，请保持静息并监测。",
                metric="spo2",
                value=record.spo2,
                threshold=f"<{baseline.spo2_min:.1f}",
            ))

        # 复合异常检测：多项指标同时异常
        if record.glucose > baseline.glucose_max and record.heart_rate > baseline.heart_rate_max and record.spo2 < baseline.spo2_min:
            alerts.append(Alert(
                level="critical",
                message="多项指标同时异常，风险较高，请立即关注。",
                metric="composite",
                value=0.0,
            ))

        return alerts

    def get_overall_alert_level(self, alerts: List[Alert]) -> str:
        """获取整体告警级别
        Args:
            alerts: 告警列表
        Returns:
            最高告警级别
        """
        if not alerts:
            return "normal"
        highest = max((self.ALERT_PRIORITY.get(alert.level, 0) for alert in alerts), default=0)
        for level, score in reversed(self.ALERT_PRIORITY.items()):
            if score == highest:
                return level
        return "normal"

    def assess_latest(self) -> tuple[List[Alert], str]:
        """评估最新记录
        Returns:
            (告警列表, 整体告警级别)
        """
        if not self.history:
            return [], "normal"
        alerts = self.assess_record(self.history[-1])
        return alerts, self.get_overall_alert_level(alerts)


def create_sample_history() -> List[HealthRecord]:
    """创建示例历史数据用于测试"""
    now = datetime.now()
    sample: List[HealthRecord] = []
    for hour in range(24):
        sample.append(HealthRecord(
            timestamp=now - timedelta(hours=24 - hour),
            heart_rate=70 + (hour % 5) * 2,
            spo2=95 - (hour % 3) * 0.4,
            glucose=90 + (hour % 6) * 4,
            activity_level=0.5 if hour < 8 or hour > 20 else 1.2,
            device_connected=True,
        ))
    return sample


def print_alerts(alerts: List[Alert], overall_level: str) -> None:
    """打印告警信息
    Args:
        alerts: 告警列表
        overall_level: 整体告警级别
    """
    if overall_level == "normal":
        print("当前监测数据正常。")
        return
    print(f"整体告警级别：{overall_level}")
    print("发现异常：")
    for alert in alerts:
        print(f"- [{alert.level}] {alert.metric}: {alert.value} -> {alert.message}")


def main() -> None:
    """主函数：运行示例"""
    history = create_sample_history()
    monitor = HealthMonitor(history=history)

    # 模拟最新一条记录
    latest_record = HealthRecord(
        timestamp=datetime.now(),
        heart_rate=120,
        spo2=90,
        glucose=240,
        activity_level=0.3,
        device_connected=True,
    )
    monitor.add_record(latest_record)
    alerts, overall_level = monitor.assess_latest()
    print_alerts(alerts, overall_level)


if __name__ == "__main__":
    main()

