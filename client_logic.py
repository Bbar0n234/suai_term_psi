from config import hash_seeds, output_bits, sigma_max, alpha, plain_modulus, \
    number_of_hashes, poly_modulus_degree, ell
import tenseal as ts

from utils import windowing
from math import log2
from hashing import CuckooHash, bin_capacity
import pickle


def generate_query(receiver_set):

    base = 2 ** ell
    minibin_capacity = bin_capacity // alpha
    logB_ell = int(log2(minibin_capacity) / ell) + 1

    # === 2. Cuckoo Hash + dummy ===
    CH = CuckooHash(hash_seeds, output_bits)
    
    for x in receiver_set:
        CH.insert(x)

    dummy = 2 ** (sigma_max - output_bits + (int(log2(number_of_hashes))+1))

    for i in range(CH.num_bins):
        if CH.data[i] is None:
            CH.data[i] = dummy

    # === 3. Окно степеней + шифрование ===
    minibin_capacity = bin_capacity // alpha
    client_windows   = [windowing(x, minibin_capacity, plain_modulus)
                        for x in CH.data]

    priv_ctx = ts.context(
        ts.SCHEME_TYPE.BFV,
        poly_modulus_degree=poly_modulus_degree,
        plain_modulus=plain_modulus
    )
    pub_ctx_serial = priv_ctx.serialize(save_secret_key=False)

    enc_query = [[None for _ in range(logB_ell)] for _ in range(base - 1)]
    plain_vec = [0] * CH.num_bins  # вектор значений перед шифрованием

    for j in range(logB_ell):
        for i in range(base - 1):
            if (i + 1) * (base ** j) - 1 < minibin_capacity:
                for k in range(CH.num_bins):
                    plain_vec[k] = client_windows[k][i][j]
                enc_query[i][j] = ts.bfv_vector(priv_ctx, plain_vec).serialize()

    query_bytes = pickle.dumps((pub_ctx_serial, enc_query))

    # client_state нужен для финального шага
    client_state = {
        "priv_ctx": priv_ctx,
        "CH": CH,
        "client_windows": client_windows,
        "receiver_set": receiver_set,
    }
    return query_bytes, client_state


def finalize_answer(answer_bytes, client_state):
    priv_ctx       = client_state["priv_ctx"]
    CH             = client_state["CH"]

    serv_answer = pickle.loads(answer_bytes)    # список сериализованных ct
    decrypted   = [ts.bfv_vector_from(priv_ctx, ct).decrypt() for ct in serv_answer]

    # === пост‑обработка: извлекаем нули и восстанавливаем элементы ===Ы
    intersection    = set()
    for alpha_idx, plain_vec in enumerate(decrypted):
        for idx, val in enumerate(plain_vec):
            if val == 0:
                packed = CH.data[idx]

                seed_idx = CH._extract_index(packed)
                item = CH._reconstruct_item(packed, idx, CH.hash_seeds[seed_idx])

                intersection.add(item)
    return intersection