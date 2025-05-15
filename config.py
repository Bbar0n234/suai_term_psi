import yaml
from math import log2
import os

# Путь к файлу config.yaml (относительно текущего файла)
config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')

# Загрузка конфигурации из YAML
with open(config_path, 'r') as file:
    config = yaml.safe_load(file)

# Загрузка параметров из YAML
sender_size = config['sender_size']
receiver_size = config['receiver_size']
intersection_size = config['intersection_size']
hash_seeds = config['hash_seeds']
output_bits = config['output_bits']
plain_modulus = config['plain_modulus']
poly_modulus_degree = config['poly_modulus_degree']
alpha = config['alpha']
ell = config['ell']

# Вычисляемые параметры
number_of_hashes = len(hash_seeds)
mask_of_power_of_2 = 2 ** output_bits - 1
sigma_max = int(log2(plain_modulus)) + output_bits - (int(log2(number_of_hashes)) + 1)