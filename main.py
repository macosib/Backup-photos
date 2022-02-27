import time
import os
import json
import requests
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload
from urllib3.packages.six import BytesIO

class VkPhotos:
    url = 'https://api.vk.com/method/'

    def __init__(self, token, version, userid_vk):
        self.user_id_vk = userid_vk
        self.params = {
            'access_token': token,
            'v': version,
            'owner_id': self.user_id_vk

        }
        self.params_for_get_foto = {
            'user_id': self.user_id_vk,
            'extended': '1',
            'count': '5'
        }

    def get_all_id_albums(self):
        get_foto_list_url = self.url + 'photos.getAlbums'
        response = requests.get(get_foto_list_url, params=self.params)
        response.raise_for_status()
        if response.status_code == 200:
            print(f'Список альбомов пользователя id{self.user_id_vk} получен')

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

    def __max_size_foto_filter_profile(self, photos):
        result = {}
        logs_file = []
        for foto in photos.json()['response']['items']:
            max_size_photo = foto['sizes'][-1]
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

    def get_photos_from_profile(self, album_id='profile'):
        link = self.url + 'photos.get'
        params = {'album_id': album_id}
        response = requests.get(link, params={**self.params, **self.params_for_get_foto, **params})
        response.raise_for_status()
        if response.status_code == 200:
            print(f'Список фотографий со профиля id{self.user_id_vk} получен')
        return self.__max_size_foto_filter_profile(response)


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


class GoogleDrive:

    folder_id = '1qPD-H-fxqvHnMuL70AFvQb93BCAN0lV-'
    def main_google(self):
        try:
            SCOPES = ['https://www.googleapis.com/auth/drive']
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            service = build('drive', 'v3', credentials=creds)
            return service, creds

        except HttpError as error:
            print(f'An error occurred: {error}')

    def __init__(self):
        data = self.main_google()
        self.service = data[0]
        self.creds = data[1]

    def get_file_list(self):
        results = self.service.files().list(pageSize=10,
                                            fields="nextPageToken, files(id, name, mimeType, parents)").execute()
        items = results.get('files', [])
        if not items:
            print('No files found.')
            return
        print('Files:')
        for item in items:
            print(u'{0} ({1})'.format(item['name'], item['id']))

    def get_check_file(self):
        results = self.service.files().list(
            pageSize=10, fields="files(name)").execute()
        return results['files']

    def upload_to_goole_drive(self, name, url):
        response = requests.get(url)
        file_content = BytesIO(response.content)
        file_metadata = {'name':
                             f'{name}.jpg',
                         'parents': [self.folder_id]}
        media = MediaIoBaseUpload(file_content, mimetype='image/jpeg')
        self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        file_list = self.get_check_file()
        for item in file_list:
            if item['name'] == f'{name}.jpg':
                print(f'Фотография {name}.jpg успешно загружена')
                break

class VkUser:
    url = 'https://api.vk.com/method/'

    def __init__(self, token, version):
        self.params = {
            'access_token': token,
            'v': version
        }

    def check_user_id_or_username(self, id_profile):
        get_foto_list_url = self.url + 'users.get'
        id_profile = {'user_ids': id_profile}
        response = requests.get(get_foto_list_url, params={**self.params, **id_profile})
        response.raise_for_status()
        if response.status_code == 200:
            print(f'Запрос на проверку пользователя отправлен.')
        if response.json()['response'] and 'deactivated' not in response.json()['response'][0]:
            return response.json()['response'][0]['id']

def main():

    with open(os.path.join(os.getcwd(), 'token_vk.txt'), 'r', encoding='UTF-8') as file_object:
        token_vk = file_object.read().strip()

    with open(os.path.join(os.getcwd(), 'yandex_token.txt'), 'r', encoding='UTF-8') as file_object:
        token_yandex = file_object.read().strip()

    output_file = []
    user_vk_check = VkUser(token_vk, '5.131')

    while True:
        user_id_or_name = input('Введите имя пользователя или ID: ')
        result = user_vk_check.check_user_id_or_username(user_id_or_name)
        if result:
            print('Проверка прошла успешно, такой пользователь есть в VK!')
            user_id_vk = result
            break
        else:
            print('Такого пользователя нет или он был удален, повторите ввод!')
            continue

    downloader = VkPhotos(token_vk, '5.131', user_id_vk)
    uploader = YandexDisk(token_yandex)
    uploader_google = GoogleDrive()

    ''' Создание папки для загрузки на Яндекс Диске'''
    def __create_folder_yandex_disc():
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
                return path_to_upload_name

    ''' Загрузка фотографий профиля пользователя на Google Drive'''
    def upload_profile_photo_from_vk_to_google_drive():
        photos = downloader.get_photos_from_profile()
        for photo in photos[0].items():
            name = photo[0].split('.')[0]
            url = photo[1]['url']
            uploader_google.upload_to_goole_drive(name, url)
            output_file.extend(photos[1])

    '''Загрузка фото со всех альбомов пользователя на Google Drive'''
    def upload_all_foto_to_google_drive():
        all_id_album = downloader.get_all_id_albums()
        for id_album in all_id_album:
            photos = downloader.get_photos_from_any_album(id_album)
            for photo in photos[0].items():
                time.sleep(0.33)
                name = photo[0].split('.')[0]
                url = photo[1]['url']
                uploader_google.upload_to_goole_drive(name, url)
                output_file.extend(photos[1])

    '''Загрузка фото со всех альбомов пользователя на Yandex Disk'''
    def upload_all_foto_to_yandex_disk():
        all_id_album = downloader.get_all_id_albums()
        path_to_upload_name = __create_folder_yandex_disc()
        for id_album in all_id_album:
            photos = downloader.get_photos_from_any_album(id_album)
            time.sleep(0.33)
            for photo in photos[0].items():
                name = photo[0].split('.')[0]
                url = photo[1]['url']
                uploader.upload_file_to_disk_from_link(f"{path_to_upload_name}/", name, url)
                output_file.extend(photos[1])

    '''Загрузка фото профиля на Yandex Disk'''
    def upload_profile_foto_to_yandex_disk():
        photos = downloader.get_photos_from_profile()
        path_to_upload_name = __create_folder_yandex_disc()
        for photo in photos[0].items():
            name = photo[0].split('.')[0]
            url = photo[1]['url']
            uploader.upload_file_to_disk_from_link(f"{path_to_upload_name}/", name, url)
            output_file.extend(photos[1])

    commands = {'1': upload_profile_foto_to_yandex_disk,
                '2': upload_all_foto_to_yandex_disk,
                '3': upload_profile_photo_from_vk_to_google_drive,
                '4': upload_all_foto_to_google_drive
                }
    while True:
        print('Доступны следующие команды:')
        print('''
Доступны следующие команды:
Загрузить фотографии профиля на яндекс диск - введите "1"
 Загрузить все фотографии на яндекс диск - введите "2"
Загрузить фотографии профиля на Google Drive - введите "3"
 Загрузить все фотографии на Google Drive - введите "4"
Выйти из программы - введите "5"
        ''')
        command = input()
        if command in commands:
            commands[command]()
            break
        elif command == '5':
            break
        else:
            print('Повторите ввод')
            continue

    with open('output_file.json', 'w', encoding='utf-8') as file_object:
        file_object.write(json.dumps(output_file))


if __name__ == '__main__':
    main()
