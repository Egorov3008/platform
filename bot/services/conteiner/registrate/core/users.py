import asyncpg
import punq
from punq import Container

from client import XUISession
from services.conteiner.protocol import ContainerProtocol
from services.core.data.service import ServiceDataModel
from services.core.user.utils.checked_admin import CheckedUser
from services.core.user.utils.delete_data import DeleteUser
from services.core.user.utils.saver import SeverUser
from services.core.user.utils.saturation import SaturationUser
from services.core.user.utils.trial import TrialService


class UserServiceRegistrar(ContainerProtocol):
    def register_dependencies(self, container: Container) -> None:
        def build_saturation_user():
            return SaturationUser(model_data=container.resolve(ServiceDataModel))

        def build_trial_service():
            return TrialService(
                model_data=container.resolve(ServiceDataModel),
            )

        def build_delete_user():
            return DeleteUser(
                model_data=container.resolve(ServiceDataModel),
                xui_session=container.resolve(XUISession),
                pool=container.resolve(asyncpg.Pool),
            )

        def build_sever_user():
            return SeverUser(model_data=container.resolve(ServiceDataModel))

        container.register(CheckedUser, scope=punq.Scope.singleton)
        container.register(
            SaturationUser, factory=build_saturation_user, scope=punq.Scope.singleton
        )
        container.register(
            TrialService, factory=build_trial_service, scope=punq.Scope.singleton
        )
        container.register(
            DeleteUser, factory=build_delete_user, scope=punq.Scope.singleton
        )
        container.register(
            SeverUser, factory=build_sever_user, scope=punq.Scope.singleton
        )
