from aiogram.filters.state import State, StatesGroup


# DEPRECATED: Registration FSM states removed
# Users are now auto-registered on first login via auto_register_user()
# This class is kept for backward compatibility (imported by states/__init__.py)
class Register(StatesGroup):
    pass
