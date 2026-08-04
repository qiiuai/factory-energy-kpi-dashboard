WITH weekly_operations AS (
    SELECT
        plant_id,
        line_id,
        product_family,
        DATE_TRUNC('week', CAST(event_date AS DATE)) AS week_start,
        SUM(production_units) AS production_units,
        SUM(energy_kwh) AS energy_kwh,
        SUM(operating_hours) AS operating_hours,
        SUM(downtime_min) AS downtime_min,
        SUM(defect_units) AS defect_units,
        AVG(peak_kw) AS avg_peak_kw,
        AVG(ambient_temp_c) AS avg_ambient_temp_c
    FROM daily_operations
    GROUP BY 1, 2, 3, 4
)
SELECT
    plant_id,
    line_id,
    product_family,
    week_start,
    production_units,
    energy_kwh,
    operating_hours,
    downtime_min,
    defect_units,
    avg_peak_kw,
    avg_ambient_temp_c,
    energy_kwh / NULLIF(production_units, 0) AS energy_intensity_kwh_per_unit,
    downtime_min / NULLIF(downtime_min + operating_hours * 60, 0) AS downtime_rate,
    defect_units / NULLIF(production_units, 0) AS defect_rate
FROM weekly_operations
ORDER BY week_start, plant_id, line_id;

