import os
import paramiko
import shutil
from dotenv import load_dotenv

load_dotenv()

ABSOLUTE_PATH: str = os.path.dirname(os.path.abspath("__file__"))
REMOTE_PATH: str = os.getenv('REMOTE_PATH')


def create_paths() -> tuple:
    """
    Функция для создания абсолютных путей для файлов,
    для отправки с локального компьютера на удаленный сервер.
    Возвращает кортеж списков типа "source_paths" и "target_paths".
    Где "source_paths" - сгенерированные пути для исходных файлов,
    "target_paths" - пути для файлов назначения.
    """
    source_folder = os.path.join(ABSOLUTE_PATH, 'reports')
    target_folder = os.path.join(REMOTE_PATH, 'reports/')
    source_paths = [
        os.path.join(source_folder, file) for file in os.listdir(source_folder)
    ]
    target_paths = [target_folder + file for file in os.listdir(source_folder)]
    return source_paths, target_paths


def folder_to_zip() -> str:
    """
    Функция для ахивации файлов в папке "reports".
    Возвращает имя созданного архива.
    """
    source_folder = os.path.join(ABSOLUTE_PATH, 'reports')
    target_folder = os.path.join(ABSOLUTE_PATH, 'archive')
    return shutil.make_archive(
        os.path.join(target_folder, 'spo2'), 'zip', source_folder
    )


def transfer_zip(hostname: str, username: str) -> None:
    """
    Функция для переноса файлов с локального компьютера
    на удаленный сервер. Принимает на вход:
    hostname: str (ip удаленного сервера)
    username: str (имя пользователя на удаленном сервере)
    """
    source_zip = os.path.join(ABSOLUTE_PATH, 'archive', 'spo2.zip')
    target_zip = os.path.join(REMOTE_PATH, 'archive/', 'spo2.zip')
    org_source = os.path.join(ABSOLUTE_PATH, 'organisations.json')
    org_target = os.path.join(REMOTE_PATH, 'organisations.json')
    with paramiko.SSHClient() as ssh:
        ssh.load_host_keys(
            os.path.expanduser(os.path.join("~", ".ssh", "known_hosts"))
        )
        ssh.connect(hostname=hostname, username=username)
        sftp = ssh.open_sftp()
        sftp.put(source_zip, target_zip)
        print(f"copying {source_zip} -> {target_zip}")
        sftp.put(org_source, org_target)
        print(f"copying {org_source} -> {org_target}")
    print('done copying')
