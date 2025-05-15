from config import hash_seeds, output_bits, sigma_max, alpha, plain_modulus, \
    number_of_hashes, poly_modulus_degree, ell
import tenseal as ts

from utils import windowing
from math import log2
from hashing import CuckooHash, bin_capacity
import pickle


def generate_query(receiver_set):
    """Генерация запроса на основе множества получателя"""
    # Параметры оконного метода
    base = 2 ** ell
    minibin_capacity = bin_capacity // alpha
    logB_ell = int(log2(minibin_capacity) / ell) + 1

    # Инициализируем и заполняем хеш-таблицу Кукушки
    cuckoo_hash = CuckooHash(hash_seeds, output_bits)
    for item in receiver_set:
        cuckoo_hash.insert(item)

    # Значение для заполнения пустых ячеек
    dummy_value = 2 ** (sigma_max - output_bits + (int(log2(number_of_hashes)) + 1))

    # Заполняем пустые ячейки фиктивными значениями
    for i in range(cuckoo_hash.num_bins):
        if cuckoo_hash.data[i] is None:
            cuckoo_hash.data[i] = dummy_value

    # Применяем оконный метод к элементам хештаблицы
    client_windows = [
        windowing(item, minibin_capacity, plain_modulus)
        for item in cuckoo_hash.data
    ]

    # Создаем контекст для гомоморфного шифрования
    private_ctx = ts.context(
        ts.SCHEME_TYPE.BFV,
        poly_modulus_degree=poly_modulus_degree,
        plain_modulus=plain_modulus
    )
    public_ctx_serial = private_ctx.serialize(save_secret_key=False)

    # Матрица для хранения зашифрованных значений
    enc_query = [[None for _ in range(logB_ell)] for _ in range(base - 1)]
    plain_vec = [0] * cuckoo_hash.num_bins 

    # Шифруем каждый элемент после применения оконного метода
    for j in range(logB_ell):
        for i in range(base - 1):
            if (i + 1) * (base ** j) - 1 < minibin_capacity:
                for k in range(cuckoo_hash.num_bins):
                    plain_vec[k] = client_windows[k][i][j]
                enc_query[i][j] = ts.bfv_vector(private_ctx, plain_vec).serialize()

    # Сериализуем запрос
    query_bytes = pickle.dumps((public_ctx_serial, enc_query))

    # Сохраняем состояние клиента для последующей обработки ответа
    client_state = {
        "priv_ctx": private_ctx,
        "cuckoo_hash": cuckoo_hash,
        "client_windows": client_windows,
        "receiver_set": receiver_set,
    }

    return query_bytes, client_state


def finalize_answer(answer_bytes, client_state):
    """Обработка ответа от сервера и формирование пересечения множеств"""
    private_ctx = client_state["priv_ctx"]
    cuckoo_hash = client_state["cuckoo_hash"]

    # Десериализуем и расшифровываем ответ сервера
    server_answer = pickle.loads(answer_bytes)
    decrypted = [ts.bfv_vector_from(private_ctx, ct).decrypt() for ct in server_answer]

    # Извлекаем нулевые значения и восстанавливаем элементы пересечения
    intersection = set()
    for block_idx, plain_vec in enumerate(decrypted):
        for bin_idx, val in enumerate(plain_vec):
            if val == 0:
                # Восстанавливаем исходный элемент из хеш-значения
                packed = cuckoo_hash.data[bin_idx]
                seed_idx = cuckoo_hash._extract_index(packed)
                item = cuckoo_hash._reconstruct_item(packed, bin_idx, cuckoo_hash.hash_seeds[seed_idx])
                intersection.add(item)
                
    return intersection