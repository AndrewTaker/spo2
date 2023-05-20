import os
import json
import requests
from time import sleep
from datetime import datetime
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium import webdriver
import pandas as pd
from dotenv import load_dotenv
from ssh_transfer import transfer_zip, folder_to_zip

load_dotenv()

START: datetime = datetime.strptime('08:50', "%H:%M").time()
END: datetime = datetime.strptime('18:10', "%H:%M").time()
SLEEP_TIME: int = 3600

ROOT_DIRECTORY: os.path = os.path.dirname(os.path.abspath("__file__"))
GECKODRIVER_DIRECTORY: os.path = os.path.join(
    'webdriver', '.wdm', 'drivers', 'geckodriver'
)

GECKODRIVER: str = 'geckodriver'
HEADLESS: bool = True

GIVC_LOGIN: str = os.getenv("GIVC_LOGIN")
GIVC_PASSWORD: str = os.getenv("GIVC_PASSWORD")
CHAPTERS: dict = {
    "1": "info", "2": "1.1", "3": "1.2", "4": "1.3",
    "5": "1.4", "6": "1.5", "7": "2.1", "8": "2.2",
    "9": "2.3", "10": "2.4", "11": "2.5", "12": "2.6",
    "13": "2.7", "14": "3.1", "15": "3.2", "16": "3.3",
    "17": "3.4", "18": "3.5", "19": "3.6", "20": "3.7",
    "21": "sign"
}
BASE_URL: str = 'https://client.miccedu.ru'

CHAT_ID: str = json.loads(os.getenv("ALLOWED_USERS"))[1]
BOT_TOKEN: str = os.getenv("BOT_TOKEN")


def send_message(message: str) -> None:
    """
    Функция для отправки сообщения о завершении парсинга админу.
    Принимает на вход сообщение для отправки.
    Использует веб-хук telegram ip.
    Необязательная функция.
    """
    token = BOT_TOKEN
    chat_id = CHAT_ID
    requests.post(
        url='https://api.telegram.org/bot{0}/sendMessage'.format(token),
        data={'chat_id': chat_id, 'text': message}
    ).json()


def init_driver() -> webdriver.Firefox:
    """
    Функция для инициализации драйвера.
    Возвращает инстанс класса webdriver.Firefox.
    Ветвление по двум условиям:
        -веб-драйвер уже установлен;
        -веб-драйвер последней версии.
    Если условия не соблюдены, драйвер будет скачан или обновлён.
    """
    options = webdriver.FirefoxOptions()
    if HEADLESS:
        options.add_argument("-headless")
    if os.path.exists(GECKODRIVER_DIRECTORY):
        driver = webdriver.Firefox(
            service=FirefoxService(GECKODRIVER),
            options=options
        )
        print('already installed')
    else:
        driver = webdriver.Firefox(
            service=FirefoxService(
                GeckoDriverManager(path=r'webdriver').install()
            ),
            options=options
        )
    return driver


def login_givc(
        driver: webdriver.Firefox, login: str, password: str
) -> None:
    """
    Функция для авторизации на сайте "https://client.miccedu.ru".
    На вход принимает:
        driver: webdriver.Firefox (инстанс класса webdriver);
        login: str (логин пользователя сайта);
        password: str (пароль пользователя сайта).
    """
    try:
        driver.get(BASE_URL)
        driver.find_element(By.LINK_TEXT, 'ЕСИА ГИВЦ').click()
        driver.find_element(By.ID, 'username').send_keys(login)
        driver.find_element(
            By.ID, 'password'
        ).send_keys(password)
        driver.find_element(By.NAME, 'login').click()
        print(f"logged in as {login}")
    except Exception as error:
        print(f"{login_givc.__name__} raised as excpetion {error}")


def determine_grant_element(driver: webdriver.Firefox):
    """
    Функция определяет ссылку на отчёт ФСН № СПО-2.
    На вход принимает:
        driver: webdriver.Firefox (инстанс класса webdriver).
    Возвращает ссылку на личный кабинет ФСН № СПО-2.
    """
    grants = driver.find_elements(
        By.XPATH, '//a[@class="block-grant-row-link"]'
    )
    for grant in grants:
        if 'СПО-2' in grant.text:
            return grant.get_attribute('href')


def get_organisations(driver: webdriver.Firefox) -> dict:
    """
    Функция для получения списка организаций, которые предоставили доступ
    нашему аккаунту к себе в личный кабинет.
    На вход принимает:
        driver: webdriver.Firefox (инстанс класса webdriver).
    Возвращает словарь словарей организаций типа:
        'id': {
            'id': int,
            'name': str,
            'selected': bool,
            'uuid': str,
            'is_avaliable': bool,
            'add_entitlement': bool
        }
    """
    driver.get('https://client.miccedu.ru/')
    organisation = determine_grant_element(driver)
    split = organisation.split('/')
    del split[-2:]
    url = 'view-source:' + '/'.join(split) + '/getOrgList'
    driver.get(url)
    extracted_json = driver.find_element(By.TAG_NAME, 'pre').text
    _json = json.loads(extracted_json)
    with open('organisations.json', 'w', encoding='utf-8') as f:
        json.dump(_json, f, ensure_ascii=False)
    return _json['orgList']


class Organisation:
    """
    Интерфейс для работы с организациями.
    """
    def __init__(
            self,
            id: str,
            name: str,
            selected: bool,
            uuid: str,
            is_available: bool,
            add_entitlement: bool,
            signed: bool = False,
            driver: webdriver.Firefox = None,
    ):
        self.id = id
        self.name = name
        self.seleceted = selected
        self.uuid = uuid
        self.is_available = is_available
        self.add_entitlement = add_entitlement
        self.signed = signed
        self.driver = driver
        self.wait = WebDriverWait(self.driver, 10)

    def __get_sign_page_number(self) -> str:
        """Возвращает номер страницы с подписью."""
        return ''.join([k for k, v in CHAPTERS.items() if v == 'sign'])

    def __build_org_url(self) -> str:
        """Создаёт ссылку на отчёт и возвращает её."""
        url = '{base_url}/workspace/{uuid}/article'
        return url.format(base_url=BASE_URL, uuid=self.uuid)

    def get_sign_status(self) -> bool:
        """Проверяет, подписан ли отчёт."""
        sign_page = self.__get_sign_page_number
        url = f"{self.__build_org_url}/{sign_page}"
        sign_xpath = '//h6["@class=pb-0 svelte-4yeyci"]'
        self.driver.get(url)
        sign_status = self.wait.until(
            EC.visibility_of_element_located((By.XPATH, sign_xpath))
        ).text
        if sign_status:
            self.signed = True
            return True
        return False

    def __optimize_dataframe(
            self, df: pd.DataFrame, chapter: str
    ) -> pd.DataFrame:
        """
        Функция для нормализации датафрейма. Возвращает очищенный датафрейм
        """
        df = df[df['B'] != '№ строки']
        df = df.drop('Unnamed: 0', errors='ignore', axis='columns')
        df = df.apply(pd.to_numeric, errors='ignore')
        df.insert(0, 'organisation', self.name)
        df.insert(0, 'chapter', chapter)
        df = df.set_index(["chapter", "organisation"]).reset_index()
        return df

    def save_result_as_xlsx(self, dataframes: "list[pd.DataFrame]") -> None:
        """
        Сохраняет список датафреймов в отдельные xlsx файлы
        с минимальным форматированием (цвета, фильтры).
        """
        with pd.ExcelWriter(
            f'reports/{self.uuid}.xlsx',
            engine='xlsxwriter',
            engine_kwargs={
                "options": {"strings_to_numbers": True}
            }
        ) as writer:
            workbook = writer.book
            worksheet = workbook.add_worksheet('result')
            writer.sheets['result'] = worksheet
            data_format1 = workbook.add_format({'bg_color': '#a4d5e0'})
            column = 0
            row = 1
            for i in range(15):
                worksheet.write(0, i, 'x')
            for df in dataframes:
                try:
                    df.to_excel(
                        writer,
                        sheet_name='result',
                        startrow=row,
                        startcol=column,
                        header=False,
                        index=False
                    )
                    worksheet.set_row(row, cell_format=data_format1)
                    worksheet.set_column('D:D', cell_format=data_format1)
                    worksheet.autofilter(0, 0, df.shape[0], 15)
                    worksheet.freeze_panes(1, 0)
                except Exception as error:
                    print(error)
                finally:
                    row += df.shape[0]
            print(
                f"saved {self.name} as {self.uuid} in reports folder"
            )
        print('done, sleeping')

    def get_data(self):
        """
        Главная функция-парсер.
        Находит таблицу на странице, преобразует в датафрейм.
        """
        dataframes = list()
        table_xpath = '//table[@class="table-givc svelte-3b8tob"]'
        chapters = {
            k: v for k, v in CHAPTERS.items() if (v != 'info' and v != 'sign')
        }
        for page, chapter in chapters.items():
            url = f"{self.__build_org_url()}/{page}"
            self.driver.get(url)
            print(f'working on: {self.name}')
            print(url)
            print('=' * 100)
            self.wait.until(
                EC.visibility_of_element_located((By.XPATH, table_xpath))
            )
            table = self.driver.page_source
            try:
                df = pd.read_html(table)[0]
            except Exception as error:
                print(
                    f"error at: {self.get_data.__name__} {error}"
                )
            df = self.__optimize_dataframe(df, chapter)
            dataframes.append(df)
        print(f"done with {self.name}")
        return dataframes


def main():
    directories = ['archive', 'reports']
    for directory in directories:
        if directory in os.listdir():
            continue
        else:
            os.mkdir(directory)
            print(f'Создана папка "{directory}"')

    while True:
        current_time = datetime.now().time()
        if current_time > START and current_time < END:
            try:
                driver = init_driver()
                login_givc(driver, GIVC_LOGIN, GIVC_PASSWORD)
                organisations_dict = get_organisations(driver)
                organisations_list = list()
                for i in organisations_dict:
                    org = Organisation(**organisations_dict[i], driver=driver)
                    organisations_list.append(org)

                for org in organisations_list:
                    dataframes = list()
                    dataframes += org.get_data()
                    org.save_result_as_xlsx(dataframes)
            except Exception as error:
                print('something went wrong: {}'.format(error))
                send_message(f"error accured: {error}")
                continue
            finally:
                driver.quit()
                folder_to_zip()
                transfer_zip(
                    hostname=os.getenv('REMOTE_HOSTNAME'),
                    username=os.getenv('REMOTE_USERNAME'),
                )
                send_message(f'completed task at {current_time}, sleeping')
                sleep(SLEEP_TIME)


if __name__ == '__main__':
    main()
