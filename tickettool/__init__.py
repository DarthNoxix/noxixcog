import json
from pathlib import Path
from dislash import InteractionClient

from .embassytool import EmbassyTool

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


def setup(bot):
    bot.add_cog(EmbassyTool(bot))
    if not hasattr(bot, "slash"):
        bot.slash = InteractionClient(bot)
