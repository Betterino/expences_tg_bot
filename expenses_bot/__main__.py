"""`python -m expenses_bot` -- the only way to start the bot (Docker's CMD runs exactly this).

The test suite is no longer run here: the Dockerfile's test stage runs it at image
build, so a red suite never becomes an image in the first place."""
import asyncio

from expenses_bot.app import main

asyncio.run(main())
