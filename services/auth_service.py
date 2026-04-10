import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from utils.security import hash_password, verify_password, create_access_token, get_user_id_from_token


async def register_user(
    db: AsyncSession,
    display_name: str,
    email: str,
    username: str,
    password: str,
) -> User:
    """
    Register a new user.

    Validates that the email and username are unique, hashes the password,
    creates the user record, and returns the new User object.

    Raises:
        ValueError: If the email or username already exists.
    """
    email_lower = email.strip().lower()
    username_lower = username.strip().lower()

    result = await db.execute(
        select(User).where(User.email == email_lower)
    )
    existing_email = result.scalars().first()
    if existing_email is not None:
        raise ValueError("A user with this email already exists.")

    result = await db.execute(
        select(User).where(User.username == username_lower)
    )
    existing_username = result.scalars().first()
    if existing_username is not None:
        raise ValueError("A user with this username already exists.")

    hashed = hash_password(password)

    new_user = User(
        display_name=display_name.strip(),
        email=email_lower,
        username=username_lower,
        password_hash=hashed,
        role="user",
        is_active=True,
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)
    return new_user


async def login_user(
    db: AsyncSession,
    username: str,
    password: str,
) -> Optional[str]:
    """
    Authenticate a user by username and password.

    Returns a JWT access token string on success, or None if credentials
    are invalid or the user account is inactive.
    """
    username_lower = username.strip().lower()

    result = await db.execute(
        select(User).where(User.username == username_lower)
    )
    user = result.scalars().first()

    if user is None:
        return None

    if not user.is_active:
        return None

    if not verify_password(password, user.password_hash):
        return None

    token = create_access_token(data={"sub": str(user.id)})
    return token


async def get_current_user(
    db: AsyncSession,
    token: str,
) -> Optional[User]:
    """
    Look up the current user from a JWT access token.

    Returns the User object if the token is valid and the user exists
    and is active, otherwise returns None.
    """
    user_id = get_user_id_from_token(token)
    if user_id is None:
        return None

    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalars().first()

    if user is None:
        return None

    if not user.is_active:
        return None

    return user


async def get_user_by_id(
    db: AsyncSession,
    user_id: int,
) -> Optional[User]:
    """
    Retrieve a user by their ID.

    Returns the User object if found, otherwise None.
    """
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalars().first()


async def get_user_by_username(
    db: AsyncSession,
    username: str,
) -> Optional[User]:
    """
    Retrieve a user by their username.

    Returns the User object if found, otherwise None.
    """
    result = await db.execute(
        select(User).where(User.username == username.strip().lower())
    )
    return result.scalars().first()


async def get_user_by_email(
    db: AsyncSession,
    email: str,
) -> Optional[User]:
    """
    Retrieve a user by their email address.

    Returns the User object if found, otherwise None.
    """
    result = await db.execute(
        select(User).where(User.email == email.strip().lower())
    )
    return result.scalars().first()


async def update_user_profile(
    db: AsyncSession,
    user: User,
    display_name: Optional[str] = None,
    email: Optional[str] = None,
) -> User:
    """
    Update a user's profile fields.

    Validates email uniqueness if changed. Returns the updated User object.

    Raises:
        ValueError: If the new email is already taken by another user.
    """
    if display_name is not None:
        stripped = display_name.strip()
        if not stripped:
            raise ValueError("Display name cannot be empty.")
        if len(stripped) > 100:
            raise ValueError("Display name must be 100 characters or fewer.")
        user.display_name = stripped

    if email is not None:
        email_lower = email.strip().lower()
        if email_lower != user.email:
            result = await db.execute(
                select(User).where(User.email == email_lower)
            )
            existing = result.scalars().first()
            if existing is not None:
                raise ValueError("A user with this email already exists.")
            user.email = email_lower

    await db.flush()
    await db.refresh(user)
    return user