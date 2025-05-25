from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI 

from .version import __version__


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


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
