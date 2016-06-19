import eventlet
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template, request
from flask_socketio import SocketIO
import random
import requests
import subprocess
import re


eventlet.monkey_patch()

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'verysecret'


class Field(object):

    VID = 0

    def __init__(self, name, interval=10):
        self.name = name
        self.interval = interval
        Field.VID += 1
        self._vid = Field.VID

    @property
    def vid(self):
        return 'vid{}'.format(self._vid)

    @property
    def value(self):
        egg = random.randint(1, 10)
        if egg < 3:
            cl = 'label label-success'
        elif egg >7:
            cl = 'label label-danger'
        else:
            cl = 'label label-warning'
        return egg, cl

    @property
    def widget(self):
        return '''<div>{0}: <span id='{1}' class="label label-info">--</span></div>'''.format(self.name, self.vid)


class URLField(Field):

    def __init__(self, name, url="http://www.ru", tag="<title>WWW.RU</title>", interval=60):
        super().__init__(name, interval)
        self.tag = tag
        self.url = url

    @property
    def value(self):
        try:
            rc = requests.get(self.url)
            if self.tag in rc.text:
                return 'ok', 'label label-success'
            else:
                raise Exception
        except:
            return '--', 'label label-danger'


class SSHField(Field):

    def __init__(self, name, cmd=None, regex="(\d+%)", interval=60):
        super().__init__(name, interval)
        self.cmd = cmd
        self.regex = re.compile(regex)

    @property
    def value(self):
        try:
            rc = subprocess.getoutput(self.cmd)
            m = self.regex.findall(rc)
            if m:
                return m[0], 'label label-success'
            else:
                raise Exception
        except:
            return '--', 'label label-danger'


class Server1(object):

    rnd1 = Field('rnd1 val', 0.3)
    rnd2 = URLField('www.ru', url="http://www.ru", tag="<title>WWW.RU<1/title>", interval=10)

    class Meta:
        title = "Server 1"


class Server2(object):

    rnd1 = Field('rnd1 val', 0.3)
    rnd2 = SSHField('df holmes', cmd='ssh test@otherpc df /dev/sdb1', interval=10)
    rnd3 = Field('rnd3 val', 10)

    class Meta:
        title = "Server 2"


servers = [
    Server1,
    Server2
]


def update_job(field):
    egg = field.value
    socket_io.emit('update', {'vid': field.vid, 'value': egg[0], 'class': egg[1]})


socket_io = SocketIO(app)


@app.route('/')
def hello_world():
    s = []
    for el in servers:
        cur = {'title': el.Meta.title, 'widgets': []}
        s.append(cur)
        for name, obj in el.__dict__.items():
            if isinstance(obj, Field):
                cur['widgets'].append(obj.widget)
    return render_template("index.html", servers=s)


@socket_io.on('connect')
def test_connect():
    app.logger.debug('client connected %s', request.sid)


@socket_io.on('my event')
def handle_my_custom_event(json):
    app.logger.debug('received json: ' + str(json))
    socket_io.emit('sendmsg', {'data': '!'})


if __name__ == '__main__':
    sched = BackgroundScheduler()
    for server in servers:
        for name, obj in server.__dict__.items():
            if isinstance(obj, Field):
                sched.add_job(update_job, trigger='interval', args=(obj,), seconds=obj.interval)
    sched.start()
    socket_io.run(app, debug=True)
