import logging

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI 

from .version import __version__
from .internal.database import database
from .internal.config import log_conf, settings
from .routers import main


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    await log_conf.setup_logging()
    logger: logging.Logger = logging.getLogger("password_manager")

    try:
        await database.setup()
    except Exception:
        logger.critical("Database startup failed:", exc_info=True)
        raise

    logger.info("Application started, running version '%s'", __version__)
    yield

    try:
        await database.close()
    except Exception:
        logger.critical("Could not close database:", exc_info=True)
        raise

    logger.info("Application stopped")


app = FastAPI(
    title='NewGuy103 - PasswordManager',
    version=__version__,
    lifespan=app_lifespan, 
    debug=True,
    contact={'name': 'NewGuy103'},
    license_info={
        'name': 'Mozilla Public License 2.0',
        'url': 'https://www.mozilla.org/en-US/MPL/2.0/',
        'identifier': 'MPL-2.0'
    }
)
app.include_router(main.router)
