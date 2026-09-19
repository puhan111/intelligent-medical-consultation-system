"""
初始化药品目录

可重复执行：已存在的药品按名称跳过。
运行：docker exec app-app python /app/scripts/seed_drugs.py
"""
import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.db.base import create_scheduler_engine, create_scheduler_session_factory
from app.models.drug import Drug

DRUGS = [
    # 抗菌药
    {"name": "阿莫西林胶囊", "spec": "0.25g×24粒", "unit": "盒", "unit_price": Decimal("18.50")},
    {"name": "头孢克洛干混悬剂", "spec": "0.125g×6袋", "unit": "盒", "unit_price": Decimal("32.00")},
    {"name": "阿奇霉素片", "spec": "0.25g×6片", "unit": "盒", "unit_price": Decimal("26.80")},
    # 解热镇痛
    {"name": "布洛芬缓释胶囊", "spec": "0.3g×20粒", "unit": "盒", "unit_price": Decimal("12.00")},
    {"name": "对乙酰氨基酚片", "spec": "0.5g×20片", "unit": "盒", "unit_price": Decimal("9.50")},
    # 呼吸系统
    {"name": "氨溴索口服溶液", "spec": "100ml", "unit": "瓶", "unit_price": Decimal("24.00")},
    {"name": "孟鲁司特钠片", "spec": "10mg×5片", "unit": "盒", "unit_price": Decimal("45.00")},
    {"name": "复方甘草片", "spec": "100片", "unit": "瓶", "unit_price": Decimal("8.00")},
    # 抗过敏
    {"name": "氯雷他定片", "spec": "10mg×6片", "unit": "盒", "unit_price": Decimal("15.60")},
    {"name": "西替利嗪片", "spec": "10mg×10片", "unit": "盒", "unit_price": Decimal("19.80")},
    # 消化系统
    {"name": "奥美拉唑肠溶胶囊", "spec": "20mg×14粒", "unit": "盒", "unit_price": Decimal("28.50")},
    {"name": "铝碳酸镁咀嚼片", "spec": "0.5g×20片", "unit": "盒", "unit_price": Decimal("22.00")},
    {"name": "蒙脱石散", "spec": "3g×10袋", "unit": "盒", "unit_price": Decimal("16.50")},
    # 心血管
    {"name": "苯磺酸氨氯地平片", "spec": "5mg×7片", "unit": "盒", "unit_price": Decimal("21.00")},
    {"name": "阿托伐他汀钙片", "spec": "20mg×7片", "unit": "盒", "unit_price": Decimal("38.00")},
    {"name": "阿司匹林肠溶片", "spec": "100mg×30片", "unit": "盒", "unit_price": Decimal("14.20")},
]


async def main() -> None:
    engine = create_scheduler_engine()
    session_factory = create_scheduler_session_factory(engine)

    created = 0
    skipped = 0
    try:
        async with session_factory() as db:
            for item in DRUGS:
                exists = (
                    await db.execute(select(Drug).where(Drug.name == item["name"]))
                ).scalar_one_or_none()
                if exists:
                    skipped += 1
                    continue
                db.add(Drug(**item, is_active=True))
                created += 1
            await db.commit()
    finally:
        await engine.dispose()

    print(f"药品目录初始化完成：新增 {created} 条，跳过 {skipped} 条")


if __name__ == "__main__":
    asyncio.run(main())
