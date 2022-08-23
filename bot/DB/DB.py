from logging import getLogger
from sqlite3 import OperationalError

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError, DataError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

# создаем класс, от которого будут наследоваться модели
Base_shared = declarative_base()
Base_user = declarative_base()
log = getLogger()
import scripts.globals as global_var

pause_period = 0.5


class DBSession(object):
    _session: Session

    def __init__(self, session: Session, *args, **kwargs):
        self._session = session

    def query(self, *entities, **kwargs):
        return self._session.query(*entities, **kwargs)

    def add(self, obj):
        self._session.add(obj)

    def add_all(self, obj):
        self._session.add_all(obj)

    # def update(self, values, synchronize_session="evaluate", update_args=None):
    #     return self._session.update(values)

    def close_session(self):
        try:
            self._session.close()
        except IntegrityError as e:
            log.error(f'`{__name__}` {e}')
            raise
        except DataError as e:
            log.error(f'`{__name__}` {e}')
            raise

    def commit_session(self, need_close: bool = False):
        operation_done = False
        try:
            self._session.commit()
            operation_done = True
        except IntegrityError as e:
            log.error(f'`{__name__}` {e}')
            raise
        except DataError as e:
            log.error(f'`{__name__}` {e}')
            raise
        except Exception as inst:
            self._session.rollback()
            if "database is locked" in inst.args[0]:
                print(inst.args[0])
                from time import sleep
                sleep(pause_period)
        if need_close:
            self.close_session()

        return operation_done


def connect(base: str) -> DBSession:
    if base == "shared":
        base_path = global_var.base_name
    elif base == "private":
        base_path = global_var.base_name_private
    else:
        base_path = base
    engine = create_engine(f'sqlite:///{base_path}?check_same_thread=False', )
    session_factory = sessionmaker(bind=engine)

    return DBSession(session_factory())
