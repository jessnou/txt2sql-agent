"""
Generate and insert realistic Sberbank hierarchy data into ClickHouse.

Usage:
    python scripts/seed_clickhouse.py [--host localhost] [--port 8123] [--db txt2sql]

Requires: clickhouse-connect
"""
from __future__ import annotations

import argparse
import calendar
import random
from datetime import date, timedelta

import clickhouse_connect

TB_DATA = [
    {"tb_id": "13", "tb_name": "Центрально-Черноземный банк"},
    {"tb_id": "16", "tb_name": "Уральский банк"},
    {"tb_id": "18", "tb_name": "Байкальский банк"},
    {"tb_id": "40", "tb_name": "Среднерусский банк"},
    {"tb_id": "42", "tb_name": "Волго-Вятский банк"},
    {"tb_id": "9044", "tb_name": "Московский банк"},
    {"tb_id": "9045", "tb_name": "Сибирский банк"},
    {"tb_id": "9046", "tb_name": "Юго-Западный банк"},
    {"tb_id": "9047", "tb_name": "Поволжский банк"},
    {"tb_id": "9048", "tb_name": "Северо-Западный банк"},
    {"tb_id": "9049", "tb_name": "Дальневосточный банк"},
]

GOSB_DATA = [
    {"struct_code": "8592", "gosb_id": "8592", "tb_id": "13", "gosb_name": "Белгородское отделение №8592", "tb_name": "Центрально-Черноземный банк"},
    {"struct_code": "8593", "gosb_id": "8593", "tb_id": "13", "gosb_name": "Липецкое отделение №8593", "tb_name": "Центрально-Черноземный банк"},
    {"struct_code": "8594", "gosb_id": "8594", "tb_id": "13", "gosb_name": "Тамбовское отделение №8594", "tb_name": "Центрально-Черноземный банк"},
    {"struct_code": "8595", "gosb_id": "8595", "tb_id": "13", "gosb_name": "Орловское отделение №8595", "tb_name": "Центрально-Черноземный банк"},
    {"struct_code": "8596", "gosb_id": "8596", "tb_id": "13", "gosb_name": "Курское отделение №8596", "tb_name": "Центрально-Черноземный банк"},
    {"struct_code": "9013", "gosb_id": "9013", "tb_id": "13", "gosb_name": "ГО по Воронежской области №9013", "tb_name": "Центрально-Черноземный банк"},
    {"struct_code": "9014", "gosb_id": "9014", "tb_id": "13", "gosb_name": "Луганское отделение №9014", "tb_name": "Центрально-Черноземный банк"},
    {"struct_code": "7003", "gosb_id": "7003", "tb_id": "16", "gosb_name": "Свердловское отделение №7003", "tb_name": "Уральский банк"},
    {"struct_code": "8598", "gosb_id": "8598", "tb_id": "16", "gosb_name": "Башкирское отделение №8598", "tb_name": "Уральский банк"},
    {"struct_code": "5940", "gosb_id": "5940", "tb_id": "16", "gosb_name": "Югорское отделение №5940", "tb_name": "Уральский банк"},
    {"struct_code": "8369", "gosb_id": "8369", "tb_id": "16", "gosb_name": "Ямало-Ненецкое отделение №8369", "tb_name": "Уральский банк"},
    {"struct_code": "8597", "gosb_id": "8597", "tb_id": "16", "gosb_name": "Челябинское отделение №8597", "tb_name": "Уральский банк"},
    {"struct_code": "8647", "gosb_id": "8647", "tb_id": "16", "gosb_name": "Западно-Сибирское отделение №8647", "tb_name": "Уральский банк"},
    {"struct_code": "8599", "gosb_id": "8599", "tb_id": "16", "gosb_name": "Курганское отделение №8599", "tb_name": "Уральский банк"},
    {"struct_code": "8586", "gosb_id": "8586", "tb_id": "18", "gosb_name": "Иркутское отделение №8586", "tb_name": "Байкальский банк"},
    {"struct_code": "8600", "gosb_id": "8600", "tb_id": "18", "gosb_name": "Читинское отделение №8600", "tb_name": "Байкальский банк"},
    {"struct_code": "8601", "gosb_id": "8601", "tb_id": "18", "gosb_name": "Бурятское отделение №8601", "tb_name": "Байкальский банк"},
    {"struct_code": "8603", "gosb_id": "8603", "tb_id": "18", "gosb_name": "Якутское отделение №8603", "tb_name": "Байкальский банк"},
    {"struct_code": "17", "gosb_id": "17", "tb_id": "40", "gosb_name": "Ярославское отделение №17", "tb_name": "Среднерусский банк"},
    {"struct_code": "1023", "gosb_id": "1023", "tb_id": "40", "gosb_name": "Восточное ГО по МО №1023", "tb_name": "Среднерусский банк"},
    {"struct_code": "1024", "gosb_id": "1024", "tb_id": "40", "gosb_name": "Южное ГО по МО №1024", "tb_name": "Среднерусский банк"},
    {"struct_code": "1025", "gosb_id": "1025", "tb_id": "40", "gosb_name": "Западное ГО по МО №1025", "tb_name": "Среднерусский банк"},
    {"struct_code": "1026", "gosb_id": "1026", "tb_id": "40", "gosb_name": "Северное ГО по МО №1026", "tb_name": "Среднерусский банк"},
    {"struct_code": "6984", "gosb_id": "6984", "tb_id": "40", "gosb_name": "Пермское отделение №6984", "tb_name": "Среднерусский банк"},
    {"struct_code": "8589", "gosb_id": "8589", "tb_id": "40", "gosb_name": "Мордовское отделение №8589", "tb_name": "Среднерусский банк"},
    {"struct_code": "8604", "gosb_id": "8604", "tb_id": "40", "gosb_name": "Тульское отделение №8604", "tb_name": "Среднерусский банк"},
    {"struct_code": "8605", "gosb_id": "8605", "tb_id": "40", "gosb_name": "Брянское отделение №8605", "tb_name": "Среднерусский банк"},
    {"struct_code": "8606", "gosb_id": "8606", "tb_id": "40", "gosb_name": "Рязанское отделение №8606", "tb_name": "Среднерусский банк"},
    {"struct_code": "8607", "gosb_id": "8607", "tb_id": "40", "gosb_name": "Тверское отделение №8607", "tb_name": "Среднерусский банк"},
    {"struct_code": "8608", "gosb_id": "8608", "tb_id": "40", "gosb_name": "Калужское отделение №8608", "tb_name": "Среднерусский банк"},
    {"struct_code": "8609", "gosb_id": "8609", "tb_id": "40", "gosb_name": "Смоленское отделение №8609", "tb_name": "Среднерусский банк"},
    {"struct_code": "8639", "gosb_id": "8639", "tb_id": "40", "gosb_name": "Ивановское отделение №8639", "tb_name": "Среднерусский банк"},
    {"struct_code": "8640", "gosb_id": "8640", "tb_id": "40", "gosb_name": "Костромское отделение №8640", "tb_name": "Среднерусский банк"},
    {"struct_code": "8610", "gosb_id": "8610", "tb_id": "42", "gosb_name": "Банк Татарстан отделение №8610", "tb_name": "Волго-Вятский банк"},
    {"struct_code": "8611", "gosb_id": "8611", "tb_id": "42", "gosb_name": "Владимирское отделение №8611", "tb_name": "Волго-Вятский банк"},
    {"struct_code": "8612", "gosb_id": "8612", "tb_id": "42", "gosb_name": "Кировское отделение №8612", "tb_name": "Волго-Вятский банк"},
    {"struct_code": "8614", "gosb_id": "8614", "tb_id": "42", "gosb_name": "Марий Эл отделение №8614", "tb_name": "Волго-Вятский банк"},
    {"struct_code": "8618", "gosb_id": "8618", "tb_id": "42", "gosb_name": "Удмуртское отделение №8618", "tb_name": "Волго-Вятский банк"},
    {"struct_code": "9042", "gosb_id": "9042", "tb_id": "42", "gosb_name": "ГО Нижегородской области №9042", "tb_name": "Волго-Вятский банк"},
]

METRICS_DICT = [
    (1, "Боевая численность массовых ролей в канале ВСП"),
    (2, "Боевая численность МО"),
    (3, "Боевая численность СКМ"),
    (4, "Боевая численность СМРК"),
    (5, "СУП ВСП - ЦА"),
    (6, "СУП канал СКМ"),
    (7, "СУП роль СКМ"),
    (8, "СУП канал СМРК"),
    (9, "СУП роль СМРК"),
    (10, "Количество обслуженных клиентов с цифровыми следами СКМ"),
    (11, "Количество обслуженных талонов СМРК"),
    (12, "Производительность СКМ"),
    (13, "Производительность СМРК"),
    (14, "Всего талонов с исключениями для роли СКМ для расчета КПЭ очередей"),
    (15, "Всего зеленых талонов с исключениями для роли СКМ для расчета КПЭ очередей"),
    (16, "Доля талонов к СКМ с ожиданием менее 15 мин — КПЭ очередей"),
    (17, "Всего талонов с исключениями для роли СМО для расчета КПЭ очередей"),
    (18, "Всего зеленых талонов с исключениями для роли СМО для расчета КПЭ очередей"),
    (19, "Доля талонов к СМО с ожиданием менее 10 мин — КПЭ очередей"),
    (20, "Всего талонов с исключениями для роли СМРК для расчета КПЭ очередей"),
    (21, "Всего зеленых талонов с исключениями для роли СМРК для расчета КПЭ очередей"),
    (22, "Доля талонов к СМРК с ожиданием менее 15 мин — КПЭ очередей"),
    (23, "Количество талонов с исключениями для расчета доли талонов с ожиданием 25+ мин"),
    (24, "Количество красных талонов с исключениями для расчета доли талонов с ожиданием 25+ мин"),
    (25, "Доля клиентов с ожиданием более 25 мин (СКМ+СМРК+СМО)"),
    (26, "Количество новичков (3 мес) СКМ"),
    (27, "Кол-во непроизводительных новичков (3 мес) СКМ"),
    (28, "Доля неуспешных новичков (3 мес) СКМ"),
    (29, "Количество новичков (3 мес) СМРК"),
    (30, "Кол-во непроизводительных новичков (3 мес) СМРК"),
    (31, "Доля неуспешных новичков (3 мес) СМРК"),
    (32, "Количество уволенных сотрудников СКМ в текучесть"),
    (33, "Среднефактическая численность СКМ для расчета текучести"),
    (34, "Текучесть СКМ"),
    (35, "Количество уволенных сотрудников СМРК в текучесть"),
    (36, "Среднефактическая численность СМРК для расчета текучести"),
    (37, "Текучесть СМРК"),
    (38, "Количество уволенных сотрудников СМО в текучесть"),
    (39, "Среднефактическая численность СМО для расчета текучести"),
]

METRIC_GROUPS = {
    "headcount": [1, 2, 3, 4],
    "sup": [5, 6, 7, 8, 9],
    "count": [10, 11, 14, 15, 17, 18, 20, 21, 23, 24, 26, 27, 29, 30, 32, 33, 35, 36, 38, 39],
    "performance": [12, 13],
    "ratio": [16, 19, 22, 25, 28, 31, 34, 37],
}

LEVEL_MULTIPLIERS = {"СБ": 1.0, "ТБ": 0.6, "ГОСБ": 0.15, "ВСП": 0.02}

BASE_RANGES = {
    "headcount": (200000, 4000),
    "sup": (50000, 800),
    "count": (100000, 1500),
    "performance": (35.0, 5.0),
    "ratio": (0.75, 0.15),
}

random.seed(42)


def _metric_group(metric_id: int) -> str:
    for group, ids in METRIC_GROUPS.items():
        if metric_id in ids:
            return group
    return "count"


def _base_value(group: str, metric_id: int, level: str) -> float:
    rng = BASE_RANGES[group]
    mult = LEVEL_MULTIPLIERS[level]
    base = rng[0] * mult
    noise = rng[1] * mult if group != "ratio" else rng[1]
    val = base + random.uniform(-noise, noise)
    if group == "ratio":
        val = max(0.0, min(1.0, val + random.uniform(-0.1, 0.1)))
    elif group in ("headcount", "sup", "count"):
        val = max(1, int(round(val)))
    elif group == "performance":
        val = max(0.5, round(val, 2))
    return val


def generate_struct_codes() -> list[dict]:
    rows = []
    rows.append({
        "struct_code": "СБ",
        "struct_lvl": "СБ",
        "tb_id": "",
        "gosb_id": "",
        "tb_name": "",
        "gosb_name": "",
        "vsp_name": "Сбербанк",
    })

    for tb in TB_DATA:
        rows.append({
            "struct_code": tb["tb_id"],
            "struct_lvl": "ТБ",
            "tb_id": tb["tb_id"],
            "gosb_id": "",
            "tb_name": tb["tb_name"],
            "gosb_name": "",
            "vsp_name": tb["tb_name"],
        })

    for g in GOSB_DATA:
        rows.append({
            "struct_code": g["struct_code"],
            "struct_lvl": "ГОСБ",
            "tb_id": g["tb_id"],
            "gosb_id": g["gosb_id"],
            "tb_name": g["tb_name"],
            "gosb_name": g["gosb_name"],
            "vsp_name": g["gosb_name"],
        })

    for g in GOSB_DATA:
        n_vsp = random.randint(3, 7)
        for j in range(1, n_vsp + 1):
            vsp_code = f"{g['gosb_id']}/{j:03d}"
            full_struct = f"{g['tb_id']}_{g['gosb_id']}_{j:03d}"
            rows.append({
                "struct_code": full_struct,
                "struct_lvl": "ВСП",
                "tb_id": g["tb_id"],
                "gosb_id": g["gosb_id"],
                "tb_name": g["tb_name"],
                "gosb_name": g["gosb_name"],
                "vsp_name": f"Доп.офис №{g['gosb_id']}/{j:03d}",
            })

    return rows


def generate_metrics_facts(struct_codes: list[dict]) -> list[dict]:
    rows = []
    end_date = date(2025, 4, 30)
    monthly_dates = []
    d = date(2024, 5, 1)
    while d <= end_date:
        last_day = calendar.monthrange(d.year, d.month)[1]
        monthly_dates.append(d.replace(day=last_day))
        if d.month == 12:
            d = d.replace(year=d.year + 1, month=1)
        else:
            d = d.replace(month=d.month + 1)

    weekly_dates = []
    d = date(2024, 5, 6)
    while d <= end_date:
        weekly_dates.append(d)
        d += timedelta(days=7)

    for sc in struct_codes:
        level = sc["struct_lvl"]
        code = sc["struct_code"]

        for mid, _ in METRICS_DICT:
            group = _metric_group(mid)
            base = _base_value(group, mid, level)

            for mdate in monthly_dates:
                val = base * random.uniform(0.88, 1.12)
                if group == "ratio":
                    val = max(0.0, min(1.0, val + random.uniform(-0.05, 0.05)))
                    val = round(val, 4)
                elif group == "performance":
                    val = round(val, 2)
                else:
                    val = max(1, int(round(val)))

                rows.append({
                    "metric_id": mid,
                    "metric_level": level,
                    "struct_code": code,
                    "period_type": "M",
                    "metric_type": "plan",
                    "report_dt": mdate,
                    "value": round(val * random.uniform(0.95, 1.05), 2) if group != "count" else max(1, int(round(val * random.uniform(0.93, 1.07)))),
                })
                fact_val = val * random.uniform(0.92, 1.08)
                if group == "ratio":
                    fact_val = max(0.0, min(1.0, fact_val + random.uniform(-0.03, 0.03)))
                    fact_val = round(fact_val, 4)
                elif group == "performance":
                    fact_val = round(fact_val, 2)
                else:
                    fact_val = max(1, int(round(fact_val)))

                rows.append({
                    "metric_id": mid,
                    "metric_level": level,
                    "struct_code": code,
                    "period_type": "M",
                    "metric_type": "fact",
                    "report_dt": mdate,
                    "value": fact_val,
                })

            if level in ("ВСП", "ГОСБ", "ТБ"):
                step = 4 if level == "ВСП" else 2 if level == "ГОСБ" else 1
                for widx, wdate in enumerate(weekly_dates):
                    if widx % step != 0:
                        continue
                    val = base * random.uniform(0.85, 1.15)
                    if group == "ratio":
                        val = max(0.0, min(1.0, val + random.uniform(-0.08, 0.08)))
                        val = round(val, 4)
                    elif group == "performance":
                        val = round(val, 2)
                    else:
                        weekly_scale = 0.25 if level == "ВСП" else 0.5
                        val = max(1, int(round(val * weekly_scale * random.uniform(0.8, 1.2))))

                    rows.append({
                        "metric_id": mid,
                        "metric_level": level,
                        "struct_code": code,
                        "period_type": "W",
                        "metric_type": "fact",
                        "report_dt": wdate,
                        "value": val,
                    })

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed ClickHouse with Sberbank metrics data")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8123)
    parser.add_argument("--user", default="default")
    parser.add_argument("--password", default="")
    parser.add_argument("--db", default="txt2sql")
    args = parser.parse_args()

    client = clickhouse_connect.get_client(
        host=args.host,
        port=args.port,
        username=args.user,
        password=args.password,
    )

    print("Creating database and tables...")
    with open("scripts/click_schema.sql") as f:
        sql = f.read()
    for stmt in sql.split(";"):
        stmt = stmt.strip()
        if stmt:
            client.command(stmt)
    print("Tables created.")

    print("Generating struct_code data...")
    struct_rows = generate_struct_codes()
    sc_columns = ["struct_code", "struct_lvl", "tb_id", "gosb_id", "tb_name", "gosb_name", "vsp_name"]
    sc_data = [[row[c] for c in sc_columns] for row in struct_rows]
    client.insert("struct_code", sc_data, sc_columns, database="txt2sql")
    print(f"Inserted {len(struct_rows)} struct_code rows.")

    print("Inserting metrics_dict data...")
    md_columns = ["metric_id", "metric_name"]
    md_data = [[mid, mname] for mid, mname in METRICS_DICT]
    client.insert("metrics_dict", md_data, md_columns, database="txt2sql")
    print(f"Inserted {len(METRICS_DICT)} metrics_dict rows.")

    print("Generating metrics_facts data...")
    facts = generate_metrics_facts(struct_rows)
    print(f"Generated {len(facts)} metrics_facts rows.")

    mf_columns = ["metric_id", "metric_level", "struct_code", "period_type", "metric_type", "report_dt", "value"]
    BATCH_SIZE = 50000
    for i in range(0, len(facts), BATCH_SIZE):
        batch = facts[i:i + BATCH_SIZE]
        mf_data = [
            [row["metric_id"], row["metric_level"], row["struct_code"],
             row["period_type"], row["metric_type"], row["report_dt"], row["value"]]
            for row in batch
        ]
        client.insert("metrics_facts", mf_data, mf_columns, database="txt2sql")
        print(f"  Inserted batch {i // BATCH_SIZE + 1}: {len(batch)} rows")

    print(f"Done. Total: {len(struct_rows)} struct_code, "
          f"{len(METRICS_DICT)} metrics_dict, {len(facts)} metrics_facts rows.")


if __name__ == "__main__":
    main()