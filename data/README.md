# Data contract

项目运行后会在 `data/generated/daily_operations.csv` 生成合成数据。

| 字段 | 含义 |
| --- | --- |
| `event_date` | 运营日期 |
| `plant_id` | 工厂标识 |
| `line_id` | 产线标识 |
| `product_family` | 产品族 |
| `production_units` | 当日完成产量 |
| `operating_hours` | 设备运行小时数 |
| `energy_kwh` | 当日用电量 |
| `peak_kw` | 当日峰值功率 |
| `downtime_min` | 当日停机分钟 |
| `defect_units` | 当日缺陷数量 |
| `ambient_temp_c` | 环境温度，仅作外部解释变量示例 |

默认数据覆盖 4 座工厂、每座 6 条产线、90 天运营记录。生成器会注入少量可解释的能效异常，用于测试异常规则和 Dashboard。

