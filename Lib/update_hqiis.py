from config.config import Config

location = Config().get("database_connection_path")


print Config().set("database_connection_path", "poop")
