import json
import os

class Data:
    """
    class for data handling
    """
    def __init__(self):
        with open(f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Database/data.json", "r") as file:
            data = json.load(file)
        for key in data.keys():
            self.__setattr__(key, data[key])



