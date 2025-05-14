from math import log2

# Размеры множеств элементов сервера, клиента и пересечения соответственно
sender_size = 2 ** 16
receiver_size = 4000
intersection_size = 3500

# Сиды для хэш-функций в CuckooHash и SimpleHash
hash_seeds = [123456789, 1011121, 17181920]

# the number of hashes we use for simple/Cuckoo hashing
number_of_hashes = len(hash_seeds)

# output_bits - количество выходных бит хэш функции (mmh3)
# mask_of_power_of_2 - битовая маска для выделения младших output_bits бит.
output_bits = 13
mask_of_power_of_2 = 2 ** output_bits - 1

# encryption parameters of the BFV scheme: the plain modulus and the polynomial modulus degree
plain_modulus = 536903681
poly_modulus_degree = 2 ** 13

# расчёт максимально возможной длины элементов БД (в битах), которые можно корректно закодировать в схеме
sigma_max = int(log2(plain_modulus)) + output_bits - (int(log2(number_of_hashes)) + 1)

# Количество мини корзин, на которые будет происходить разбиение
alpha = 16

# windowing параметр, определяет, как значения будут возводиться в степени для последующих операций
ell = 2

oprf_client_key = 12345678910111213141516171819222222222222
oprf_server_key = 1234567891011121314151617181920