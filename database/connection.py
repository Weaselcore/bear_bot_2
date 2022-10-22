from os import getenv
from dotenv import load_dotenv
import pymongo
from pymongo import MongoClient

load_dotenv()

password = getenv('PASSWORD')
if password is None:
    raise TypeError("Password is none")


class MongoManager:
    __instance: MongoClient | None = None

    @staticmethod
    def getInstance():
        if MongoManager.__instance is None:
            MongoManager()
        return MongoManager.__instance

    def __init__(self):
        if MongoManager.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            MongoManager.__instance = pymongo.MongoClient(
                f"mongodb+srv://admin:{password}@singapore-cluster.5vyhpbn.mongodb.net/?retryWrites=true&w=majority"
            )
