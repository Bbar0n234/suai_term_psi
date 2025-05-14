from data_generator import generate_sets_to_files
from client_logic   import generate_query, finalize_answer
from server_logic   import preprocess_sender, process_query
import pickle

# 1. генерим данные
generate_sets_to_files()
sender_set   = [int(x.strip()) for x in open("sender.txt")]
receiver_set = [int(x.strip()) for x in open("receiver.txt")]

# 2. сервер готовит state
srv_state = preprocess_sender(sender_set)

# 3. клиент формирует запрос
query_bytes, client_state = generate_query(receiver_set)

# 4. «обмен» байтами
answer_bytes = process_query(pickle.loads(query_bytes), srv_state)

# 5. клиент завершает
intersection = finalize_answer(answer_bytes, client_state)
print("│∩│ =", len(intersection))
