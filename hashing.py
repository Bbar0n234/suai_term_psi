import random
from random import randint

import mmh3

import logging

import math
from math import log2, comb, ceil

from config import output_bits, number_of_hashes, sender_size

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("psi_api")


def calculate_bin_capacity(security_bits: int = 30) -> int:
    """
    Вычисляет bin_capacity на основе параметров безопасности и конфигурации хеширования.

    :param security_bits: Требуемый уровень безопасности (по умолчанию 2^-30).
    :return: Значение bin_capacity.
    """
    m = 2 ** output_bits
    d = number_of_hashes * sender_size

    md_1 = m ** (d - 1)
    s = 0
    S = m ** d
    i = 0
    power_of_m_1 = (m - 1) ** d
    while True:
        current_term = comb(d, i) * power_of_m_1
        s += current_term
        S -= current_term
        if int(log2(md_1) - log2(S)) >= security_bits:
            break
        i += 1
        power_of_m_1 //= (m - 1)

    return i - 1


class SimpleHash:
    def __init__(self, hash_seed_list, output_bits, bin_capacity):
        """
        :param hash_seed_list: список сидов для хеш-функций Murmur
        :param output_bits: количество бит, определяющее количество корзин (2^output_bits)
        :param bin_capacity: максимальное количество элементов в одной корзине
        """
        self.output_bits = output_bits
        self.bin_capacity = bin_capacity
        self.hash_seeds = hash_seed_list
        self.num_bins = 2 ** output_bits
        self.mask = (1 << output_bits) - 1
        self.hashed_data = [[None for _ in range(bin_capacity)] for _ in range(self.num_bins)]
        self.occurrences = [0] * self.num_bins
        self.failed = False

    def _combine_left_and_index(self, item: int, index: int) -> int:
        """
        Объединение старших бит item и индекса в одно целое число.
        :param item: элемент (целое число)
        :param index: индекс хеш-функции
        :return: результат item_left || index
        """
        item_left = item >> self.output_bits
        return (item_left << self._log_num_hashes()) + index

    def _location(self, seed: int, item: int) -> int:
        """
        Вычисляет местоположение элемента в таблице по хешу.
        :param seed: сид хеш-функции
        :param item: элемент
        :return: индекс корзины
        """
        item_left = item >> self.output_bits
        item_right = item & self.mask
        hash_left = mmh3.hash(str(item_left), seed, signed=False) >> (32 - self.output_bits)
        return hash_left ^ item_right

    def _log_num_hashes(self):
        """
        Возвращает количество бит, необходимое для хранения индекса хеш-функции.
        Предполагается, что количество хеш-функций равно длине self.hash_seeds.
        """
        return ceil(log2(len(self.hash_seeds)))

    def insert(self, item: int, hash_index: int):
        """
        Вставляет элемент в таблицу с использованием хеш-функции по индексу.
        :param item: вставляемый элемент
        :param hash_index: индекс используемой хеш-функции
        """
        loc = self._location(self.hash_seeds[hash_index], item)
        if self.occurrences[loc] < self.bin_capacity:
            encoded_item = self._combine_left_and_index(item, hash_index)
            self.hashed_data[loc][self.occurrences[loc]] = encoded_item
            self.occurrences[loc] += 1
        else:
            self.failed = True
            logger.critical('Ошибка: превышена ёмкость корзины. Хеширование остановлено.')


class CuckooHash:
    def __init__(self, hash_seeds, output_bits: int):
        """
        :param hash_seeds: список сидов для хеш-функций
        :param output_bits: количество бит (2^output_bits корзин)
        :param num_hashes: количество используемых хеш-функций
        """
        self.hash_seeds = hash_seeds
        self.output_bits = output_bits
        self.num_hashes = len(self.hash_seeds)
        self.num_bins = 2 ** output_bits
        self.mask = (1 << output_bits) - 1
        self.log_num_hashes = math.ceil(math.log2(self.num_hashes))
        self.data = [None] * self.num_bins
        self.recursion_limit = int(8 * math.log2(self.num_bins))
        self.insert_index = randint(0, self.num_hashes - 1)
        self.depth = 0
        self.failed = False

    def _hash_location(self, seed, item):
        item_left = item >> self.output_bits
        item_right = item & self.mask
        hashed = mmh3.hash(str(item_left), seed, signed=False) >> (32 - self.output_bits)
        return hashed ^ item_right

    def _combine_left_and_index(self, item, index):
        item_left = item >> self.output_bits
        return (item_left << self.log_num_hashes) + index

    def _extract_index(self, value):
        return value & ((1 << self.log_num_hashes) - 1)

    def _reconstruct_item(self, encoded, location, seed):
        item_left = encoded >> self.log_num_hashes
        hashed_left = mmh3.hash(str(item_left), seed, signed=False) >> (32 - self.output_bits)
        item_right = hashed_left ^ location
        return (item_left << self.output_bits) + item_right

    def _random_index_excluding(self, bound, exclude):
        value = randint(0, bound - 1)
        while value == exclude:
            value = randint(0, bound - 1)
        return value

    def insert(self, item: int):
        """
        Вставляет элемент в таблицу кукушки
        :param item: число
        """
        loc = self._hash_location(self.hash_seeds[self.insert_index], item)
        current_value = self.data[loc]
        self.data[loc] = self._combine_left_and_index(item, self.insert_index)

        if current_value is None:
            self.insert_index = randint(0, self.num_hashes - 1)
            self.depth = 0
        else:
            old_index = self._extract_index(current_value)
            self.insert_index = self._random_index_excluding(self.num_hashes, old_index)

            if self.depth < self.recursion_limit:
                self.depth += 1
                kicked_item = self._reconstruct_item(
                    current_value, loc, self.hash_seeds[old_index]
                )
                self.insert(kicked_item)
            else:
                self.failed = True

bin_capacity = calculate_bin_capacity()
