from __future__ import absolute_import
import constants
TEST_DATABASE = 'samapper_test'
constants.dbconfig['db'] = TEST_DATABASE
import common
import integrity
from MySQLdb import OperationalError
import models.datasources
import models.subscriptions
import web.template
import importers.import_base
import preprocess
import models.links
import models.nodes
from datetime import datetime
import time


class mocker(object):
    def __init__(self, *args, **kwargs):
        self.constructor = (args, kwargs)
        self.kvs = {}
        self.calls = []

    def __getitem__(self, k):
        self.kvs.__getitem__(k)

    def __setitem__(self, k, v):
        self.kvs.__setitem__(k, v)

    def __getattr__(self, name):
        q = self.calls
        def receiver(*args, **kwargs):
            q.append((name, args, kwargs))
        return receiver

    def clear(self):
        self.calls = []

    def was_called(self, name, *args, **kwargs):
        for call in self.calls:
            if call == (name, args, kwargs):
                return True
        return False


class session(dict):
    def kill(self):
        self.clear()


class env():
    def __init__(self, mock_input=False, login_active=None, mock_session=False, mock_render=False):
        self.input_real = web.input
        self.active_old = constants.access_control['active']
        self.session = common.session
        self.render = common.render

        self.mock_input = mock_input
        self.mock_login = login_active
        self.mock_render = mock_render
        self.mock_session = mock_session

    def __enter__(self):
        if self.mock_input:
            web.input = lambda: {}
        if self.mock_login is True:
            constants.access_control['active'] = True
        elif self.mock_login is False:
            constants.access_control['active'] = False
        if self.mock_session:
            common.session = session()
        if self.mock_render:
            common.render = mocker()

    def __exit__(self, type, value, traceback):
        if self.mock_input:
            web.input = self.input_real
        if self.mock_login:
            constants.access_control['active'] = self.active_old
        if self.mock_session:
            common.session = self.session
        if self.mock_render:
            common.render = self.render


def make_timestamp(timestring):
    d = datetime.strptime(timestring, "%Y-%m-%d %H:%M")
    ts = time.mktime(d.timetuple())
    return int(ts)


def get_test_db_connection():
    constants.dbconfig['db'] = TEST_DATABASE
    db = web.database(**constants.dbconfig)
    common.db = db
    try:
        # dummy query to test db connection
        tables = db.query("SHOW TABLES")
    except OperationalError as e:
        print("Error establishing db connection.")
        print e
        create_test_database()
        try:
            # dummy query to test db connection
            tables = db.query("SHOW TABLES")
        except OperationalError as e:
            print("Error establishing db connection.")
            raise e

    rows = db.query("SELECT DATABASE();")
    row = rows.first()
    if row['DATABASE()'] == TEST_DATABASE:
        return db
    else:
        print("Database name doesn't match")
        raise ValueError("Test Database not available")


def create_test_database():
    # creates all the default tables and profile.
    integrity.check_and_fix_integrity()
    setup_datasources()


def setup_datasources():
    d = models.datasources.Datasources({}, constants.demo['id'])
    sources = d.datasources
    remaining = ['default', 'short', 'live']
    for ds in sources.values():
        if ds.name in remaining:
            remaining.remove(ds.name)
        else:
            d.remove_datasource(ds.id)
    for ds_name in remaining:
        d.create_datasource(ds_name)


def template_sql(path, *args):
    tmpl = web.template.Template(open(path).read())
    commands = common.parse_sql_string(unicode(tmpl(*args)), {})
    return commands


def clear_network(db, sub, ds):
    l_model = models.links.Links(sub, ds)
    l_model.delete_connections()

    n_model = models.nodes.Nodes(sub)
    n_model.delete_custom_tags()
    n_model.delete_custom_envs()
    n_model.delete_custom_hostnames()
    db.query("DELETE FROM {table}".format(table=n_model.table_nodes))


def setup_network(db, sub_id, ds_id):
    clear_network(db, sub_id, ds_id)
    loader = importers.import_base.BaseImporter()
    loader.subscription = sub_id
    loader.datasource = ds_id
    processor = preprocess.Preprocessor(db, sub_id, ds_id)

    # used to generate network data for testing
    #def rand_time():
    #    d_start = datetime(2017, 3, 21, 6, 13, 05)
    #    d_end = datetime(2017, 3, 24, 13, 30, 54)
    #    delta = (d_end - d_start).total_seconds()
    #    offset = random.randint(0, delta)
    #    d_rand = d_start + timedelta(seconds=offset)
    #    return d_rand
    #t = common.IPStringtoInt
    #IPS = ['10.20.30.40','10.20.30.41','10.20.32.42','10.20.32.43','10.24.34.44','10.24.34.45',
    #       '10.24.36.46','10.24.36.47','50.60.70.80','50.60.70.81','50.60.72.82','50.60.72.83',
    #       '50.64.74.84','50.64.74.85','50.64.76.86','50.64.76.87','59.69.79.89']
    #ports = [136, 511]
    #protocols = ['UDP', 'TCP']
    #bytes_outs = [200, 500, 1000]
    #bytes_ins = [50, 100, 500]
    #packets_outs = [1, 4]
    #packets_ins = [1, 4]
    #durations = [3, 60]
    #
    #log_lines = []
    #for port in ports:
    #    for protocol in protocols:
    #        for b_o in bytes_outs:
    #            for b_i in bytes_ins:
    #                for p_o in packets_outs:
    #                    for p_i in packets_ins:
    #                        for d in durations:
    #                            log_lines.append([t(random.choice(IPS)), 12345, t(random.choice(IPS)), port, rand_time(), protocol, b_o, b_i, p_o, p_i, d])
    # # for lines that aren't 169090600, shuffle the ports.
    # for line in lines:
    #     line[3] = random.randint(10, 50) * 8
    # 169090600 is 10.20.30.40

    when1 = datetime(2016, 1, 17, 13, 24, 35)
    when2 = datetime(2017, 2, 18, 14, 25, 36)
    when3 = datetime(2018, 3, 19, 15, 26, 37)
    t = common.IPStringtoInt

    log_lines = [
        [t('110.20.30.40'), 12345, t('110.20.30.40'), 180, when1, 'TCP', 100, 0, 1, 0, 5],
        [t('110.20.30.40'), 12345, t('110.20.30.41'), 180, when2, 'TCP', 100, 0, 1, 0, 5],
        [t('110.20.30.40'), 12345, t('110.20.32.42'), 180, when3, 'TCP', 100, 0, 1, 0, 5],
        [t('110.20.30.40'), 12345, t('110.20.32.43'), 180, when3, 'TCP', 100, 0, 1, 0, 5],
        [t('110.20.30.40'), 12345, t('110.24.34.44'), 1443, when1, 'TCP', 100, 0, 1, 0, 5],
        [t('110.20.30.40'), 12345, t('110.24.34.45'), 1443, when2, 'TCP', 100, 0, 1, 0, 5],
        [t('110.20.30.40'), 12345, t('110.24.36.46'), 1443, when3, 'TCP', 100, 0, 1, 0, 5],
        [t('110.20.30.40'), 12345, t('110.24.36.47'), 1443, when3, 'TCP', 100, 0, 1, 0, 5],
        [t('110.20.30.40'), 12345, t('150.60.70.80'), 180, when1, 'UDP', 100, 0, 1, 0, 5],
        [t('110.20.30.40'), 12345, t('150.60.70.81'), 180, when2, 'UDP', 100, 0, 1, 0, 5],
        [t('110.20.30.40'), 12345, t('150.60.72.82'), 180, when2, 'UDP', 100, 0, 1, 0, 5],
        [t('110.20.30.40'), 12345, t('150.60.72.83'), 180, when3, 'UDP', 100, 0, 1, 0, 5],
        [t('110.20.30.40'), 12345, t('150.64.74.84'), 1443, when1, 'UDP', 100, 0, 1, 0, 5],
        [t('110.20.30.40'), 12345, t('150.64.74.85'), 1443, when1, 'UDP', 100, 0, 1, 0, 5],
        [t('110.20.30.40'), 12345, t('150.64.76.86'), 1443, when2, 'UDP', 100, 0, 1, 0, 5],
        [t('110.20.30.40'), 12345, t('150.64.76.87'), 1443, when3, 'UDP', 100, 0, 1, 0, 5],
        [t('159.69.79.89'), 12345, t('110.20.30.40'), 180, when1, 'ICMP', 100, 0, 1, 0, 5],
        [t('159.69.79.89'), 12345, t('110.20.30.40'), 1443, when2, 'ICMP', 100, 0, 1, 0, 5],
        [t('159.69.79.89'), 12345, t('110.20.30.40'), 180, when3, 'ICMP', 100, 0, 1, 0, 5],
        [843074133, 12345, 169090600, 136, datetime(2017, 3, 23, 5, 24, 21), 'UDP', 1000, 500, 4, 1, 60],
        [843074133, 12345, 169090600, 136, datetime(2017, 3, 23, 20, 28, 34), 'TCP', 500, 100, 1, 1, 60],
        [843074132, 12345, 169090600, 511, datetime(2017, 3, 24, 6, 49, 51), 'TCP', 200, 100, 4, 4, 3],
        [843074132, 12345, 169090600, 511, datetime(2017, 3, 22, 13, 53, 25), 'TCP', 500, 100, 4, 4, 3],
        [169354286, 12345, 169090600, 511, datetime(2017, 3, 22, 12, 42, 36), 'UDP', 500, 500, 1, 1, 60],
        [169353773, 12345, 169090600, 136, datetime(2017, 3, 22, 16, 17, 17), 'UDP', 500, 500, 1, 4, 60],
        [169353772, 12345, 169090600, 136, datetime(2017, 3, 22, 12, 35, 12), 'UDP', 500, 100, 1, 1, 60],
        [169353772, 12345, 169090600, 136, datetime(2017, 3, 23, 7, 5, 56), 'TCP', 1000, 50, 4, 1, 60],
        [169091115, 12345, 169090600, 511, datetime(2017, 3, 21, 6, 39, 54), 'TCP', 1000, 500, 1, 4, 3],
        [169091114, 12345, 169090600, 136, datetime(2017, 3, 21, 8, 52, 27), 'TCP', 1000, 50, 4, 4, 3],
        [169090600, 12345, 169090600, 511, datetime(2017, 3, 23, 8, 21, 51), 'UDP', 500, 50, 4, 4, 3],
        [169090600, 12345, 169090600, 511, datetime(2017, 3, 23, 14, 26, 43), 'TCP', 1000, 100, 4, 4, 3],
        [169090600, 12345, 169090600, 136, datetime(2017, 3, 23, 14, 5, 25), 'TCP', 200, 100, 1, 4, 60],
        [169090600, 12345, 169091114, 511, datetime(2017, 3, 21, 8, 1, 11), 'UDP', 1000, 50, 1, 1, 3],
        [169090600, 12345, 169353772, 136, datetime(2017, 3, 22, 20, 25, 56), 'TCP', 1000, 100, 1, 1, 3],
        [169090600, 12345, 169353772, 511, datetime(2017, 3, 23, 5, 54, 10), 'UDP', 1000, 50, 4, 4, 3],
        [169090600, 12345, 169353773, 136, datetime(2017, 3, 23, 3, 14), 'TCP', 200, 500, 4, 1, 3],
        [169090600, 12345, 169354286, 136, datetime(2017, 3, 24, 7, 31, 9), 'UDP', 200, 100, 1, 1, 3],
        [169090600, 12345, 169354286, 136, datetime(2017, 3, 23, 16, 50, 55), 'TCP', 200, 100, 4, 1, 60],
        [169090600, 12345, 842810960, 136, datetime(2017, 3, 24, 2, 15, 23), 'TCP', 200, 100, 4, 1, 3],
        [169090600, 12345, 842810961, 511, datetime(2017, 3, 24, 6, 58, 48), 'TCP', 200, 50, 4, 4, 60],
        [169090600, 12345, 842811474, 511, datetime(2017, 3, 24, 1, 21, 2), 'TCP', 500, 100, 1, 4, 3],
        [169090600, 12345, 842811474, 511, datetime(2017, 3, 23, 4, 0, 13), 'TCP', 1000, 100, 4, 1, 60],
        [169090600, 12345, 842811475, 511, datetime(2017, 3, 22, 4, 53, 26), 'UDP', 500, 50, 4, 4, 60],
        [169090600, 12345, 842811475, 511, datetime(2017, 3, 23, 0, 39, 51), 'TCP', 200, 50, 4, 1, 3],
        [169090600, 12345, 842811475, 511, datetime(2017, 3, 21, 19, 34, 58), 'TCP', 500, 100, 1, 1, 3],
        [169090600, 12345, 842811475, 511, datetime(2017, 3, 21, 8, 53, 24), 'TCP', 1000, 100, 1, 1, 3],
        [169090600, 12345, 843074132, 136, datetime(2017, 3, 23, 1, 59, 58), 'UDP', 1000, 500, 1, 4, 60],
        [169090600, 12345, 843074132, 136, datetime(2017, 3, 23, 6, 9, 39), 'UDP', 1000, 500, 4, 1, 3],
        [169090600, 12345, 843074133, 511, datetime(2017, 3, 23, 6, 37, 5), 'UDP', 1000, 50, 1, 4, 3],
        [169090600, 12345, 843074133, 136, datetime(2017, 3, 21, 10, 37, 21), 'UDP', 500, 100, 4, 4, 60],
        [169090600, 12345, 843074646, 511, datetime(2017, 3, 24, 7, 17, 29), 'TCP', 200, 500, 4, 4, 3],
        [169090600, 12345, 843074647, 511, datetime(2017, 3, 21, 21, 32, 57), 'UDP', 500, 500, 4, 4, 3],
        [169090600, 12345, 994398041, 511, datetime(2017, 3, 21, 18, 0, 5), 'TCP', 200, 100, 4, 4, 60],
        [842811475, 12345, 842810961, 104, datetime(2017, 3, 21, 14, 42, 54), 'UDP', 200, 50, 1, 1, 3],
        [169354286, 12345, 843074133, 256, datetime(2017, 3, 21, 22, 25, 18), 'UDP', 200, 50, 1, 1, 60],
        [842810960, 12345, 842811475, 400, datetime(2017, 3, 23, 22, 16, 12), 'UDP', 200, 50, 1, 4, 3],
        [169090601, 12345, 842810961, 240, datetime(2017, 3, 23, 16, 19, 11), 'UDP', 200, 50, 1, 4, 60],
        [169354287, 12345, 169353773, 312, datetime(2017, 3, 24, 1, 43, 29), 'UDP', 200, 50, 4, 1, 3],
        [169353773, 12345, 842811475, 256, datetime(2017, 3, 22, 13, 36, 25), 'UDP', 200, 50, 4, 1, 60],
        [843074646, 12345, 169091114, 184, datetime(2017, 3, 23, 0, 44, 5), 'UDP', 200, 50, 4, 4, 3],
        [843074647, 12345, 843074647, 312, datetime(2017, 3, 22, 6, 43, 15), 'UDP', 200, 50, 4, 4, 60],
        [843074647, 12345, 842810960, 360, datetime(2017, 3, 22, 6, 24, 35), 'UDP', 200, 100, 1, 1, 60],
        [169353772, 12345, 169091115, 336, datetime(2017, 3, 23, 17, 34, 59), 'UDP', 200, 100, 1, 4, 3],
        [842811475, 12345, 169091114, 232, datetime(2017, 3, 22, 5, 48, 31), 'UDP', 200, 100, 1, 4, 60],
        [994398041, 12345, 169091114, 376, datetime(2017, 3, 24, 3, 43, 59), 'UDP', 200, 100, 4, 1, 3],
        [169091114, 12345, 843074647, 320, datetime(2017, 3, 23, 6, 42, 19), 'UDP', 200, 100, 4, 1, 60],
        [169354286, 12345, 169091114, 96, datetime(2017, 3, 24, 10, 10, 3), 'UDP', 200, 100, 4, 4, 3],
        [169354287, 12345, 843074646, 288, datetime(2017, 3, 23, 6, 39, 12), 'UDP', 200, 100, 4, 4, 60],
        [843074132, 12345, 842810960, 160, datetime(2017, 3, 22, 8, 38, 45), 'UDP', 200, 500, 1, 1, 3],
        [842810960, 12345, 843074132, 160, datetime(2017, 3, 22, 1, 38, 38), 'UDP', 200, 500, 1, 1, 60],
        [842810960, 12345, 169353773, 392, datetime(2017, 3, 23, 0, 17, 58), 'UDP', 200, 500, 1, 4, 3],
        [169091115, 12345, 169091115, 344, datetime(2017, 3, 23, 21, 24, 44), 'UDP', 200, 500, 1, 4, 60],
        [169353773, 12345, 843074132, 328, datetime(2017, 3, 23, 11, 52, 34), 'UDP', 200, 500, 4, 1, 3],
        [843074646, 12345, 169091115, 392, datetime(2017, 3, 21, 10, 15, 24), 'UDP', 200, 500, 4, 1, 60],
        [842810961, 12345, 842811474, 296, datetime(2017, 3, 23, 19, 18, 26), 'UDP', 200, 500, 4, 4, 3],
        [169354287, 12345, 169354287, 392, datetime(2017, 3, 22, 3, 23, 27), 'UDP', 200, 500, 4, 4, 60],
        [842811474, 12345, 843074646, 224, datetime(2017, 3, 23, 0, 47, 4), 'UDP', 500, 50, 1, 1, 3],
        [169353773, 12345, 843074647, 192, datetime(2017, 3, 22, 22, 10, 42), 'UDP', 500, 50, 1, 1, 60],
        [169353772, 12345, 842810961, 328, datetime(2017, 3, 23, 13, 10, 39), 'UDP', 500, 50, 1, 4, 3],
        [169354287, 12345, 169354286, 152, datetime(2017, 3, 21, 14, 20, 44), 'UDP', 500, 50, 1, 4, 60],
        [843074646, 12345, 994398041, 344, datetime(2017, 3, 24, 13, 16, 27), 'UDP', 500, 50, 4, 1, 3],
        [842811474, 12345, 169090601, 112, datetime(2017, 3, 23, 21, 27, 25), 'UDP', 500, 50, 4, 1, 60],
        [842810960, 12345, 843074132, 248, datetime(2017, 3, 23, 6, 16, 52), 'UDP', 500, 50, 4, 4, 3],
        [169354287, 12345, 842811475, 208, datetime(2017, 3, 23, 13, 29, 47), 'UDP', 500, 50, 4, 4, 60],
        [842810961, 12345, 843074133, 256, datetime(2017, 3, 22, 8, 52, 47), 'UDP', 500, 100, 1, 1, 3],
        [169090601, 12345, 842810961, 240, datetime(2017, 3, 21, 8, 2, 27), 'UDP', 500, 100, 1, 4, 3],
        [169353773, 12345, 169091115, 280, datetime(2017, 3, 23, 18, 4, 45), 'UDP', 500, 100, 1, 4, 60],
        [169353772, 12345, 843074647, 136, datetime(2017, 3, 22, 6, 10, 44), 'UDP', 500, 100, 4, 1, 3],
        [842810961, 12345, 169091114, 352, datetime(2017, 3, 21, 15, 9, 6), 'UDP', 500, 100, 4, 1, 60],
        [842811474, 12345, 843074132, 120, datetime(2017, 3, 23, 22, 33, 9), 'UDP', 500, 100, 4, 4, 3],
        [169091115, 12345, 843074647, 176, datetime(2017, 3, 24, 8, 20, 39), 'UDP', 500, 500, 1, 1, 3],
        [843074646, 12345, 994398041, 216, datetime(2017, 3, 21, 22, 10, 56), 'UDP', 500, 500, 1, 1, 60],
        [843074646, 12345, 169354286, 216, datetime(2017, 3, 22, 18, 0, 1), 'UDP', 500, 500, 1, 4, 3],
        [169354287, 12345, 842811475, 264, datetime(2017, 3, 23, 9, 14, 2), 'UDP', 500, 500, 4, 1, 3],
        [169090601, 12345, 843074646, 136, datetime(2017, 3, 22, 1, 12, 35), 'UDP', 500, 500, 4, 1, 60],
        [169091115, 12345, 994398041, 144, datetime(2017, 3, 24, 8, 43, 28), 'UDP', 500, 500, 4, 4, 3],
        [842810960, 12345, 842810961, 128, datetime(2017, 3, 24, 0, 24, 21), 'UDP', 500, 500, 4, 4, 60],
        [842810960, 12345, 169353773, 128, datetime(2017, 3, 22, 9, 17, 48), 'UDP', 1000, 50, 1, 1, 3],
        [169354287, 12345, 843074647, 232, datetime(2017, 3, 24, 2, 47, 30), 'UDP', 1000, 50, 1, 1, 60],
        [169353772, 12345, 169090601, 288, datetime(2017, 3, 21, 21, 29, 44), 'UDP', 1000, 50, 1, 4, 3],
        [169353773, 12345, 842811474, 208, datetime(2017, 3, 22, 12, 45, 16), 'UDP', 1000, 50, 1, 4, 60],
        [842810961, 12345, 169354286, 384, datetime(2017, 3, 24, 12, 57, 35), 'UDP', 1000, 50, 4, 1, 3],
        [843074132, 12345, 842810961, 96, datetime(2017, 3, 21, 14, 37, 32), 'UDP', 1000, 50, 4, 1, 60],
        [842811475, 12345, 842810960, 328, datetime(2017, 3, 24, 13, 19, 54), 'UDP', 1000, 50, 4, 4, 3],
        [843074647, 12345, 169091114, 248, datetime(2017, 3, 23, 4, 53, 13), 'UDP', 1000, 50, 4, 4, 60],
        [169090601, 12345, 169354286, 328, datetime(2017, 3, 22, 10, 59, 25), 'UDP', 1000, 100, 1, 1, 3],
        [842811475, 12345, 843074133, 400, datetime(2017, 3, 21, 19, 35, 25), 'UDP', 1000, 100, 1, 1, 60],
        [169354287, 12345, 169354286, 136, datetime(2017, 3, 24, 12, 10, 26), 'UDP', 1000, 100, 1, 4, 3],
        [169091115, 12345, 169353773, 80, datetime(2017, 3, 21, 16, 20, 3), 'UDP', 1000, 100, 1, 4, 60],
        [843074133, 12345, 842810961, 240, datetime(2017, 3, 23, 7, 44, 28), 'UDP', 1000, 100, 4, 1, 3],
        [842811475, 12345, 169090601, 120, datetime(2017, 3, 21, 13, 20, 31), 'UDP', 1000, 100, 4, 1, 60],
        [842810960, 12345, 842810960, 160, datetime(2017, 3, 22, 8, 0, 1), 'UDP', 1000, 100, 4, 4, 3],
        [169091115, 12345, 169091115, 360, datetime(2017, 3, 22, 5, 58, 24), 'UDP', 1000, 100, 4, 4, 60],
        [842811475, 12345, 169091115, 256, datetime(2017, 3, 21, 12, 13, 36), 'UDP', 1000, 500, 1, 1, 3],
        [169090601, 12345, 842810961, 264, datetime(2017, 3, 21, 16, 24, 51), 'UDP', 1000, 500, 1, 1, 60],
        [169354286, 12345, 169354287, 272, datetime(2017, 3, 23, 12, 20, 26), 'UDP', 1000, 500, 1, 4, 3],
        [169353772, 12345, 169353773, 272, datetime(2017, 3, 22, 1, 26, 12), 'UDP', 1000, 500, 4, 4, 3],
        [843074132, 12345, 169091114, 248, datetime(2017, 3, 22, 2, 43, 22), 'UDP', 1000, 500, 4, 4, 60],
        [842811474, 12345, 843074133, 352, datetime(2017, 3, 21, 7, 32, 26), 'TCP', 200, 50, 1, 1, 3],
        [842811475, 12345, 994398041, 200, datetime(2017, 3, 21, 13, 50, 16), 'TCP', 200, 50, 1, 1, 60],
        [169354287, 12345, 842810961, 144, datetime(2017, 3, 22, 17, 39, 44), 'TCP', 200, 50, 1, 4, 3],
        [843074646, 12345, 843074133, 344, datetime(2017, 3, 21, 15, 57, 15), 'TCP', 200, 50, 1, 4, 60],
        [169090601, 12345, 169354287, 104, datetime(2017, 3, 24, 13, 12, 19), 'TCP', 200, 50, 4, 1, 3],
        [169091114, 12345, 169354286, 136, datetime(2017, 3, 21, 9, 56), 'TCP', 200, 50, 4, 1, 60],
        [843074646, 12345, 843074133, 328, datetime(2017, 3, 22, 18, 42, 41), 'TCP', 200, 50, 4, 4, 3],
        [994398041, 12345, 843074133, 224, datetime(2017, 3, 21, 11, 9, 57), 'TCP', 200, 50, 4, 4, 60],
        [169353772, 12345, 169353772, 272, datetime(2017, 3, 24, 11, 51, 10), 'TCP', 200, 100, 1, 1, 3],
        [169353773, 12345, 843074133, 224, datetime(2017, 3, 23, 4, 28, 36), 'TCP', 200, 100, 1, 1, 60],
        [169091114, 12345, 843074133, 288, datetime(2017, 3, 22, 18, 25, 59), 'TCP', 200, 100, 1, 4, 3],
        [169353772, 12345, 843074646, 80, datetime(2017, 3, 21, 20, 59, 51), 'TCP', 200, 100, 4, 4, 3],
        [169091114, 12345, 169353772, 232, datetime(2017, 3, 24, 1, 41, 9), 'TCP', 200, 100, 4, 4, 60],
        [843074133, 12345, 169091114, 328, datetime(2017, 3, 21, 20, 55, 27), 'TCP', 200, 500, 1, 1, 3],
        [169354287, 12345, 842811474, 264, datetime(2017, 3, 24, 6, 4, 8), 'TCP', 200, 500, 1, 1, 60],
        [169353772, 12345, 843074132, 192, datetime(2017, 3, 22, 22, 29), 'TCP', 200, 500, 1, 4, 3],
        [842810960, 12345, 169354287, 128, datetime(2017, 3, 21, 14, 7, 13), 'TCP', 200, 500, 1, 4, 60],
        [843074133, 12345, 169090601, 192, datetime(2017, 3, 21, 9, 7, 55), 'TCP', 200, 500, 4, 1, 60],
        [994398041, 12345, 843074132, 392, datetime(2017, 3, 21, 11, 32, 47), 'TCP', 200, 500, 4, 4, 3],
        [842811474, 12345, 843074132, 232, datetime(2017, 3, 22, 13, 23, 15), 'TCP', 200, 500, 4, 4, 60],
        [842810960, 12345, 843074133, 328, datetime(2017, 3, 23, 17, 49, 20), 'TCP', 500, 50, 1, 1, 3],
        [169353772, 12345, 169354287, 296, datetime(2017, 3, 23, 8, 55, 52), 'TCP', 500, 50, 1, 1, 60],
        [843074647, 12345, 169091114, 232, datetime(2017, 3, 24, 9, 38, 56), 'TCP', 500, 50, 1, 4, 3],
        [842811475, 12345, 843074647, 264, datetime(2017, 3, 21, 22, 16, 48), 'TCP', 500, 50, 1, 4, 60],
        [842810961, 12345, 843074132, 352, datetime(2017, 3, 23, 0, 33, 7), 'TCP', 500, 50, 4, 1, 3],
        [169354287, 12345, 169090601, 312, datetime(2017, 3, 21, 9, 10, 22), 'TCP', 500, 50, 4, 1, 60],
        [169353772, 12345, 169091114, 392, datetime(2017, 3, 21, 16, 21, 43), 'TCP', 500, 50, 4, 4, 3],
        [843074647, 12345, 169353772, 400, datetime(2017, 3, 23, 2, 15, 54), 'TCP', 500, 50, 4, 4, 60],
        [169353772, 12345, 169353773, 200, datetime(2017, 3, 23, 1, 38, 41), 'TCP', 500, 100, 1, 1, 3],
        [842810960, 12345, 169091114, 336, datetime(2017, 3, 22, 12, 57, 39), 'TCP', 500, 100, 1, 4, 3],
        [169353773, 12345, 842810961, 88, datetime(2017, 3, 24, 7, 27, 37), 'TCP', 500, 100, 1, 4, 60],
        [843074647, 12345, 169353772, 152, datetime(2017, 3, 22, 23, 49, 53), 'TCP', 500, 100, 4, 1, 3],
        [842811474, 12345, 843074132, 272, datetime(2017, 3, 24, 1, 57, 59), 'TCP', 500, 100, 4, 1, 60],
        [842810960, 12345, 169354286, 368, datetime(2017, 3, 22, 17, 43, 8), 'TCP', 500, 100, 4, 4, 3],
        [169354286, 12345, 843074132, 256, datetime(2017, 3, 21, 10, 9, 14), 'TCP', 500, 100, 4, 4, 60],
        [169091115, 12345, 169353772, 128, datetime(2017, 3, 22, 17, 54, 30), 'TCP', 500, 500, 1, 1, 3],
        [169354286, 12345, 843074647, 312, datetime(2017, 3, 23, 11, 39, 10), 'TCP', 500, 500, 1, 1, 60],
        [994398041, 12345, 169091114, 336, datetime(2017, 3, 23, 15, 47, 37), 'TCP', 500, 500, 1, 4, 3],
        [169090601, 12345, 169090601, 352, datetime(2017, 3, 21, 10, 56, 41), 'TCP', 500, 500, 1, 4, 60],
        [994398041, 12345, 169354287, 104, datetime(2017, 3, 24, 4, 35, 38), 'TCP', 500, 500, 4, 1, 3],
        [843074132, 12345, 169090601, 256, datetime(2017, 3, 24, 2, 35, 44), 'TCP', 500, 500, 4, 1, 60],
        [843074646, 12345, 169090601, 104, datetime(2017, 3, 23, 17, 53, 12), 'TCP', 500, 500, 4, 4, 3],
        [994398041, 12345, 843074646, 240, datetime(2017, 3, 21, 15, 11, 32), 'TCP', 500, 500, 4, 4, 60],
        [169354287, 12345, 169090601, 368, datetime(2017, 3, 24, 6, 9, 28), 'TCP', 1000, 50, 1, 1, 3],
        [843074132, 12345, 842811475, 128, datetime(2017, 3, 22, 4, 5, 45), 'TCP', 1000, 50, 1, 1, 60],
        [843074133, 12345, 994398041, 280, datetime(2017, 3, 23, 13, 21, 18), 'TCP', 1000, 50, 1, 4, 3],
        [842811474, 12345, 843074646, 400, datetime(2017, 3, 23, 8, 26, 26), 'TCP', 1000, 50, 1, 4, 60],
        [843074133, 12345, 169091114, 136, datetime(2017, 3, 21, 17, 0, 40), 'TCP', 1000, 50, 4, 1, 3],
        [994398041, 12345, 169091114, 304, datetime(2017, 3, 24, 11, 44, 50), 'TCP', 1000, 50, 4, 4, 60],
        [169353772, 12345, 842811474, 144, datetime(2017, 3, 22, 6, 55, 28), 'TCP', 1000, 100, 1, 1, 60],
        [842811474, 12345, 169091115, 352, datetime(2017, 3, 24, 7, 34, 14), 'TCP', 1000, 100, 1, 4, 3],
        [843074133, 12345, 994398041, 336, datetime(2017, 3, 23, 6, 9, 45), 'TCP', 1000, 100, 1, 4, 60],
        [169353772, 12345, 842811475, 88, datetime(2017, 3, 23, 3, 30, 57), 'TCP', 1000, 100, 4, 1, 3],
        [994398041, 12345, 994398041, 336, datetime(2017, 3, 21, 12, 18, 52), 'TCP', 1000, 100, 4, 1, 60],
        [169354286, 12345, 842811474, 392, datetime(2017, 3, 22, 8, 32, 6), 'TCP', 1000, 100, 4, 4, 3],
        [842810961, 12345, 843074647, 312, datetime(2017, 3, 23, 7, 9, 52), 'TCP', 1000, 100, 4, 4, 60],
        [843074646, 12345, 843074133, 296, datetime(2017, 3, 22, 9, 2, 56), 'TCP', 1000, 500, 1, 1, 3],
        [169354287, 12345, 169353772, 344, datetime(2017, 3, 23, 15, 10, 2), 'TCP', 1000, 500, 1, 1, 60],
        [842811475, 12345, 843074132, 104, datetime(2017, 3, 23, 3, 53), 'TCP', 1000, 500, 1, 4, 3],
        [169354287, 12345, 169353773, 272, datetime(2017, 3, 23, 7, 50, 43), 'TCP', 1000, 500, 1, 4, 60],
        [842811474, 12345, 169354287, 168, datetime(2017, 3, 23, 14, 52, 41), 'TCP', 1000, 500, 4, 1, 3],
        [843074646, 12345, 169353772, 192, datetime(2017, 3, 24, 3, 19, 4), 'TCP', 1000, 500, 4, 1, 60],
        [994398041, 12345, 169353772, 248, datetime(2017, 3, 21, 17, 14, 8), 'TCP', 1000, 500, 4, 4, 3],
        [843074646, 12345, 842811475, 200, datetime(2017, 3, 24, 4, 25, 1), 'TCP', 1000, 500, 4, 4, 60],
        [842811475, 12345, 842810960, 312, datetime(2017, 3, 24, 4, 58, 39), 'UDP', 200, 50, 1, 1, 3],
        [842811474, 12345, 842810961, 384, datetime(2017, 3, 21, 22, 51, 24), 'UDP', 200, 50, 1, 1, 60],
        [843074132, 12345, 843074133, 376, datetime(2017, 3, 23, 11, 25, 22), 'UDP', 200, 50, 1, 4, 3],
        [842810960, 12345, 169353773, 136, datetime(2017, 3, 23, 5, 49, 51), 'UDP', 200, 50, 1, 4, 60],
        [843074133, 12345, 169353773, 248, datetime(2017, 3, 21, 17, 47, 4), 'UDP', 200, 50, 4, 1, 3],
        [842811474, 12345, 842811475, 104, datetime(2017, 3, 21, 14, 13, 59), 'UDP', 200, 50, 4, 1, 60],
        [842810960, 12345, 169354286, 384, datetime(2017, 3, 23, 13, 41, 20), 'UDP', 200, 50, 4, 4, 3],
        [169353773, 12345, 169090601, 192, datetime(2017, 3, 22, 3, 32, 50), 'UDP', 200, 50, 4, 4, 60],
        [169354287, 12345, 169090601, 312, datetime(2017, 3, 22, 23, 39, 20), 'UDP', 200, 100, 1, 1, 3],
        [169091115, 12345, 842811474, 272, datetime(2017, 3, 24, 6, 1, 28), 'UDP', 200, 100, 1, 1, 60],
        [169091115, 12345, 842811474, 184, datetime(2017, 3, 24, 10, 40, 31), 'UDP', 200, 100, 1, 4, 3],
        [169354287, 12345, 842811474, 88, datetime(2017, 3, 23, 18, 5, 48), 'UDP', 200, 100, 1, 4, 60],
        [169091115, 12345, 169091115, 184, datetime(2017, 3, 22, 5, 14, 15), 'UDP', 200, 100, 4, 1, 3],
        [169090601, 12345, 843074133, 120, datetime(2017, 3, 21, 9, 7, 26), 'UDP', 200, 100, 4, 1, 60],
        [843074133, 12345, 169353773, 184, datetime(2017, 3, 22, 4, 2, 25), 'UDP', 200, 100, 4, 4, 3],
        [843074646, 12345, 994398041, 88, datetime(2017, 3, 23, 16, 56, 4), 'UDP', 200, 100, 4, 4, 60],
        [169353772, 12345, 994398041, 256, datetime(2017, 3, 21, 22, 38, 7), 'UDP', 200, 500, 1, 1, 3],
        [994398041, 12345, 169353772, 88, datetime(2017, 3, 22, 7, 53, 56), 'UDP', 200, 500, 1, 1, 60],
        [843074646, 12345, 169353773, 96, datetime(2017, 3, 22, 20, 36, 10), 'UDP', 200, 500, 1, 4, 3],
        [843074647, 12345, 169354286, 392, datetime(2017, 3, 23, 18, 28, 33), 'UDP', 200, 500, 1, 4, 60],
        [842810961, 12345, 169353773, 208, datetime(2017, 3, 23, 7, 36, 29), 'UDP', 200, 500, 4, 1, 3],
        [842811475, 12345, 169353772, 160, datetime(2017, 3, 24, 10, 31, 27), 'UDP', 200, 500, 4, 1, 60],
        [842811475, 12345, 842811474, 240, datetime(2017, 3, 23, 9, 28, 41), 'UDP', 200, 500, 4, 4, 3],
        [169091115, 12345, 169091114, 112, datetime(2017, 3, 22, 13, 22, 48), 'UDP', 200, 500, 4, 4, 60],
        [843074647, 12345, 843074133, 216, datetime(2017, 3, 21, 21, 54, 36), 'UDP', 500, 50, 1, 1, 3],
        [843074133, 12345, 842810961, 144, datetime(2017, 3, 24, 3, 11, 20), 'UDP', 500, 50, 1, 1, 60],
        [169354287, 12345, 843074647, 96, datetime(2017, 3, 21, 18, 25, 46), 'UDP', 500, 50, 1, 4, 3],
        [169354287, 12345, 169354286, 272, datetime(2017, 3, 24, 1, 28, 46), 'UDP', 500, 50, 1, 4, 60],
        [169354286, 12345, 169354286, 272, datetime(2017, 3, 22, 20, 31, 48), 'UDP', 500, 50, 4, 1, 3],
        [843074646, 12345, 842811475, 288, datetime(2017, 3, 23, 3, 55, 22), 'UDP', 500, 50, 4, 1, 60],
        [843074132, 12345, 843074647, 360, datetime(2017, 3, 22, 23, 9, 5), 'UDP', 500, 100, 1, 1, 3],
        [169091115, 12345, 169090601, 368, datetime(2017, 3, 23, 6, 40, 18), 'UDP', 500, 100, 1, 1, 60],
        [994398041, 12345, 843074646, 248, datetime(2017, 3, 22, 1, 27, 14), 'UDP', 500, 100, 1, 4, 3],
        [843074132, 12345, 843074133, 88, datetime(2017, 3, 23, 17, 32, 36), 'UDP', 500, 100, 1, 4, 60],
        [169354287, 12345, 169353772, 184, datetime(2017, 3, 24, 8, 54, 54), 'UDP', 500, 100, 4, 1, 3],
        [843074647, 12345, 169353773, 96, datetime(2017, 3, 23, 19, 33, 4), 'UDP', 500, 100, 4, 1, 60],
        [169091115, 12345, 169353773, 304, datetime(2017, 3, 22, 12, 5, 8), 'UDP', 500, 100, 4, 4, 3],
        [169090601, 12345, 994398041, 160, datetime(2017, 3, 22, 7, 27, 22), 'UDP', 500, 100, 4, 4, 60],
        [169091115, 12345, 169354287, 328, datetime(2017, 3, 21, 19, 33, 33), 'UDP', 500, 500, 1, 1, 3],
        [842811474, 12345, 169090601, 320, datetime(2017, 3, 23, 3, 13, 54), 'UDP', 500, 500, 1, 4, 3],
        [842810960, 12345, 169353772, 264, datetime(2017, 3, 22, 0, 37, 45), 'UDP', 500, 500, 1, 4, 60],
        [843074647, 12345, 842810961, 352, datetime(2017, 3, 22, 22, 44, 49), 'UDP', 500, 500, 4, 1, 3],
        [169354287, 12345, 842810960, 120, datetime(2017, 3, 23, 10, 53, 5), 'UDP', 500, 500, 4, 1, 60],
        [169091114, 12345, 169353772, 80, datetime(2017, 3, 22, 2, 12, 46), 'UDP', 500, 500, 4, 4, 60],
        [994398041, 12345, 169091115, 352, datetime(2017, 3, 23, 4, 25, 22), 'UDP', 1000, 50, 1, 1, 60],
        [842811475, 12345, 169353773, 224, datetime(2017, 3, 22, 8, 56, 45), 'UDP', 1000, 50, 1, 4, 60],
        [842811474, 12345, 842810961, 240, datetime(2017, 3, 21, 22, 9, 3), 'UDP', 1000, 50, 4, 1, 3],
        [842811475, 12345, 842810961, 144, datetime(2017, 3, 23, 22, 14, 52), 'UDP', 1000, 50, 4, 1, 60],
        [843074647, 12345, 169354287, 400, datetime(2017, 3, 24, 10, 21, 27), 'UDP', 1000, 50, 4, 4, 60],
        [842810960, 12345, 169090601, 256, datetime(2017, 3, 22, 17, 53, 6), 'UDP', 1000, 100, 1, 1, 3],
        [842810961, 12345, 842810960, 224, datetime(2017, 3, 22, 8, 9, 11), 'UDP', 1000, 100, 1, 1, 60],
        [842811474, 12345, 843074132, 88, datetime(2017, 3, 24, 1, 57, 33), 'UDP', 1000, 100, 1, 4, 3],
        [169353773, 12345, 842811475, 104, datetime(2017, 3, 22, 22, 18, 2), 'UDP', 1000, 100, 1, 4, 60],
        [843074133, 12345, 169091115, 112, datetime(2017, 3, 23, 21, 36, 57), 'UDP', 1000, 100, 4, 1, 3],
        [843074646, 12345, 169353772, 152, datetime(2017, 3, 22, 19, 21, 31), 'UDP', 1000, 100, 4, 1, 60],
        [843074647, 12345, 169091115, 392, datetime(2017, 3, 22, 13, 15, 3), 'UDP', 1000, 100, 4, 4, 3],
        [169090601, 12345, 169091115, 288, datetime(2017, 3, 21, 13, 52, 21), 'UDP', 1000, 100, 4, 4, 60],
        [169353772, 12345, 842811475, 184, datetime(2017, 3, 22, 2, 33, 53), 'UDP', 1000, 500, 1, 1, 3],
        [843074646, 12345, 169091115, 400, datetime(2017, 3, 23, 12, 5, 40), 'UDP', 1000, 500, 1, 1, 60],
        [169353773, 12345, 169354286, 344, datetime(2017, 3, 22, 2, 38, 42), 'UDP', 1000, 500, 1, 4, 3],
        [169091114, 12345, 169353772, 168, datetime(2017, 3, 23, 21, 50, 30), 'UDP', 1000, 500, 1, 4, 60],
        [843074132, 12345, 842811475, 320, datetime(2017, 3, 24, 13, 5, 19), 'UDP', 1000, 500, 4, 1, 3],
        [169091115, 12345, 842811474, 192, datetime(2017, 3, 23, 8, 35, 52), 'UDP', 1000, 500, 4, 1, 60],
        [994398041, 12345, 842810960, 360, datetime(2017, 3, 21, 22, 53, 15), 'UDP', 1000, 500, 4, 4, 3],
        [842810961, 12345, 169353773, 176, datetime(2017, 3, 23, 2, 12, 34), 'UDP', 1000, 500, 4, 4, 60],
        [994398041, 12345, 842811475, 136, datetime(2017, 3, 21, 6, 35, 17), 'TCP', 200, 50, 1, 1, 3],
        [169091114, 12345, 169091114, 352, datetime(2017, 3, 22, 21, 59, 57), 'TCP', 200, 50, 1, 1, 60],
        [169354286, 12345, 169354287, 400, datetime(2017, 3, 23, 14, 12, 21), 'TCP', 200, 50, 1, 4, 3],
        [842810960, 12345, 169353772, 256, datetime(2017, 3, 21, 10, 21, 28), 'TCP', 200, 50, 1, 4, 60],
        [842810961, 12345, 842811474, 296, datetime(2017, 3, 22, 14, 28, 20), 'TCP', 200, 50, 4, 1, 60],
        [842810961, 12345, 843074646, 104, datetime(2017, 3, 23, 20, 35, 2), 'TCP', 200, 50, 4, 4, 3],
        [169353773, 12345, 842810960, 160, datetime(2017, 3, 24, 4, 5, 4), 'TCP', 200, 100, 1, 1, 3],
        [169353773, 12345, 842811474, 216, datetime(2017, 3, 22, 2, 15, 27), 'TCP', 200, 100, 1, 1, 60],
        [169354287, 12345, 842810961, 248, datetime(2017, 3, 24, 1, 47, 25), 'TCP', 200, 100, 1, 4, 3],
        [169353773, 12345, 169354286, 160, datetime(2017, 3, 23, 10, 35, 7), 'TCP', 200, 100, 1, 4, 60],
        [169354287, 12345, 169354286, 184, datetime(2017, 3, 23, 4, 43, 55), 'TCP', 200, 100, 4, 1, 3],
        [843074132, 12345, 842810960, 232, datetime(2017, 3, 22, 18, 22, 12), 'TCP', 200, 100, 4, 1, 60],
        [842811475, 12345, 843074646, 384, datetime(2017, 3, 23, 4, 5, 10), 'TCP', 200, 500, 1, 1, 3],
        [843074646, 12345, 843074132, 256, datetime(2017, 3, 22, 8, 41, 44), 'TCP', 200, 500, 1, 1, 60],
        [169353772, 12345, 842810961, 280, datetime(2017, 3, 24, 2, 15, 41), 'TCP', 200, 500, 1, 4, 3],
        [843074647, 12345, 843074646, 168, datetime(2017, 3, 23, 7, 33, 56), 'TCP', 200, 500, 1, 4, 60],
        [169353772, 12345, 169353772, 160, datetime(2017, 3, 23, 7, 58, 30), 'TCP', 200, 500, 4, 1, 3],
        [169353772, 12345, 169091115, 320, datetime(2017, 3, 22, 22, 27, 38), 'TCP', 200, 500, 4, 1, 60],
        [169353772, 12345, 169091115, 360, datetime(2017, 3, 22, 6, 7), 'TCP', 200, 500, 4, 4, 60],
        [169091115, 12345, 842811474, 392, datetime(2017, 3, 21, 21, 39, 17), 'TCP', 500, 50, 1, 1, 3],
        [169091114, 12345, 843074132, 88, datetime(2017, 3, 22, 19, 29, 23), 'TCP', 500, 50, 1, 1, 60],
        [169354286, 12345, 169090601, 208, datetime(2017, 3, 22, 4, 23, 32), 'TCP', 500, 50, 1, 4, 3],
        [169091115, 12345, 169091114, 360, datetime(2017, 3, 24, 1, 43, 21), 'TCP', 500, 50, 1, 4, 60],
        [169090601, 12345, 843074133, 296, datetime(2017, 3, 22, 7, 28, 7), 'TCP', 500, 50, 4, 1, 3],
        [169354286, 12345, 994398041, 384, datetime(2017, 3, 21, 23, 9, 35), 'TCP', 500, 50, 4, 1, 60],
        [169353773, 12345, 843074132, 88, datetime(2017, 3, 21, 9, 39, 44), 'TCP', 500, 50, 4, 4, 3],
        [169353773, 12345, 169353772, 312, datetime(2017, 3, 23, 6, 32, 18), 'TCP', 500, 50, 4, 4, 60],
        [169090601, 12345, 843074647, 288, datetime(2017, 3, 21, 17, 44, 38), 'TCP', 500, 100, 1, 1, 60],
        [843074647, 12345, 842810960, 192, datetime(2017, 3, 22, 22, 35, 22), 'TCP', 500, 100, 1, 4, 60],
        [843074647, 12345, 169091114, 296, datetime(2017, 3, 23, 15, 16, 17), 'TCP', 500, 100, 4, 1, 3],
        [994398041, 12345, 169091115, 96, datetime(2017, 3, 23, 23, 52, 54), 'TCP', 500, 100, 4, 1, 60],
        [169091115, 12345, 842811475, 280, datetime(2017, 3, 23, 2, 10, 23), 'TCP', 500, 100, 4, 4, 60],
        [994398041, 12345, 169091114, 264, datetime(2017, 3, 21, 23, 40, 18), 'TCP', 500, 500, 1, 1, 3],
        [843074132, 12345, 842811474, 336, datetime(2017, 3, 23, 7, 3, 8), 'TCP', 500, 500, 1, 1, 60],
        [843074133, 12345, 842811474, 288, datetime(2017, 3, 22, 5, 44, 10), 'TCP', 500, 500, 1, 4, 3],
        [843074647, 12345, 169354287, 96, datetime(2017, 3, 23, 19, 51, 22), 'TCP', 500, 500, 1, 4, 60],
        [843074133, 12345, 842811475, 336, datetime(2017, 3, 23, 18, 33, 13), 'TCP', 500, 500, 4, 1, 3],
        [842810961, 12345, 843074132, 304, datetime(2017, 3, 23, 2, 52, 44), 'TCP', 500, 500, 4, 1, 60],
        [843074647, 12345, 169354286, 280, datetime(2017, 3, 21, 17, 33, 40), 'TCP', 500, 500, 4, 4, 3],
        [843074647, 12345, 169091115, 192, datetime(2017, 3, 22, 10, 0, 1), 'TCP', 500, 500, 4, 4, 60],
        [169354287, 12345, 842810960, 320, datetime(2017, 3, 21, 11, 39, 6), 'TCP', 1000, 50, 1, 1, 3],
        [842810960, 12345, 994398041, 392, datetime(2017, 3, 23, 3, 29, 7), 'TCP', 1000, 50, 1, 1, 60],
        [843074132, 12345, 169354287, 272, datetime(2017, 3, 23, 12, 34, 49), 'TCP', 1000, 50, 1, 4, 3],
        [843074133, 12345, 169091115, 168, datetime(2017, 3, 22, 19, 40, 46), 'TCP', 1000, 50, 1, 4, 60],
        [169091115, 12345, 994398041, 352, datetime(2017, 3, 22, 22, 58, 41), 'TCP', 1000, 50, 4, 1, 3],
        [169354286, 12345, 842810961, 160, datetime(2017, 3, 22, 1, 32, 58), 'TCP', 1000, 50, 4, 1, 60],
        [169354286, 12345, 169354286, 280, datetime(2017, 3, 21, 14, 8, 26), 'TCP', 1000, 50, 4, 4, 3],
        [842811475, 12345, 169091115, 80, datetime(2017, 3, 24, 6, 17, 56), 'TCP', 1000, 50, 4, 4, 60],
        [169354287, 12345, 169091114, 328, datetime(2017, 3, 22, 1, 56, 15), 'TCP', 1000, 100, 1, 1, 60],
        [843074647, 12345, 843074133, 88, datetime(2017, 3, 22, 21, 46, 22), 'TCP', 1000, 100, 1, 4, 3],
        [843074647, 12345, 169354286, 96, datetime(2017, 3, 21, 19, 50, 14), 'TCP', 1000, 100, 1, 4, 60],
        [169090601, 12345, 994398041, 264, datetime(2017, 3, 24, 6, 31, 1), 'TCP', 1000, 100, 4, 1, 3],
        [169091115, 12345, 169091115, 272, datetime(2017, 3, 22, 16, 16, 28), 'TCP', 1000, 100, 4, 4, 60],
        [169091115, 12345, 843074647, 192, datetime(2017, 3, 24, 6, 43, 58), 'TCP', 1000, 500, 1, 1, 3],
        [842811474, 12345, 842811475, 208, datetime(2017, 3, 21, 13, 58, 6), 'TCP', 1000, 500, 1, 1, 60],
        [843074646, 12345, 169354287, 344, datetime(2017, 3, 23, 18, 16, 39), 'TCP', 1000, 500, 1, 4, 60],
        [169354287, 12345, 842810960, 152, datetime(2017, 3, 22, 1, 28, 53), 'TCP', 1000, 500, 4, 1, 3],
        [843074646, 12345, 843074133, 320, datetime(2017, 3, 22, 11, 37, 14), 'TCP', 1000, 500, 4, 1, 60],
        [842810961, 12345, 843074647, 120, datetime(2017, 3, 22, 15, 52, 3), 'TCP', 1000, 500, 4, 4, 3],
        [843074133, 12345, 843074647, 384, datetime(2017, 3, 21, 22, 56, 27), 'TCP', 1000, 500, 4, 4, 60]
    ]

    rows = [dict(zip(loader.keys, entry)) for entry in log_lines]
    count = len(rows)
    loader.insert_data(rows, count)
    processor.run_all()


def setup_node_extras():
    sub_id = constants.demo['id']
    commands = template_sql("./sql/test_data.sql", sub_id)
    for command in commands:
        print command


# immediately run, to ensure the test db is present.
db = get_test_db_connection()
default_sub = constants.demo['id']
ds_model = models.datasources.Datasources({}, default_sub)
dsid_default = 0
dsid_short = 0
dsid_live = 0
for k, v in ds_model.datasources.iteritems():
    if v['name'] == 'default':
        dsid_default = k
    if v['name'] == 'short':
        dsid_short = k
    if v['name'] == 'live':
        dsid_live = k
clear_network(db, default_sub, dsid_default)
setup_network(db, default_sub, dsid_default)
