import argparse
import Utils
from urllib.parse import urlparse, parse_qs
import WatchRuDAO
import time
import datetime
import config
import logging
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))


class WatchRuForumScrapper:
    def __init__(self, login, password, debug=False, indocker=False):
        self.closed = False
        if not indocker:
            options = webdriver.ChromeOptions()
            if not debug:
                options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            self.driver = webdriver.Chrome(chrome_options=options)
        else:
            started = False
            while not started:
                try:
                    self.driver = webdriver.Remote("http://chromebrowser:4444/wd/hub", DesiredCapabilities.CHROME)
                    started = True
                except Exception as e:
                    logging.exception(e)
                    time.sleep(10)
        self.driver.get('http://forum.watch.ru')
        self._login(login, password)

    def _login(self, login, password):
        try:
            login_field = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "navbar_username")))
            password_field = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "navbar_password")))
            login_field.send_keys(login)
            password_field.send_keys(password)
            button = self.driver.find_element_by_xpath("/html/body/div[2]/div/div/table[3]/tbody/tr/td[2]/form/table/tbody/tr[2]/td[3]/input")
            button.click()
            success_username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/div/div/table[3]/tbody/tr/td[2]/div/strong/a")))
        except Exception as e:
            logging.exception(e)

    def get_list_themes(self, section_id):
        if section_id is None:
            return None
        try:
            ret = []
            self.driver.get('http://forum.watch.ru/forumdisplay.php?f={}'.format(section_id))
            threadlist = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, "threadbits_forum_{}".format(section_id))))
            for thread in threadlist.find_elements_by_tag_name('tr')[:]:
                try:
                    current_title = thread.find_elements_by_tag_name('td')[2].get_attribute('title')
                    theme_url = thread.find_elements_by_tag_name('td')[2].find_elements_by_tag_name('div')[0].find_elements_by_tag_name('a')[1].get_attribute('href')
                    theme_name = thread.find_elements_by_tag_name('td')[2].find_elements_by_tag_name('div')[0].find_elements_by_tag_name('a')[1].text
                    theme_name += thread.find_elements_by_tag_name('td')[2].get_attribute('title')
                    update_date = datetime.datetime.strptime(thread.find_elements_by_tag_name('td')[3].text.split('\n')[0], "%d.%m.%Y %H:%M")
                    ret.append({'name': theme_name, 'title': current_title,
                                'url': theme_url, 'update_time': update_date,
                                'id': parse_qs(urlparse(theme_url).query)['t'][0]})
                except:
                    continue
            return ret
        except Exception as e:
            logging.exception(e)

    def get_screenshot(self, theme_url):
        try:
            self.driver.get(theme_url)
            _ = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//*[contains(@id,\"post_message\")]")))
            theme_id = parse_qs(urlparse(theme_url).query)['t'][0]
            directory_path = os.path.join(config.DATA_DIRECTORY, theme_id)
            if not os.path.exists(directory_path):
                os.makedirs(directory_path)
            pdf_path = os.path.join(directory_path, '{}_{}.pdf'.format(theme_id, time.time()))
            screen_path = os.path.join(directory_path, '{}_{}.png'.format(theme_id, time.time()))
            # self.driver.save_screenshot(screen_path)
            current_temp_file = os.path.join(config.DATA_DIRECTORY, "{}.png".format(time.time()))
            Utils.fullpage_screenshot(self.driver, current_temp_file)
            os.rename(current_temp_file, screen_path)
            # Utils.save_as_pdf(self.driver, pdf_path, {'landscape': False})
            return {'pdf': pdf_path, 'jpeg': screen_path}
        except Exception:
            return {'pdf': '', 'jpeg': ''}

    def close(self):
        self.closed = True
        if self.driver:
            self.driver.close()

    def __del__(self):
        if not self.closed:
            self.close()


def scrape(scrapper):
    session = config.Session()
    logging.info('starting scrapper')
    for section_id, section_name in config.sections.items():
        for theme in scrapper.get_list_themes(section_id=section_id):
            stored_themes = session.query(WatchRuDAO.WatchRuTheme)\
                .filter(WatchRuDAO.WatchRuTheme.theme_id==theme['id'] and
                        WatchRuDAO.WatchRuTheme.section_id==section_id).all()
            if len(stored_themes) == 0:
                logging.info('new theme, not stored in db -> adding')
                ret_screens = scrapper.get_screenshot(theme['url'])
                parsed_theme = WatchRuDAO.WatchRuTheme(theme_id=theme['id'],
                                                       theme_name=theme['name'],
                                                       section_id=section_id,
                                                       section=section_name,
                                                       pdf_path=ret_screens['pdf'],
                                                       screenshot_path=ret_screens['jpeg'],
                                                       last_update=theme['update_time'],
                                                       sended=False,
                                                       was_updated=False
                                                       )
                session.add(parsed_theme)
            elif len(stored_themes) == 1:
                stored_theme = stored_themes[0]
                logging.info('old theme, i need check time update')
                if theme['update_time'] <= stored_theme.last_update:
                    continue
                ret_screens = scrapper.get_screenshot(theme['url'])
                stored_theme.last_update = theme['update_time']
                stored_theme.was_updated = True
                stored_theme.sended = False
                stored_theme.pdf_path = ret_screens['pdf']
                stored_theme.screenshot_path = ret_screens['jpeg']
            else:
                logging.warning('wtf too many themes with same id and section')
                continue
            try:
                session.commit()
            except:
                session.rollback()
    scrapper.close()
    session.close()
    logging.info('finished')


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-d', '--docker', type=bool, default=False, help="docker start flag")
    parser.add_argument('-v', '--debug', type=bool, default=False, help="debug flag")
    args = parser.parse_args()
    while True:
        scrapper = WatchRuForumScrapper(login=config.LOGIN, password=config.PASSWORD, debug=args.debug, indocker=args.docker)
        scrape(scrapper=scrapper)
        scrapper.close()
        time.sleep(config.TIME_QUANT)


if __name__ == "__main__":
    main()
