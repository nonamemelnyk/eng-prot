from environs import Env
from groq import Groq, AsyncGroq

env = Env()
env.read_env()


groq_client = AsyncGroq(api_key=env.str("GROQ_API_KEY"))