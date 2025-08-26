import shutil
import os
import requests
import json
import vk_api
from datetime import datetime, timedelta
import random

# Настройки
DOWNLOAD_FROM = "Postim"  # Папка с изображениями
MOVE_TO = "PostedAlready"  # Куда перемещать опубликованные изображения
GROUP_ID =  0 # ID группы
TIME_DELAY = 4  # Часы между постами
MAX_PHOTOS_PER_POST = 10  # Максимальное количество фото в одном посте

# Инициализация API
vk_session = vk_api.VkApi(token='')#Введите свой токен
vk = vk_session.get_api()

def upload_photos(group_id, image_paths):
    """Загружает несколько фото на сервер VK и возвращает список photo_id"""
    attachments = []
    
    # Получаем URL для загрузки
    upload_url = vk.photos.getWallUploadServer(group_id=group_id)['upload_url']
    
    for img_path in image_paths:
        try:
            # Загружаем фото на сервер
            with open(img_path, 'rb') as img_file:
                files = {'photo': (os.path.basename(img_path), img_file)}
                upload_response = requests.post(upload_url, files=files).json()
            
            if 'photo' not in upload_response:
                print(f"Ошибка загрузки {img_path}: неверный ответ сервера")
                continue
                
            # Сохраняем фото в группе
            save_response = vk.photos.saveWallPhoto(
                group_id=group_id,
                photo=upload_response['photo'],
                server=upload_response['server'],
                hash=upload_response['hash']
            )[0]
            
            photo_id = f"photo{save_response['owner_id']}_{save_response['id']}"
            attachments.append(photo_id)
            
            # Перемещаем обработанное изображение
            shutil.move(img_path, os.path.join(MOVE_TO, os.path.basename(img_path)))
            print(f"Изображение {os.path.basename(img_path)} успешно загружено")
            
        except Exception as e:
            print(f"Ошибка при обработке {img_path}: {str(e)}")
    
    return attachments

def schedule_posts(post_count):
    """Планирует указанное количество постов"""
    all_images = os.listdir(DOWNLOAD_FROM)
    if not all_images:
        print("Нет изображений для загрузки.")
        return

    # Читаем текущее время поста
    with open('on.json', 'r') as f:
        schedule_data = json.load(f)
    
    current_time = datetime.strptime(schedule_data['date_stamp'], '%Y-%m-%d %H:%M:%S')
    
    num_images = int(input("Сколько картинок в посте? 0 - для того чтобы поделить оставшиеся картинки поровну по постам "))
    if num_images == 0: num_images = len(all_images)//post_count
    while post_count > 0 and all_images:
        # Определяем количество фото для этого поста
        selected_images = random.sample(all_images, num_images)
        image_paths = [os.path.join(DOWNLOAD_FROM, img) for img in selected_images]
        
        # Загружаем фото
        attachments = upload_photos(GROUP_ID, image_paths)
        if not attachments:
            print("Не удалось загрузить ни одного изображения")
            break
            
        # Обновляем время поста
        current_time += timedelta(hours=TIME_DELAY)
        schedule_data['date_stamp'] = current_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # Сохраняем новое время
        with open('on.json', 'w') as f:
            json.dump(schedule_data, f)
        
        # Публикуем пост
        try:
            vk.wall.post(
                owner_id=f"-{GROUP_ID}",
                from_group=1,
                attachments=",".join(attachments),
                publish_date=int(current_time.timestamp())
            )
            
            print(f"Пост с {len(attachments)} фото запланирован на {current_time}")
            post_count -= 1
            
            # Удаляем обработанные изображения из списка
            for img in selected_images:
                all_images.remove(img)
                
        except Exception as e:
            print(f"Ошибка при публикации: {str(e)}")
            break

if __name__ == "__main__":
    post_count = int(input("Сколько постов нужно? "))
    schedule_posts(post_count)