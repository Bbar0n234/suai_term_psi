from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import pickle
import uvicorn
import os
from typing import List, Optional
import io
import traceback
import asyncio

from client_logic import generate_query, finalize_answer
from server_logic import preprocess_sender, process_query
from data_generator import generate_sets_to_files

app = FastAPI(title="PSI - Private Set Intersection")

# Создадим директории для шаблонов и статики, если их нет
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Настраиваем статические файлы и шаблоны
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Модель для данных пользовательских множеств
class SetInput(BaseModel):
    sender_set: List[int]
    receiver_set: List[int]

class SetFileUpload:
    def __init__(self, sender_file: UploadFile, receiver_file: UploadFile):
        self.sender_file = sender_file
        self.receiver_file = receiver_file

# Максимальный размер файла (в байтах) - 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

# Главная страница
@app.get("/", response_class=HTMLResponse)
async def get_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Эндпоинт для вычисления пересечения множеств по введенным данным
@app.post("/calculate-intersection")
async def calculate_intersection(
    sender_set: str = Form(...),
    receiver_set: str = Form(...)
):
    try:
        # Преобразуем строки в списки целых чисел
        sender_set = [int(x.strip()) for x in sender_set.split(",")]
        receiver_set = [int(x.strip()) for x in receiver_set.split(",")]
        
        # Запускаем PSI-протокол
        srv_state = preprocess_sender(sender_set)
        query_bytes, client_state = generate_query(receiver_set)
        answer_bytes = process_query(pickle.loads(query_bytes), srv_state)
        intersection = finalize_answer(answer_bytes, client_state)
        
        return {
            "success": True,
            "sender_size": len(sender_set),
            "receiver_size": len(receiver_set),
            "intersection_size": len(intersection),
            "intersection": list(intersection)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# Эндпоинт для вычисления пересечения множеств с файлами
@app.post("/calculate-intersection-files")
async def calculate_intersection_files(
    sender_file: UploadFile = File(...),
    receiver_file: UploadFile = File(...),
    use_default_files: bool = Form(False)
):
    try:
        # Если указано использовать файлы по умолчанию
        if use_default_files:
            print("Используем файлы по умолчанию: sender.txt и receiver.txt")
            try:
                # Проверяем, существуют ли файлы
                if not os.path.exists("sender.txt") or not os.path.exists("receiver.txt"):
                    # Если нет, генерируем их
                    print("Файлы по умолчанию не найдены, генерируем...")
                    generate_sets_to_files()
                
                # Читаем файлы
                with open("sender.txt", "r") as f:
                    sender_content = f.read().encode()
                
                with open("receiver.txt", "r") as f:
                    receiver_content = f.read().encode()
                
                print(f"Файлы по умолчанию прочитаны: sender.txt ({len(sender_content)} байт), receiver.txt ({len(receiver_content)} байт)")
            except Exception as e:
                error_msg = str(e)
                print(f"Ошибка при чтении файлов по умолчанию: {error_msg}")
                return JSONResponse(
                    status_code=500,
                    content={"success": False, "error": f"Ошибка при чтении файлов по умолчанию: {error_msg}"}
                )
        else:
            # Проверяем размер файлов (если content_length доступен)
            if sender_file.size and sender_file.size > MAX_FILE_SIZE:
                return JSONResponse(
                    status_code=413,
                    content={"success": False, "error": f"Файл отправителя слишком большой. Максимальный размер: {MAX_FILE_SIZE} байт"}
                )
                
            if receiver_file.size and receiver_file.size > MAX_FILE_SIZE:
                return JSONResponse(
                    status_code=413,
                    content={"success": False, "error": f"Файл получателя слишком большой. Максимальный размер: {MAX_FILE_SIZE} байт"}
                )
                
            # Читаем данные из файлов
            sender_content = await sender_file.read()
            receiver_content = await receiver_file.read()
            
            # Добавляем отладочную информацию
            print(f"Sender file name: {sender_file.filename}, size: {len(sender_content)}")
            print(f"Receiver file name: {receiver_file.filename}, size: {len(receiver_content)}")
            
            # Проверяем размер файлов
            if len(sender_content) > MAX_FILE_SIZE or len(receiver_content) > MAX_FILE_SIZE:
                return JSONResponse(
                    status_code=413,
                    content={"success": False, "error": f"Файл слишком большой. Максимальный размер: {MAX_FILE_SIZE} байт"}
                )
        
        # Преобразуем содержимое файлов в списки целых чисел
        try:
            sender_set = [int(x.strip()) for x in sender_content.decode().split("\n") if x.strip()]
            receiver_set = [int(x.strip()) for x in receiver_content.decode().split("\n") if x.strip()]
        except ValueError as e:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": f"Неверный формат данных в файлах. Убедитесь, что файлы содержат только целые числа (по одному в строке): {str(e)}"}
            )
        
        if not sender_set or not receiver_set:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Один или оба файла пусты или не содержат целых чисел"}
            )
            
        # Добавляем отладочную информацию
        print(f"Sender set size: {len(sender_set)}")
        print(f"Receiver set size: {len(receiver_set)}")
        
        # Добавляем проверку на слишком большие множества
        if len(sender_set) > 100000 or len(receiver_set) > 100000:
            return JSONResponse(
                status_code=413,
                content={"success": False, "error": "Множества слишком большие. Максимальный размер множества: 100,000 элементов"}
            )
        
        # Дополнительно ограничиваем размер множеств для удобства обработки
        # Если размеры больше, чем значения в config, ограничиваем их
        from config import sender_size as max_sender_size, receiver_size as max_receiver_size
        
        if len(sender_set) > max_sender_size:
            print(f"Ограничиваем размер множества отправителя с {len(sender_set)} до {max_sender_size}")
            sender_set = sender_set[:max_sender_size]
            
        if len(receiver_set) > max_receiver_size:
            print(f"Ограничиваем размер множества получателя с {len(receiver_set)} до {max_receiver_size}")
            receiver_set = receiver_set[:max_receiver_size]
        
        # Запускаем PSI-протокол с таймаутом
        try:
            # Создаем задачу для вычисления PSI
            srv_state = preprocess_sender(sender_set)
            query_bytes, client_state = generate_query(receiver_set)
            answer_bytes = process_query(pickle.loads(query_bytes), srv_state)
            intersection = finalize_answer(answer_bytes, client_state)
            
            # Добавляем отладочную информацию
            print(f"Intersection size: {len(intersection)}")
            
            result = {
                "success": True,
                "sender_size": len(sender_set),
                "receiver_size": len(receiver_set),
                "intersection_size": len(intersection),
                "intersection": list(intersection)
            }
            
            # Добавляем отладочную информацию
            print(f"Result successfully generated")
            
            return result
        
        except Exception as e:
            error_msg = str(e)
            print(f"Error in PSI computation: {error_msg}")
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": f"Ошибка при вычислении пересечения: {error_msg}"}
            )
            
    except Exception as e:
        error_msg = str(e)
        traceback_str = traceback.format_exc()
        print(f"Error in calculate_intersection_files: {error_msg}")
        print(f"Traceback: {traceback_str}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Неожиданная ошибка: {error_msg}"}
        )

# Эндпоинт для генерации тестовых множеств
@app.get("/generate-test-sets")
async def generate_test_sets():
    try:
        generate_sets_to_files()
        sender_set = [int(x.strip()) for x in open("sender.txt")]
        receiver_set = [int(x.strip()) for x in open("receiver.txt")]
        
        return {
            "success": True,
            "sender_size": len(sender_set),
            "receiver_size": len(receiver_set),
            "message": "Тестовые множества успешно сгенерированы"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# Запуск сервера
if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True) 