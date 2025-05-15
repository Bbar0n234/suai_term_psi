from math import log2

import pickle

import tenseal as ts

from config import hash_seeds, output_bits, number_of_hashes, sigma_max, alpha, plain_modulus, ell
from hashing import SimpleHash, bin_capacity
from utils import coeffs_from_roots, power_reconstruct

import numpy as np


def preprocess_sender(sender_set):

    # 1. Заполняем SimpleHash элементами
    SH = SimpleHash(hash_seeds, output_bits, bin_capacity)
    for item in sender_set:
        for h in range(number_of_hashes):
            SH.insert(item, h)

    dummy = 2 ** (sigma_max - output_bits + (int(log2(number_of_hashes))+1)) + 1

    # 2. Заполняем SimpleHash dummy-элементами 
    for b in range(2 ** output_bits):
        for j in range(bin_capacity):
            if SH.hashed_data[b][j] is None:
                SH.hashed_data[b][j] = dummy

    # 3 Делим каждую корзину на α мини‑корзин
    poly_coeffs = []
    minibin_capacity = bin_capacity // alpha
    for b in range(2 ** output_bits):
        coeffs = []
        for j in range(alpha):
            roots = [SH.hashed_data[b][minibin_capacity*j + r] for r in range(minibin_capacity)]
            coeffs += coeffs_from_roots(roots, plain_modulus).tolist()
        poly_coeffs.append(coeffs)

    return {
        "poly_coeffs": poly_coeffs,
        "minibin_capacity": minibin_capacity
    }


def process_query(query_serialized_ctx, sender_state):
    """
    query_serialized_ctx  — bytes‑объект, полученный от клиента
                            (pickle: (public_ctx_serialized, enc_query_matrix))
    sender_state          — объект, вернувшийся из preprocess_sender().
    Возвращает bytes (pickle) — список сериализованных шифротекстов‑ответов.
    """
    # ────────────────────────────────────────────────────────────────
    poly_coeffs      = sender_state["poly_coeffs"]
    minibin_capacity = sender_state["minibin_capacity"]

    # ➊ контекст ГШ и расшифровка матрицы шифротекстов y^(k)
    public_ctx_ser, enc_query_serial = query_serialized_ctx # Здесь непонятно что за tuple
    ctx = ts.context_from(public_ctx_ser)

    # вычислим параметры окна
    base       = 2 ** ell
    logB_ell   = int(log2(minibin_capacity) / ell) + 1

    # раскладываем в матрицу ciphertext‑ов
    enc_query = [[None for _ in range(logB_ell)] for _ in range(base - 1)]
    for i in range(base - 1):
        for j in range(logB_ell):
            if enc_query_serial[i][j] is not None:
                enc_query[i][j] = ts.bfv_vector_from(ctx, enc_query_serial[i][j])

    # ➋ собираем все y, y², …, y^{B-1}
    all_enc_powers = [None] * minibin_capacity
    for i in range(base - 1):
        for j in range(logB_ell):
            exp = (i + 1) * base ** j - 1
            if exp < minibin_capacity:
                all_enc_powers[exp] = enc_query[i][j]

    # восстанавливаем «дырки» через гомоморфное power_reconstruct
    for k in range(minibin_capacity):
        if all_enc_powers[k] is None:
            all_enc_powers[k] = power_reconstruct(enc_query, k + 1)

    # Tensil‑векторы идут от y^{B-1} к y, поэтому разворачиваем
    all_enc_powers = all_enc_powers[::-1]

    # ➌ домножение на коэффициенты полиномов и скалярные произведения
    transposed_coeffs = np.transpose(poly_coeffs).tolist()
    server_ans_serial = []

    for block in range(alpha):
        dot = all_enc_powers[0]                        # коэффициент 1
        for j in range(1, minibin_capacity):
            coeff = transposed_coeffs[(minibin_capacity + 1) * block + j]
            dot   = dot + coeff * all_enc_powers[j]
        # свободный член полинома (=последний коэффициент)
        dot = dot + transposed_coeffs[(minibin_capacity + 1) * block + minibin_capacity]
        server_ans_serial.append(dot.serialize())

    return pickle.dumps(server_ans_serial)