from hashing import bin_capacity
from math import log2
import numpy as np
from config import ell, alpha, plain_modulus

base = 2 ** ell
minibin_capacity = int(bin_capacity / alpha)# minibin_capacity = B / alpha
logB_ell = int(log2(minibin_capacity) / ell) + 1 # <= 2 ** HE.depth = 16
t = plain_modulus

def int2base(n, b):
    '''
    :param n: an integer
    :param b: a base
    :return: an array of coefficients from the base decomposition of an integer n with coeff[i] being the coeff of b ** i
    '''
    if n < b:
        return [n]
    else:
        return [n % b] + int2base(n // b, b)

# We need len(powers_vec) <= 2 ** HE.depth
def low_depth_multiplication(vector):
    '''
    :param: vector: a vector of integers
    :return: an integer representing the multiplication of all the integers from vector
    '''
    L = len(vector)
    if L == 1:
        return vector[0]
    if L == 2:
        return(vector[0] * vector[1])
    else:
        if (L % 2 == 1):
            vec = []
            for i in range(int(L / 2)):
                vec.append(vector[2 * i] * vector[2 * i + 1])
            vec.append(vector[L-1])
            return low_depth_multiplication(vec)
        else:
            vec = []
            for i in range(int(L / 2)):
                vec.append(vector[2 * i] * vector[2 * i + 1])
            return low_depth_multiplication(vec)

def power_reconstruct(window, exponent):
    '''
    :param: window: a matrix of integers as powers of y; in the protocol is the matrix with entries window[i][j] = [y ** i * base ** j]
    :param: exponent: an integer, will be an exponent <= logB_ell
    :return: y ** exponent
    '''
    e_base_coef = int2base(exponent, base)
    necessary_powers = [] #len(necessary_powers) <= 2 ** HE.depth
    j = 0
    for x in e_base_coef:
        if x >= 1:
            necessary_powers.append(window[x - 1][j])
        j = j + 1
    return low_depth_multiplication(necessary_powers)


def windowing(y, bound, modulus):
    '''
    :param: y: an integer
    :param bound: an integer
    :param modulus: a modulus integer
    :return: a matrix associated to y, where we put y ** (i+1)*base ** j mod modulus in the (i,j) entry, as long as the exponent of y is smaller than some bound
    '''
    windowed_y = [[None for j in range(logB_ell)] for i in range(base-1)]
    for j in range(logB_ell):
        for i in range(base-1):
            if ((i+1) * base ** j - 1 < bound):
                windowed_y[i][j] = pow(y, (i+1) * base ** j, modulus)
    return windowed_y

def coeffs_from_roots(roots, modulus):
    '''
    :param roots: an array of integers
    :param modulus: an integer
    :return: coefficients of a polynomial whose roots are roots modulo modulus
    '''
    coefficients = np.array(1, dtype=np.int64)
    for r in roots:
        coefficients = np.convolve(coefficients, [1, -r]) % modulus
    return coefficients


def decompose_to_base(n: int, base: int) -> list[int]:
    """
    Разлагает число n в систему счисления с основанием base.
    :param n: число для разложения
    :param base: основание
    :return: список коэффициентов [c0, c1, ..., ck] таких, что n = c0 + c1*base + ...
    """
    if n < base:
        return [n]
    return [n % base] + decompose_to_base(n // base, base)

def multiply_tree_style(elements: list[int]) -> int:
    """
    Вычисляет произведение всех элементов в списке с логарифмической глубиной (рекурсивно, попарно).
    :param elements: список чисел
    :return: произведение всех чисел
    """
    length = len(elements)
    if length == 1:
        return elements[0]
    if length == 2:
        return elements[0] * elements[1]

    # разбиваем на пары и перемножаем
    reduced = [
        elements[2 * i] * elements[2 * i + 1]
        for i in range(length // 2)
    ]
    if length % 2 == 1:
        reduced.append(elements[-1])
    return multiply_tree_style(reduced)

def reconstruct_power(window_matrix: list[list[int]], exponent: int, base: int, modulus: int) -> int:
    """
    Восстанавливает y^exponent, используя предварительно вычисленную оконную матрицу.
    :param window_matrix: матрица [y**((i+1)*base**j)] (base-1 x logB_ell)
    :param exponent: степень, которую нужно восстановить
    :param base: основание окна
    :param modulus: модуль
    :return: y^exponent mod modulus
    """
    base_coeffs = decompose_to_base(exponent, base)
    result_terms = [
        window_matrix[coeff - 1][j]
        for j, coeff in enumerate(base_coeffs) if coeff > 0
    ]
    return multiply_tree_style(result_terms) % modulus

def generate_window_matrix(y: int, max_exponent: int, modulus: int, base: int, log_window_depth: int) -> list[list[int]]:
    """
    Строит матрицу степеней y^( (i+1) * base^j ) % modulus.
    :param y: основание степени
    :param max_exponent: максимальная допустимая степень (ограничение по глубине)
    :param modulus: модуль
    :param base: основание окна
    :param log_window_depth: логарифм глубины окна (logB_ell)
    :return: матрица степеней
    """
    rows = base - 1
    cols = log_window_depth
    matrix = [[None for _ in range(cols)] for _ in range(rows)]
    for j in range(cols):
        for i in range(rows):
            exponent = (i + 1) * base ** j
            if exponent - 1 < max_exponent:
                matrix[i][j] = pow(y, exponent, modulus)
    return matrix