from typing import List

from aiogram_dialog import DialogManager

from dialogs.windows.base import DataGetter
from models import Tariff
from services.core.price.service import PriceService
from services.core.tariff.data import TariffData
from logger import logger


class TariffPreviewGetter(DataGetter):
    """Геттер для получения данных для отображения доступных тарифов."""

    def __init__(
        self,
        tariff_display: TariffData,
        price_service: PriceService,
    ):
        self.tariff_display = tariff_display
        self.price_service = price_service

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> dict:
        """Получение данных для отображения."""
        tg_id = dialog_manager.event.from_user.id

        tariffs: List[Tariff] = await self.tariff_display.get(tg_id)
        results = await self.price_service.calculate_batch(tg_id, tariffs)

        logger.info(
            "[Цена:TariffPreview] Начало формирования тарифов",
            tg_id=tg_id,
            tariff_count=len(tariffs),
        )

        processed_tariffs = {}
        tariff_list = []

        for tariff in tariffs:
            r = results[tariff.id]

            logger.debug(
                "[Цена:TariffPreview] Тариф обработан",
                tariff_id=tariff.id,
                tariff_name=tariff.name_tariff,
                original_amount=r.original_amount,
                discounted_amount=r.final_amount,
                has_discount=r.has_discount
            )

            # Формируем текст кнопки с правильной (скидочной) ценой
            button_text = (
                f"Тариф-{r.final_amount}₽ SALE 🎁"
                if r.has_discount
                else tariff.name_tariff
            )
            tariff_list.append((button_text, tariff.id))

            # Заполняем processed_tariffs с информацией о тарифе и скидке
            processed_tariffs[str(tariff.id)] = {
                "tariff": tariff,
                "discounted_amount": r.final_amount if r.has_discount else None,
            }

        logger.debug("[Цена:TariffPreview] Тарифы записаны", count=len(processed_tariffs))

        # Сохраняем в dialog_data для доступа из обработчиков клавиатуры
        dialog_manager.dialog_data["processed_tariffs"] = processed_tariffs

        # Берём данные скидки из последнего обработанного результата
        last_result = results[tariffs[-1].id] if tariffs else None
        return {
            "tariffs": processed_tariffs,
            "discount_value": float(last_result.stock_value) if last_result else 0.0,
            "discount_type": last_result.stock_type if last_result else "",
            "tariff_list": tariff_list,
        }
