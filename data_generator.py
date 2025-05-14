from random import sample
from config import sender_size, receiver_size, intersection_size

def generate_sets_to_files(sender_path="sender.txt", receiver_path="receiver.txt"):
    """
    Генерирует sender_set и receiver_set с заданным пересечением и сохраняет их в текстовые файлы.
    Каждый элемент на новой строке.
    """
    max_value = 2 ** 63 - 1
    disjoint_union = sample(range(max_value), sender_size + receiver_size)

    intersection = disjoint_union[:intersection_size]

    sender_set = intersection + disjoint_union[intersection_size: sender_size]
    receiver_set = intersection + disjoint_union[sender_size: sender_size - intersection_size + receiver_size]

    with open(sender_path, "w") as f:
        f.write("\n".join(map(str, sender_set)))

    with open(receiver_path, "w") as f:
        f.write("\n".join(map(str, receiver_set)))