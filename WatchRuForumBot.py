import re
from WatchRuDAO import *
import traceback
import asyncio
import config
import logging
import telepot
import telepot.aio
from telepot.aio.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import and_
from sqlalchemy import desc
TOKEN = config.BOT_API_TOKEN


def main():
    message_with_inline_keyboard = None

    async def send_themes():
        while True:
            logging.info('sending themes to admins')
            session = config.Session()
            try:
                themes_to_send = session.query(WatchRuTheme).filter(WatchRuTheme.sended == False).all()
                for theme_to_send in themes_to_send:
                    # print(theme_to_send)
                    if theme_to_send.was_updated:
                        message = '''В секции форума **{}** обновилась тема:\n **{}**\n __Обновлена__: {}\nurl: http://forum.watch.ru/showthread.php?t={}'''\
                            .format(theme_to_send.section.replace('"', ''),
                                    theme_to_send.theme_name.replace('http://forum.watch.ru/images/market-question.png', ''),
                                    theme_to_send.last_update,
                                    theme_to_send.theme_id)
                    else:
                        message = '''В секции форума **{}** добавлена тема:\n **{}**\n __Добавлена__: {}\nurl: http://forum.watch.ru/showthread.php?t={}''' \
                            .format(theme_to_send.section.replace('"', ''),
                                    theme_to_send.theme_name.replace('http://forum.watch.ru/images/market-question.png', ''),
                                    theme_to_send.last_update,
                                    theme_to_send.theme_id)
                    for chat_id in [x.chat_id for x in session.query(Chat).filter(Chat.admin == True).all()]:
                        regexes = session.query(Regexes).filter(Regexes.chat_id==chat_id).all()
                        if any([re.search(y.regex, theme_to_send.theme_name) for y in regexes]):
                            await bot.sendMessage(chat_id=chat_id, text=message, parse_mode='html')
                            try:
                                with open(theme_to_send.screenshot_path, 'rb') as cf:
                                    await bot.sendDocument(chat_id=chat_id, document=cf, caption=theme_to_send.theme_name[:50])
                                    #await bot.sendPhoto(chat_id=chat_id, photo=cf, caption=theme_to_send.theme_name[:50])
                            except Exception as e:
                                logging.exception(e)
                    theme_to_send.sended = True
                    theme_to_send.was_updated = False
                    session.add(theme_to_send)
                    try:
                        session.commit()
                    except Exception as e:
                        logging.exception(e)
                        session.rollback()
            except Exception as e:
                logging.exception(e)
                for chat_id in [x.chat_id for x in session.query(Chat).filter(Chat.admin == True).all()]:
                    await bot.sendMessage(chat_id=chat_id,
                                          text='Exception {} with {}'.format(str(e), traceback.format_exc()))
            finally:
                session.close()
            await asyncio.sleep(config.TIME_SLEEP_SENDER)

    async def _send_help(chat_id):
        await bot.sendMessage(chat_id, u'Бот мониторит форум forum.watch.ru и уведомляет по секциям пользователей об изменениях. Управление регулярными выражениями:\n /regex - список, /regex_add - добавить, /regex_remove - удалить')

    async def on_chat_message(msg):
        session = config.Session()
        try:
            content_type, chat_type, chat_id = telepot.glance(msg)

            if content_type != 'text':
                return

            command = msg['text'][:].lower()
            if 'text' in msg and msg['text'] == '/start':
                new_chat_info = session.query(Chat).filter(Chat.chat_id == chat_id).first()
                if new_chat_info is None:
                    new_chat_info = Chat(chat_id=chat_id, admin=False, tg_ans=str(msg))
                    await bot.sendMessage(chat_id, u'Шо?! Новый пользователь?!')
                else:
                    await bot.sendMessage(chat_id, u'А я тебя уже знаю')
                session.add(new_chat_info)
                try:
                    session.commit()
                except Exception as e:
                    logging.exception(e)
                    session.rollback()
            elif command.startswith('/client'):
                passw = re.search('\/admin\s+(?P<passw>\w+)', msg['text'])
            elif command.startswith('/admin'):
                passw = re.search('\/admin\s+(?P<passw>\w+)', msg['text'])
                if passw and passw.group('passw') == config.BOT_ADMIN_PASSWORD:
                    current_chat_info = session.query(Chat).filter(Chat.chat_id == chat_id).first()
                    current_chat_info.admin = True
                    session.add(current_chat_info)
                    try:
                        session.commit()
                    except Exception as e:
                        session.rollback()
                    await bot.sendMessage(chat_id, u'Слушаю и повинуюсь, хозяин')
                    await _send_help(chat_id)
                else:
                    await bot.sendMessage(chat_id, u'ЭЭЭ ТЫ КТО ТАКОЙ? ДАВАЙ ДО СВИДАНИЯ!')
            elif command == '/help':
                await _send_help(chat_id)
            elif command.startswith('/regex'):
                chats = session.query(Chat).filter(Chat.chat_id==chat_id).all()
                if not(chats and len(chats) > 0):
                    return
                if command.startswith('/regex_add'):
                    regex_text = re.search('\/regex_add\s+(?P<regex_text>.*)', msg['text'])
                    if regex_text and regex_text.group('regex_text'):
                        regex_obj = Regexes(chat_id=chat_id, regex=regex_text.group('regex_text').rstrip().lstrip())
                        session.add(regex_obj)
                        try:
                            session.commit()
                        except Exception as e:
                            session.rollback()
                        await bot.sendMessage(chat_id, u'Added regex {}'.format(regex_text))
                    else:
                        await bot.sendMessage(chat_id, u'Not found regex')
                elif command.startswith('/regex_remove'):
                    uid_remove = re.search('\/regex_remove_(?P<uid>\w+)', msg['text'])
                    if uid_remove and uid_remove.group('uid'):
                        regex_obj = session.query(Regexes).filter(Regexes.id==uid_remove.group('uid')).first()
                        session.delete(regex_obj)
                        try:
                            session.commit()
                            await bot.sendMessage(chat_id, u'Removed regex <b>{}</b>'.format(regex_obj.regex), parse_mode='html')
                        except Exception as e:
                            session.rollback()
                            await bot.sendMessage(chat_id, u'Error on removing regex <b>{}</b> with exception {}'.format(regex_obj.regex, str(e)),
                                                  parse_mode='html')
                    else:
                        await bot.sendMessage(chat_id, u'Error on removing regex not found uid')
                else:
                    regexes = session.query(Regexes).filter(Regexes.chat_id==chat_id).all()
                    for regex in regexes:
                        await bot.sendMessage(chat_id, u"Регулярное выражение <b>{0}</b>. Удалить /regex_remove_{1}".format(regex.regex, regex.id), parse_mode='html')
            else:
                await bot.sendMessage(chat_id, 'Неизвестная команда.')
        except Exception as e:
            logging.exception(e)
            for chat_id in [x.chat_id for x in session.query(Chat).filter(Chat.admin == True).all()]:
                await bot.sendMessage(chat_id=chat_id,
                                      text='Exception {} with {}'.format(str(e), traceback.format_exc()))
        finally:
            session.close()

    bot = telepot.aio.Bot(TOKEN)
    answerer = telepot.aio.helper.Answerer(bot)
    loop = asyncio.get_event_loop()
    loop.create_task(send_themes())
    loop.create_task(MessageLoop(bot, {'chat': on_chat_message}).run_forever())
    loop.run_forever()


if __name__ == "__main__":
    main()
