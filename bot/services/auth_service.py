"""Bot authentication service for invite-based registration."""
import logging
from typing import Optional

from api.backend_client import BackendAPIClient
from app.schemas.auth import RegisterFromInviteRequest, RegisterFromInviteResponse
from config import INVITE_TOKEN

logger = logging.getLogger(__name__)


class BotAuthService:
    """Service for handling bot authentication and user registration from invites."""

    def __init__(self, backend_client: BackendAPIClient, invite_token: str = INVITE_TOKEN):
        """Initialize BotAuthService.

        Args:
            backend_client: BackendAPIClient for communicating with backend API
            invite_token: The invite token for web registrations
        """
        self.backend_client = backend_client
        self.invite_token = invite_token

    def validate_invite_token(self, token: str) -> bool:
        """Validate an invite token.

        Args:
            token: The invite token to validate

        Returns:
            True if token is valid, False otherwise
        """
        is_valid = token == self.invite_token
        if not is_valid:
            logger.warning(f"Invalid invite token provided")
        return is_valid

    async def _check_user_exists(self, tg_id: int) -> bool:
        """Check if user already exists in backend.

        Args:
            tg_id: Telegram user ID

        Returns:
            True if user exists, False otherwise
        """
        try:
            user = await self.backend_client.get_user(tg_id)
            exists = user is not None
            logger.debug(f"User existence check: tg_id={tg_id}, exists={exists}")
            return exists
        except Exception as e:
            logger.error(f"Error checking user existence: tg_id={tg_id}, error={str(e)}")
            return False

    async def _register_user_and_get_code(
        self,
        tg_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: str = "en",
        invite_token: str = None,
    ) -> Optional[str]:
        """Register user and get generated login code from backend.

        Args:
            tg_id: Telegram user ID
            username: User's Telegram username (optional)
            first_name: User's first name (optional)
            last_name: User's last name (optional)
            language_code: User's language code (default: 'en')
            invite_token: The invite token for validation

        Returns:
            Login code string if successful, None if failed
        """
        if invite_token is None:
            invite_token = self.invite_token

        try:
            request = RegisterFromInviteRequest(
                tg_id=tg_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code,
                invite_token=invite_token,
            )

            response = await self.backend_client.register_from_invite(request)

            logger.info(
                f"User registered from invite: tg_id={tg_id}, "
                f"code_expires_at={response.code_expires_at}"
            )

            return response.login_code

        except Exception as e:
            logger.error(
                f"Error registering user from invite: tg_id={tg_id}, error={str(e)}"
            )
            return None

    async def get_or_register_user(
        self,
        tg_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: str = "en",
        invite_token: Optional[str] = None,
    ) -> Optional[str]:
        """Get existing user's login code or register new user from invite.

        This is the main entry point for the service. It:
        1. Validates the invite token
        2. Checks if user already exists
        3. If user exists, fetches their latest login code (if available)
        4. If user doesn't exist, registers them and gets generated code

        Args:
            tg_id: Telegram user ID
            username: User's Telegram username (optional)
            first_name: User's first name (optional)
            last_name: User's last name (optional)
            language_code: User's language code (default: 'en')
            invite_token: The invite token for validation (uses config default if not provided)

        Returns:
            Login code string if successful, None if failed or token invalid
        """
        if invite_token is None:
            invite_token = self.invite_token

        # Validate token first
        if not self.validate_invite_token(invite_token):
            logger.warning(f"Invalid invite token: tg_id={tg_id}")
            return None

        # Check if user already exists
        user_exists = await self._check_user_exists(tg_id)

        if user_exists:
            logger.info(f"User already exists: tg_id={tg_id}, generating new code via registration")
            # If user exists, we still need to generate a login code
            # The backend will handle the conflict and return the code
            return await self._register_user_and_get_code(
                tg_id=tg_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code,
                invite_token=invite_token,
            )

        # Register new user and get code
        return await self._register_user_and_get_code(
            tg_id=tg_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
            invite_token=invite_token,
        )
