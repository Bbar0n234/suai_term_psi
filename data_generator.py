from random import sample
from config import sender_size, receiver_size, intersection_size

def generate_sets_to_files(sender_path="sender.txt", receiver_path="receiver.txt"):
    """
    Генерирует sender_set и receiver_set с заданным пересечением и сохраняет их в текстовые файлы (каждый элемент на новой строке).
    """
    # Используем большое число
    universe_bound = 2147483629765874212
    # Создаем общий пул элементов для обоих множеств
    element_pool = sample(range(universe_bound), sender_size + receiver_size)

    intersection = element_pool[:intersection_size]

    sender_set = intersection + element_pool[intersection_size: sender_size]
    receiver_set = intersection + element_pool[sender_size: sender_size - intersection_size + receiver_size]

    with open(sender_path, "w") as f:
        f.write("\n".join(map(str, sender_set)))

    with open(receiver_path, "w") as f:
        f.write("\n".join(map(str, receiver_set)))