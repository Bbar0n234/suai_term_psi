from hashing import bin_capacity
from math import log2
import numpy as np
from config import ell, alpha, plain_modulus

base = 2 ** ell
minibin_capacity = bin_capacity // alpha
logB_ell = int(log2(minibin_capacity) / ell) + 1
t = plain_modulus

def int2base(number, base_value):
    """
    Разложение числа по основанию
    """
    if number < base_value:
        return [number]
    else:
        return [number % base_value] + int2base(number // base_value, base_value)


def low_depth_multiplication(vector):
    """
    Вычисление произведения элементов вектора с логарифмической глубиной схемы
    """
    length = len(vector)
    if length == 1:
        return vector[0]
    if length == 2:
        return vector[0] * vector[1]
    else:
        if length % 2 == 1:
            new_vec = []
            for i in range(length // 2):
                new_vec.append(vector[2 * i] * vector[2 * i + 1])
            new_vec.append(vector[length - 1])
            return low_depth_multiplication(new_vec)
        else:
            new_vec = []
            for i in range(length // 2):
                new_vec.append(vector[2 * i] * vector[2 * i + 1])
            return low_depth_multiplication(new_vec)

def power_reconstruct(window, exponent):
    """
    Восстановление степени y в exponent используя оконный метод
    """
    base_coeffs = int2base(exponent, base)
    needed_powers = []
    j = 0
    for coeff in base_coeffs:
        if coeff >= 1:
            needed_powers.append(window[coeff - 1][j])
        j += 1
    return low_depth_multiplication(needed_powers)


def windowing(y, bound, modulus):
    """
    Создание матрицы степеней y для оконного метода
    """
    windowed_y = [[None for j in range(logB_ell)] for i in range(base - 1)]
    for j in range(logB_ell):
        for i in range(base - 1):
            if (i + 1) * base ** j - 1 < bound:
                windowed_y[i][j] = pow(y, (i + 1) * base ** j, modulus)
    return windowed_y

def coeffs_from_roots(roots, modulus):
    """
    Вычисление коэффициентов полинома по его корням
    """
    coefficients = np.array(1, dtype=np.int64)
    for root in roots:
        coefficients = np.convolve(coefficients, [1, -root]) % modulus
    return coefficients


def decompose_to_base(n, base_value):
    """
    Разложение числа n в систему счисления с основанием base
    """
    if n < base_value:
        return [n]
    return [n % base_value] + decompose_to_base(n // base_value, base_value)

def multiply_tree_style(elements):
    """
    Вычисление произведения элементов с логарифмической глубиной
    """
    length = len(elements)
    if length == 1:
        return elements[0]
    if length == 2:
        return elements[0] * elements[1]

    # Разбиваем на пары и перемножаем
    reduced = [
        elements[2 * i] * elements[2 * i + 1]
        for i in range(length // 2)
    ]
    if length % 2 == 1:
        reduced.append(elements[-1])
    return multiply_tree_style(reduced)

def reconstruct_power(window_matrix, exponent, base_value, modulus):
    """
    Восстановление степени y в exponent по оконной матрице
    """
    base_coeffs = decompose_to_base(exponent, base_value)
    result_terms = [
        window_matrix[coeff - 1][j]
        for j, coeff in enumerate(base_coeffs) if coeff > 0
    ]
    return multiply_tree_style(result_terms) % modulus

def generate_window_matrix(y, max_exponent, modulus, base_value, log_window_depth):
    """
    Построение матрицы степеней y для оконного метода
    """
    rows = base_value - 1
    cols = log_window_depth
    matrix = [[None for _ in range(cols)] for _ in range(rows)]
    for j in range(cols):
        for i in range(rows):
            exponent = (i + 1) * base_value ** j
            if exponent - 1 < max_exponent:
                matrix[i][j] = pow(y, exponent, modulus)
    return matrix