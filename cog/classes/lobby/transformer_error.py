from discord import app_commands

class GameTransformError(app_commands.AppCommandError):
    pass


class NumberTransformError(app_commands.AppCommandError):
    pass