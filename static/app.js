// Функция для загрузки страницы
document.addEventListener('DOMContentLoaded', function() {
    // Получаем формы и элементы на странице
    const manualForm = document.getElementById('manual-form');
    const fileForm = document.getElementById('file-form');
    const generateTestBtn = document.getElementById('generate-test-btn');
    const loading = document.getElementById('loading');
    const resultContainer = document.getElementById('result-container');
    const testInfo = document.getElementById('test-info');
    
    // Добавим элемент для отображения ошибок
    const errorContainer = document.createElement('div');
    errorContainer.className = 'alert alert-danger mt-3';
    errorContainer.style.display = 'none';
    document.querySelector('.container').appendChild(errorContainer);

    // Обработчик для формы с ручным вводом
    manualForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const senderSet = document.getElementById('sender-set').value;
        const receiverSet = document.getElementById('receiver-set').value;
        
        if (!senderSet || !receiverSet) {
            showAlert('Пожалуйста, заполните оба множества');
            return;
        }
        
        toggleLoading(true);
        
        try {
            const formData = new FormData();
            formData.append('sender_set', senderSet);
            formData.append('receiver_set', receiverSet);
            
            const response = await fetch('/calculate-intersection', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            displayResult(result);
        } catch (error) {
            console.error('Ошибка:', error);
            showAlert('Произошла ошибка при вычислении пересечения');
        } finally {
            toggleLoading(false);
        }
    });

    // Обработчик для формы с загрузкой файлов
    fileForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const senderFile = document.getElementById('sender-file').files[0];
        const receiverFile = document.getElementById('receiver-file').files[0];
        const useDefaultFiles = document.getElementById('use-default-files').checked;
        
        // Сбрасываем предыдущие сообщения об ошибках
        errorContainer.style.display = 'none';
        
        // Если не используем файлы по умолчанию, проверяем загруженные файлы
        if (!useDefaultFiles) {
            if (!senderFile || !receiverFile) {
                showError('Пожалуйста, выберите оба файла или используйте файлы по умолчанию');
                return;
            }
            
            // Проверка размера файла (10MB максимум)
            const MAX_FILE_SIZE = 10 * 1024 * 1024;
            if (senderFile.size > MAX_FILE_SIZE || receiverFile.size > MAX_FILE_SIZE) {
                showError('Файл слишком большой. Максимальный размер файла: 10MB.');
                return;
            }
            
            // Проверка формата файла
            if (!senderFile.name.endsWith('.txt') && !senderFile.name.endsWith('.csv') ||
                !receiverFile.name.endsWith('.txt') && !receiverFile.name.endsWith('.csv')) {
                showError('Пожалуйста, загрузите файлы в формате TXT или CSV.');
                return;
            }
        }
        
        toggleLoading(true, useDefaultFiles ? 
            'Обработка файлов по умолчанию...' : 
            'Загрузка и обработка файлов...');
        
        try {
            const formData = new FormData();
            
            if (!useDefaultFiles) {
                formData.append('sender_file', senderFile);
                formData.append('receiver_file', receiverFile);
            } else {
                // Если используем файлы по умолчанию, всё равно нужно добавить пустые файлы
                // (FastAPI требует все обязательные поля даже если мы не будем их использовать)
                const emptyBlob = new Blob([''], { type: 'text/plain' });
                formData.append('sender_file', emptyBlob, 'empty.txt');
                formData.append('receiver_file', emptyBlob, 'empty.txt');
                formData.append('use_default_files', 'true');
            }
            
            const response = await fetch('/calculate-intersection-files', {
                method: 'POST',
                body: formData
            });
            
            // Проверяем статус ответа
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `Ошибка сервера: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || 'Неизвестная ошибка при обработке данных');
            }
            
            // Явно устанавливаем значения элементов
            errorContainer.style.display = 'none';
            document.getElementById('sender-size').textContent = result.sender_size;
            document.getElementById('receiver-size').textContent = result.receiver_size;
            document.getElementById('intersection-size').textContent = result.intersection_size;
            document.getElementById('intersection-result').value = result.intersection.join(', ');
            
            // Явно отображаем контейнер результатов
            resultContainer.style.display = 'block';
            
            // Прокрутим страницу к результатам
            resultContainer.scrollIntoView({ behavior: 'smooth' });
        } catch (error) {
            console.error('Ошибка:', error);
            showError(`Произошла ошибка при вычислении пересечения: ${error.message}`);
        } finally {
            toggleLoading(false);
        }
    });

    // Обработчик события изменения состояния чекбокса "использовать файлы по умолчанию"
    document.getElementById('use-default-files').addEventListener('change', function(e) {
        const useDefault = e.target.checked;
        const senderFileInput = document.getElementById('sender-file');
        const receiverFileInput = document.getElementById('receiver-file');
        
        // Если выбрано использование файлов по умолчанию, делаем поля загрузки неактивными
        senderFileInput.disabled = useDefault;
        receiverFileInput.disabled = useDefault;
        
        if (useDefault) {
            // Очищаем поля загрузки
            senderFileInput.value = '';
            receiverFileInput.value = '';
        }
    });

    // Обработчик для кнопки генерации тестовых данных
    generateTestBtn.addEventListener('click', async function() {
        testInfo.textContent = 'Генерация тестовых данных...';
        
        try {
            const response = await fetch('/generate-test-sets');
            const result = await response.json();
            
            if (result.success) {
                testInfo.innerHTML = `
                    <div class="alert alert-success">
                        ${result.message}<br>
                        Размер множества отправителя: ${result.sender_size}<br>
                        Размер множества получателя: ${result.receiver_size}
                    </div>
                `;
            } else {
                testInfo.innerHTML = `
                    <div class="alert alert-danger">
                        Ошибка: ${result.error}
                    </div>
                `;
            }
        } catch (error) {
            console.error('Ошибка:', error);
            testInfo.innerHTML = `
                <div class="alert alert-danger">
                    Произошла ошибка при генерации тестовых данных
                </div>
            `;
        }
    });

    // Вспомогательные функции
    function toggleLoading(show, message = 'Вычисление пересечения множеств...') {
        loading.style.display = show ? 'block' : 'none';
        
        // Если показываем лоадер, скрываем результаты
        // Но когда скрываем лоадер, НЕ скрываем результаты
        if (show) {
            resultContainer.style.display = 'none';
        }
        
        errorContainer.style.display = 'none';
        
        // Обновляем текст сообщения загрузки
        const loadingMessage = loading.querySelector('p');
        if (loadingMessage) {
            loadingMessage.textContent = message;
        }
    }

    function displayResult(result) {
        if (result.success) {
            errorContainer.style.display = 'none';
            
            // Проверим существование элементов перед установкой значений
            const senderSize = document.getElementById('sender-size');
            const receiverSize = document.getElementById('receiver-size');
            const intersectionSize = document.getElementById('intersection-size');
            const intersectionResult = document.getElementById('intersection-result');
            
            if (!senderSize || !receiverSize || !intersectionSize || !intersectionResult) {
                console.error('Не все элементы найдены для отображения результата');
                return;
            }
            
            senderSize.textContent = result.sender_size;
            receiverSize.textContent = result.receiver_size;
            intersectionSize.textContent = result.intersection_size;
            intersectionResult.value = result.intersection.join(', ');
            
            // Явно задаем display: block для контейнера результатов
            resultContainer.style.display = 'block';
            
            // Прокрутим страницу к результатам
            resultContainer.scrollIntoView({ behavior: 'smooth' });
        } else {
            console.error('Ошибка в результате:', result.error);
            showError('Ошибка: ' + result.error);
        }
    }

    function showError(message) {
        errorContainer.textContent = message;
        errorContainer.style.display = 'block';
        errorContainer.scrollIntoView({ behavior: 'smooth' });
    }

    function showAlert(message) {
        // Заменяем алерты на наш контейнер для ошибок
        showError(message);
    }

    // Инициализация подсказок
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
        new bootstrap.Tooltip(el);
    });
}); 