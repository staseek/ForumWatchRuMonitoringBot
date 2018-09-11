import config
import uuid
from sqlalchemy import Column, Integer, DateTime, Text, Boolean


class WatchRuTheme(config.Base):
    __tablename__ = 'whatch_ru_theme'
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(Text, primary_key=True, default=lambda: uuid.uuid4().hex)
    theme_id = Column(Integer)
    theme_name = Column(Text)
    section = Column(Text)
    section_id = Column(Integer)
    pdf_path = Column(Text)
    screenshot_path = Column(Text)
    last_update = Column(DateTime)
    sended = Column(Boolean)
    was_updated = Column(Boolean)


class Chat(config.Base):
    __tablename__ = 'chats'
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(Text, primary_key=True, default=lambda: uuid.uuid4().hex)
    chat_id = Column(Integer)
    admin = Column(Boolean)
    tg_ans = Column(Text)

    def __str__(self):
        import json
        return json.dumps(self.__dict__, default=str, indent=4)


class Regexes(config.Base):
    __tablename__ = 'regexes'
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(Text, primary_key=True, default=lambda: uuid.uuid4().hex)
    chat_id = Column(Integer)
    regex = Column(Text)


# config.Base.metadata.drop_all(config.engine)
config.Base.metadata.create_all(config.engine)
