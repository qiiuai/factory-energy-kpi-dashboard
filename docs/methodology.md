# Methodology

## 1. Business question

运营团队通常不需要先看到一个复杂模型，而是需要知道：哪条线的能耗偏离了自己的正常水平、偏离是否伴随停机或质量问题、下一步应由谁排查。

## 2. KPI layer

`sql/energy_kpi.sql` 将日运营数据聚合到 `plant_id + line_id + week_start` 粒度。

- 产量、能耗、停机、缺陷使用周累计；
- 峰值功率使用周内日均峰值；
- 单位能耗、停机率、缺陷率在聚合后计算，避免先平均日比例造成口径偏差。

## 3. Explainable anomaly rule

对每一条产线，使用其周单位能耗历史均值和标准差：

```text
energy_intensity_zscore =
    (weekly_intensity - line_history_mean) / line_history_std
```

规则：

- `critical`：z-score ≥ 2.0，或停机率 ≥ 12%；
- `watch`：z-score ≥ 1.25，或停机率 ≥ 8%；
- `normal`：其余情况。

这不是故障诊断模型，而是运营分析的优先级规则。真实场景还需要结合维护工单、设备传感器、班次、产品配方、产能计划和电价时段。

## 4. Suggested operating loop

1. 看工厂/产线排名，定位高能耗和高停机组合；
2. 看趋势，确认是单周波动还是持续恶化；
3. 与维护记录和电表数据核对，排除计量或数据质量问题；
4. 采取维护、参数校准或生产排程动作；
5. 用下一周 KPI 验证动作是否有效。

## 5. Limitations

- 合成数据不代表真实工业分布；
- z-score 对历史长度和异常污染敏感；
- 能耗异常不等于设备故障，也不等于浪费；
- 生产化前应增加数据质量检查、权限管理、告警去重和反馈闭环。

