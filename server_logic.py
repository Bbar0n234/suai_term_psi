from math import log2

import pickle

import tenseal as ts

from config import hash_seeds, output_bits, number_of_hashes, sigma_max, alpha, plain_modulus, ell
from hashing import SimpleHash, bin_capacity
from utils import coeffs_from_roots, power_reconstruct

import numpy as np


def preprocess_sender(sender_set):
    """Предварительная обработка множества отправителя"""
    # Инициализируем хеш таблицу и заполняем элементами
    simple_hash = SimpleHash(hash_seeds, output_bits, bin_capacity)
    for item in sender_set:
        for h_idx in range(number_of_hashes):
            simple_hash.insert(item, h_idx)

    # Значение для заполнения пустых ячеек
    dummy_value = 2 ** (sigma_max - output_bits + (int(log2(number_of_hashes)) + 1)) + 1

    # Заполняем пустые ячейки фиктивными значениями
    for bin_idx in range(2 ** output_bits):
        for pos in range(bin_capacity):
            if simple_hash.hashed_data[bin_idx][pos] is None:
                simple_hash.hashed_data[bin_idx][pos] = dummy_value

    # Разделяем корзины на миникорзины и вычисляем коэффициенты полиномов
    poly_coeffs = []
    minibin_capacity = bin_capacity // alpha
    for bin_idx in range(2 ** output_bits):
        bin_coeffs = []
        for mini_idx in range(alpha):
            # Получаем элементы текущей миникорзины
            roots = [simple_hash.hashed_data[bin_idx][minibin_capacity * mini_idx + r] 
                    for r in range(minibin_capacity)]
            # Вычисляем коэффициенты полинома с корнями в элементах миникорзины
            bin_coeffs += coeffs_from_roots(roots, plain_modulus).tolist()
        poly_coeffs.append(bin_coeffs)

    return {
        "poly_coeffs": poly_coeffs,
        "minibin_capacity": minibin_capacity
    }


def process_query(query_serialized_ctx, sender_state):
    """Обработка запроса от клиента"""
    poly_coeffs = sender_state["poly_coeffs"]
    minibin_capacity = sender_state["minibin_capacity"]

    # Распаковываем контекст и зашифрованный запрос
    public_ctx_ser, enc_query_serial = query_serialized_ctx
    ctx = ts.context_from(public_ctx_ser)

    # Параметры оконного метода
    base = 2 ** ell
    logB_ell = int(log2(minibin_capacity) / ell) + 1

    # Восстанавливаем матрицу шифротекстов
    enc_query = [[None for _ in range(logB_ell)] for _ in range(base - 1)]
    for i in range(base - 1):
        for j in range(logB_ell):
            if enc_query_serial[i][j] is not None:
                enc_query[i][j] = ts.bfv_vector_from(ctx, enc_query_serial[i][j])

    # Собираем все степени y
    all_enc_powers = [None] * minibin_capacity
    for i in range(base - 1):
        for j in range(logB_ell):
            exp = (i + 1) * base ** j - 1
            if exp < minibin_capacity:
                all_enc_powers[exp] = enc_query[i][j]

    # Восстанавливаем недостающие степени
    for k in range(minibin_capacity):
        if all_enc_powers[k] is None:
            all_enc_powers[k] = power_reconstruct(enc_query, k + 1)

    # Переворачиваем для соответствия порядку в Tenseal
    all_enc_powers = all_enc_powers[::-1]

    # Вычисляем скалярные произведения с коэффициентами полиномов
    transposed_coeffs = np.transpose(poly_coeffs).tolist()
    server_answers = []

    for block in range(alpha):
        # Начинаем с коэффициента при старшей степени
        result = all_enc_powers[0]
        for j in range(1, minibin_capacity):
            coeff = transposed_coeffs[(minibin_capacity + 1) * block + j]
            result = result + coeff * all_enc_powers[j]
        
        # Добавляем свободный член полинома
        result = result + transposed_coeffs[(minibin_capacity + 1) * block + minibin_capacity]
        server_answers.append(result.serialize())

    return pickle.dumps(server_answers)