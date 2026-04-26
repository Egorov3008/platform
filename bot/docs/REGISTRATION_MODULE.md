# Модуль регистрации (registration)

Этот модуль отвечает за обработку регистрации пользователей по специальным ссылкам (подарочные и реферальные).

## Структура модуля

Модуль состоит из следующих компонентов:

- `base_registration.py` - абстрактный базовый класс для всех типов регистрации
- `gift_registration.py` - реализация регистрации по подарочным ссылкам
- `referral_registration.py` - реализация регистрации по реферальным ссылкам
- `registration_factory.py` - фабрика для управления обработчиками регистрации
- `__init__.py` - инициализация модуля

## Базовый класс BaseRegistration

Абстрактный класс `BaseRegistration`, определяющий общий интерфейс для всех типов регистрации:

```python
class BaseRegistration(ABC):
    @abstractmethod
    async def can_handle(self, token: str) -> bool:
        """Проверяет, может ли обработчик работать с токеном"""
        pass

    @abstractmethod
    async def register(self, token: str) -> Dict[str, Any]:
        """Выполняет регистрацию и возвращает результат"""
        pass
```

## Реализации регистрации

### GiftRegistration

Класс `GiftRegistration` обрабатывает регистрацию по подарочным ссылкам:

- Проверяет наличие и активность подарочной ссылки в базе данных
- Проверяет, что ссылка еще не была использована (is_redeemable)
- Возвращает информацию о подарке, включая tariff_id и отправителя

### ReferralRegistration

Класс `ReferralRegistration` обрабатывает регистрацию по реферальным ссылкам (файл не найден, структура предполагается аналогичной GiftRegistration)

## RegistrationFactory

Фабрика `RegistrationFactory` управляет обработчиками регистрации:

- Регистрирует обработчики с помощью метода `register_handler`
- Найходит подходящий обработчик для токена с помощью метода `can_handle`
- Выполняет регистрацию с помощью метода `register`
- Возвращает результат регистрации в формате словаря

## Использование

```python
# Создание фабрики
factory = RegistrationFactory()

# Регистрация обработчиков
factory.register_handler(GiftRegistration(service))
factory.register_handler(ReferralRegistration(service))

# Обработка регистрации
result = await factory.handle_registration(token)
if result["success"]:
    print(f"Регистрация успешна: {result["type"]}")
```

## Формат результата

Результат регистрации возвращает словарь со следующими полями:

- `success`: bool - успешность регистрации
- `type`: str - тип регистрации (gift, referral, unknown_user)
- `token`: str - токен регистрации
- `tariff_id`: int - идентификатор тарифа (для подарков)
- `from_user_id`: int - ID пользователя, создавшего ссылку (для подарков и рефералов)
- `error`: str - код ошибки при неуспешной регистрации
