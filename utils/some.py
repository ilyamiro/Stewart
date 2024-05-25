import os.path
import random
import json
from datetime import datetime

def random_ips(amount: int):
    return [generate_ip() for _ in range(amount)]


def generate_ip():
    return '.'.join(str(random.randint(0, 255)) for _ in range(4))


def half_hour_passed(dt_obj):
    current_time = datetime.now()
    time_difference = current_time - dt_obj
    if time_difference.seconds >= 1800:
        return True
    else:
        return False



