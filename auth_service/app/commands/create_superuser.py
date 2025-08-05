import typer
from sqlalchemy import select
from app.models.auth import User
from app.db.database import async_session
from app.services.auth import create_user, create_email_verify_token, publish_event
from shared.utils import constants as rb_const
from app.core.config import settings
import asyncio
import logging

app = typer.Typer()
logger = logging.getLogger(__name__)


async def async_create_superuser(email: str, password: str, username: str, user_id: int = None):
    """Create a superuser with is_superadmin=True and ID between 1 and 5."""
    async with async_session() as db:
        try:
            if user_id is None:
                result = await db.execute(select(User.id).where(User.id <= 5))
                existing_ids = {id_tuple[0] for id_tuple in result.fetchall()}
                available_ids = set(range(1, 6)) - existing_ids
                if not available_ids:
                    typer.echo("Error: All IDs from 1 to 5 are already taken.")
                    raise ValueError("No available IDs for superuser.")
                user_id = min(available_ids)
            elif user_id < 1 or user_id > 5:
                typer.echo("Error: Superuser ID must be between 1 and 5.")
                raise ValueError("Invalid user_id for superuser.")

            result = await db.execute(select(User).where(User.id == user_id))
            existing_user = result.scalars().first()
            if existing_user:
                typer.echo(f"Error: User with ID {user_id} already exists.")
                raise ValueError("User ID already taken.")

            db_user = await create_user(db, email, password, username)

            db_user.id = user_id
            db_user.is_superadmin = True
            await db.commit()
            await db.refresh(db_user)

            token = await create_email_verify_token(db, db_user)

            await publish_event(
                rb_const.RABBITMQ_QUEUE_EMAIL_EVENTS,
                rb_const.EVENT_EMAIL_SEND,
                {
                    "email": db_user.email,
                    "subject": "Verify Your Account",
                    "template_name": "register.html",
                    "context": {
                        "verify_url": f'{settings.frontend_url}/verify-email/{token}',
                        "username": db_user.username,
                    }
                }
            )

            logger.info(
                "Superuser registered, verification email sent",
                extra={"user_id": db_user.id, "email": db_user.email, "username": db_user.username}
            )
            typer.echo(f"Superuser {username} created successfully with ID {db_user.id}. Verification email sent.")

        except Exception as e:
            await db.rollback()
            typer.echo(f"Error creating superuser: {str(e)}")
            raise
        finally:
            await db.close()


@app.command()
def create_superuser(
    email: str = typer.Option(..., "--email", help="Email address of the superuser"),
    password: str = typer.Option(..., "--password", help="Password for the superuser"),
    username: str = typer.Option(..., "--username", help="Username for the superuser"),
    user_id: int = typer.Option(None, "--user-id", help="User ID (1-5) for the superuser, defaults to first available")
):
    """Create a superuser with is_superadmin=True and ID between 1 and 5.
    Usage: poetry run python -m app.commands.create_superuser --email admin@example.com --password Secret123! --username Admin --user-id 1
    """
    asyncio.run(async_create_superuser(email, password, username, user_id))

if __name__ == "__main__":
    app()
