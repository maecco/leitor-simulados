from abc import ABC, abstractmethod
from enum import Enum

class StorageType:
    pass


class StorageDriver:
    pass



class DataBaseDriver():
    
    @classmethod
    def get_available_dbs(cls) -> list[str]:
        pass

    def get_connection(self):
        pass


class FileSystemDriver():

    @classmethod
    def find_images(cls, path : str, name : str, extension : str) -> list[str]:
        pass

    @classmethod
    def find_models(cls, path : str, name : str, extension : str) -> list[str]:
        pass