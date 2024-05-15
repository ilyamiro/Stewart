import os.path
import random
import json


def random_ips(amount: int):
    return [generate_ip() for _ in range(amount)]


def generate_ip():
    return '.'.join(str(random.randint(0, 255)) for _ in range(4))



