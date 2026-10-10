from app.exceptions.custom import AppException
from app.utils.password import verify_password
from app.exceptions.custom import UserNotFoundException, InvalidCredentialsException, UserAlreadyExistsException
from app.types.auth import TokenResponse
from app.types.user import UserResponse
from app.utils.jwt import create_access_token
import logging
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.utils.password import hash_password


logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def register(self, email: str, name: str, password: str) -> TokenResponse:
        user = await self.user_repository.get_user_by_email(email)
        if user:
            logger.error(f"auth_service: User with email '{email}' already taken")
            raise UserAlreadyExistsException(f"User with email '{email}' already taken")
        
        password_hash = hash_password(password)

        try:
            user = User(email=email, name=name, password_hash=password_hash)
            created_user = await self.user_repository.create_user(user)

            user_response = UserResponse.model_validate(created_user)
            access_token = create_access_token(data={"user_id": str(created_user.id)})

            return TokenResponse(
                access_token=access_token,
                token_type="bearer",
                user=user_response,
            )
        except Exception as e:
            logger.error(f"auth_service: Failed to create user: {str(e)}", exc_info=True)
            raise AppException("Unable to complete registration. Please try again later.", status_code=500)
    
    async def login(self, email: str, password: str) -> TokenResponse:
        try: 
            user = await self.user_repository.get_user_by_email(email)
            if not user:
                logger.error(f"auth_service: User with email '{email}' not found")
                raise UserNotFoundException(f"User with email '{email}' not found")
            
            if not verify_password(password, user.password_hash):
                logger.error(f"auth_service: Invalid password for email '{email}'")
                raise InvalidCredentialsException(f"Invalid password for email '{email}'")
            
            user_response = UserResponse.model_validate(user)
            access_token = create_access_token(data={"user_id": str(user.id)})

            return TokenResponse(
                access_token=access_token,
                token_type="bearer",
                user=user_response,
            )
        except Exception as e:
            logger.error(f"auth_service: Failed to login: {str(e)}", exc_info=True)
            raise AppException("Unable to complete login. Please try again later.", status_code=500)
        
    