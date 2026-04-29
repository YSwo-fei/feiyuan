from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from statistics import mean, stdev
from typing import Iterable, List, Optional


@dataclass
class HealthRecord:
    timestamp: datetime
    heart_rate: float
    spo2: float
    glucose: float
    activity_level: float
    device_connected: bool = True


@dataclass
class Baseline:
    heart_rate_min: float
    heart_rate_max: float
    spo2_min: float
    spo2_max: float
    glucose_min: float
    glucose_max: float


@dataclass
class Alert:
    level: str
    message: str
    metric: str
    value: float
    threshold: Optional[str] = None


class HealthMonitor:
    def __init__(self, history: Optional[List[HealthRecord]] = None):
        self.history: List[HealthRecord] = history or []
        self.baseline: Optional[Baseline] = None
        self.update_baseline()

    def add_record(self, record: HealthRecord) -> None:
        self.history.append(record)
        self.update_baseline()

    def update_baseline(self) -> None:
        if len(self.history) < 5:
            self.baseline = Baseline(
                heart_rate_min=50,
                heart_rate_max=110,
                spo2_min=92,
                spo2_max=100,
                glucose_min=70,
                glucose_max=180,
            )
            return

        hr_values = [r.heart_rate for r in self.history]
        spo2_values = [r.spo2 for r in self.history]
        glucose_values = [r.glucose for r in self.history]

        self.baseline = Baseline(
            heart_rate_min=max(40, mean(hr_values) - 1.5 * stdev(hr_values)),
            heart_rate_max=min(140, mean(hr_values) + 1.5 * stdev(hr_values)),
            spo2_min=max(88, mean(spo2_values) - 1.5 * stdev(spo2_values)),
            spo2_max=100,
            glucose_min=max(60, mean(glucose_values) - 1.5 * stdev(glucose_values)),
            glucose_max=min(250, mean(glucose_values) + 1.5 * stdev(glucose_values)),
        )

    def assess_record(self, record: HealthRecord) -> List[Alert]:
        alerts: List[Alert] = []
        baseline = self.baseline
        if baseline is None:
            return alerts

        if not record.device_connected:
            alerts.append(Alert(
                level="warning",
                message="设备未连接或未佩戴，无法获取可靠数据。",
                metric="device_connected",
                value=0.0,
            ))
            return alerts

        if record.glucose < baseline.glucose_min:
            alerts.append(Alert(
                level="critical",
                message="血糖低于正常基线，建议立即复测并补充碳水化合物。",
                metric="glucose",
                value=record.glucose,
                threshold=f"<{baseline.glucose_min:.1f}",
            ))
        elif record.glucose > baseline.glucose_max:
            alerts.append(Alert(
                level="critical",
                message="血糖高于正常基线，可能存在高血糖风险。",
                metric="glucose",
                value=record.glucose,
                threshold=f">{baseline.glucose_max:.1f}",
            ))

        if record.heart_rate < baseline.heart_rate_min:
            alerts.append(Alert(
                level="warning",
                message="心率偏低，需注意是否有头晕或疲劳。",
                metric="heart_rate",
                value=record.heart_rate,
                threshold=f"<{baseline.heart_rate_min:.1f}",
            ))
        elif record.heart_rate > baseline.heart_rate_max:
            alerts.append(Alert(
                level="warning",
                message="心率偏高，建议观察休息状态。",
                metric="heart_rate",
                value=record.heart_rate,
                threshold=f">{baseline.heart_rate_max:.1f}",
            ))

        if record.spo2 < baseline.spo2_min:
            alerts.append(Alert(
                level="warning",
                message="血氧低于正常范围，请保持静息并监测。",
                metric="spo2",
                value=record.spo2,
                threshold=f"<{baseline.spo2_min:.1f}",
            ))

        return alerts

    def assess_latest(self) -> List[Alert]:
        if not self.history:
            return []
        return self.assess_record(self.history[-1])


def create_sample_history() -> List[HealthRecord]:
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


def print_alerts(alerts: List[Alert]) -> None:
    if not alerts:
        print("当前监测数据正常。")
        return
    print("发现异常：")
    for alert in alerts:
        print(f"- [{alert.level}] {alert.metric}: {alert.value} -> {alert.message}")


def main() -> None:
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
    alerts = monitor.assess_latest()
    print_alerts(alerts)


if __name__ == "__main__":
    main()
