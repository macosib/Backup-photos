import time
import requests
import os
import json

with open(os.path.join(os.getcwd(), 'token_vk.txt'), 'r', encoding='UTF-8') as file_object:
    token_vk = file_object.read().strip()

with open(os.path.join(os.getcwd(), 'yandex_token.txt'), 'r', encoding='UTF-8') as file_object:
    token_yandex = file_object.read().strip()

with open(os.path.join(os.getcwd(), 'id_user_vk.txt'), 'r', encoding='UTF-8') as file_object:
    user_id_vk = file_object.read().strip()


class VkPhotos:
    url = 'https://api.vk.com/method/'

    def __init__(self, token, version, userid_vk):
        self.user_id_vk = userid_vk
        self.params = {
            'access_token': token,
            'v': version,
            'owner_id': user_id_vk

        }
        self.params_for_get_foto = {
            'user_id': user_id_vk,
            'extended': '1',
            'count': '5'
        }

    def get_all_id_albums(self):
        get_foto_list_url = self.url + 'photos.getAlbums'
        response = requests.get(get_foto_list_url, params=self.params)
        response.raise_for_status()
        if response.status_code == 200:
            print(f'Список альбомов пользователя id{user_id_vk} получен')

        result_all_id = []
        if response.json()['response']['items']:
            for album in response.json()['response']['items']:
                result_all_id.append(str(album['id']))
        return result_all_id

    def __max_size_foto_filter(self, photos):
        result = {}
        logs_file = []
        for foto in photos.json()['response']['items']:
            max_size_photo = sorted(foto['sizes'], key=lambda x: (x['height'], x['width']), reverse=True)[0]
            if f"{foto['likes']['count']}.jpg" in result:
                result.update({f"{foto['likes']['count']} {foto['date']}.jpg": max_size_photo})
                logs_file.extend([{'file_name': f"{foto['likes']['count']} {foto['date']}.jpg",
                                   'size': f"{max_size_photo['height']}x{max_size_photo['width']}"}])
            else:
                result.update({f"{foto['likes']['count']}.jpg": max_size_photo})
                logs_file.extend([{'file_name': f"{foto['likes']['count']}.jpg",
                                   'size': f"{max_size_photo['height']}x{max_size_photo['width']}"}])
        return result, logs_file

    def get_photos_from_any_album(self, album_id):
        link = self.url + 'photos.get'
        params = {'album_id': album_id}
        response = requests.get(link, params={**self.params, **self.params_for_get_foto, **params})
        response.raise_for_status()
        if response.status_code == 200:
            print(f'Список фотографий с альбома id{album_id} получен')
        return self.__max_size_foto_filter(response)

    def get_photos_from_wall(self, album_id='profile'):
        link = self.url + 'photos.get'
        params = {'album_id': album_id}
        response = requests.get(link, params={**self.params, **self.params_for_get_foto, **params})
        response.raise_for_status()
        if response.status_code == 200:
            print(f'Список фотографий со профиля id{user_id_vk} получен')
        return self.__max_size_foto_filter(response)


class YandexDisk:

    def __init__(self, token):
        self.token = token

    def get_headers(self):
        return {
            'Content-Type': 'application/json',
            'Authorization': f'OAuth {self.token}'
        }

    def get_files_list(self, name_folder):
        files_url = 'https://cloud-api.yandex.net/v1/disk/resources/'
        params = {"path": name_folder}
        headers = self.get_headers()
        response = requests.get(files_url, headers=headers, params=params)
        return response.json()

    def create_folder(self, name_folder):
        url = 'https://cloud-api.yandex.net/v1/disk/resources'
        headers = self.get_headers()
        params = {"path": name_folder}
        response = requests.put(url, headers=headers, params=params)
        response.raise_for_status()
        if response.status_code == 201:
            print(f'Папка {name_folder} успешно создана')

    def upload_file_to_disk_from_link(self, name_folder, file_name, url_upload_vk):
        upload_url = "https://cloud-api.yandex.net/v1/disk/resources/upload"
        headers = self.get_headers()
        params = {"path": f"{name_folder}{file_name}", "url": url_upload_vk}
        response = requests.post(upload_url, headers=headers, params=params)
        response.raise_for_status()
        if response.status_code == 202:
            print(f"Фото {file_name} успешно загружено")


if __name__ == '__main__':
    downloader = VkPhotos(token_vk, '5.131', user_id_vk)
    uploader = YandexDisk(token_yandex)
    output_file = []


    def check_name(name):
        if 'error' in uploader.get_files_list(name):
            return uploader.create_folder(name)
        else:
            print('Папка с таким названием уже существует! Необходимо ввести другое имя')
            return 'False'


    while True:
        path_to_upload_name = input('Введите имя папки, для загрузки фотографий: ')
        if check_name(path_to_upload_name) == 'False':
            continue
        else:
            break

    # Загрузка фото со всех папок
    for id_album in downloader.get_all_id_albums():
        time.sleep(0.33)
        for photo in downloader.get_photos_from_any_album(id_album)[0].items():
            uploader.upload_file_to_disk_from_link(f"{path_to_upload_name}/", photo[0], photo[1]['url'])
        output_file.extend(downloader.get_photos_from_any_album(id_album)[1])

    # Загрузка фото с профиля
    for photo in downloader.get_photos_from_wall()[0].items():
        uploader.upload_file_to_disk_from_link(f"{path_to_upload_name}/", photo[0], photo[1]['url'])
        output_file.extend(downloader.get_photos_from_wall()[1])

    with open('output_file.json', 'w', encoding='utf-8') as file_object:
        file_object.write(json.dumps(output_file))
