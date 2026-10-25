'''
刀刀的猫猫
Made by Wolf
http://www.wolfchen.top
https://github.com/WolfChen1996/DesktopPet
'''
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from PIL import Image
import random
import sys
import os
import io
import json
import time
import configparser
import urllib.request
from setting import Ui_MainWindow

# pythonw 无控制台时 stdout 为 None，print 会崩，这里兜底
if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

# 单实例保护：已经有桌宠在跑时，本次启动直接退出（避免出现两只猫）
import ctypes
_ct = ctypes.windll.kernel32
_ct.CreateMutexW(None, False, 'DesktopPet_SingleInstance_Meow')
if _ct.GetLastError() == 183:   # ERROR_ALREADY_EXISTS
    print('DesktopPet already running, exit.')
    sys.exit(0)

#初始化配置，并定义全局变量
#fp_dir=os.getcwd()
fp_dir=os.path.dirname(os.path.abspath(__file__))
print(fp_dir+'/config.ini')
config = configparser.ConfigParser()
configpath=fp_dir+'/config.ini'
config.read(configpath, encoding="utf-8-sig")
petidraw=config.get("config", "petids")
petids=petidraw.split(',')
petid=config.get("config", "petid")
traypath=config.get("config", "traypath")

# 自动发现 data 目录下所有宠物包：就算配置文件被写回旧版也不会丢形象
try:
    for _d in sorted(os.listdir(fp_dir+'/data')):
        if _d not in petids and os.path.isfile(fp_dir+'/data/'+_d+'/petconfig.ini'):
            petids.append(_d)
    petidraw=','.join(petids)
except Exception as e:
    print('pet scan failed:', e)

#print(fp_dir+"/"+petid+"/petconfig.ini")
petconfig = configparser.ConfigParser()
petconfigpath=fp_dir+"/data/"+petid+"/petconfig.ini"
petconfig.read(petconfigpath, encoding="utf-8-sig")
petname=petconfig.get("config", "petname")
petscale=petconfig.getfloat("config", "petscale")
bottomfix=petconfig.getfloat("config", "bottomfix")
gamespeed=petconfig.getfloat("config", "gamespeed")
petspeed=petconfig.getfloat("config", "petspeed")
throwout=petconfig.get("config", "throwout")
intotray=petconfig.get("config", "intotray")
mirror=petconfig.get("config", "intotray")
dropspeed=petconfig.getfloat("config", "dropspeed")
gravity=petconfig.getfloat("config", "gravity")
dragingfixx=petconfig.getfloat("config", "dragingfixx")
dragingfixy=petconfig.getfloat("config", "dragingfixy")
fixdragspeedx=petconfig.getfloat("config", "dragspeedx")
fixdragspeedy=petconfig.getfloat("config", "dragspeedy")

petactionsraw=petconfig.get("config", "petaction")
petactionnumraw=petconfig.get("config", "petactionnum")
petactionrateraw=petconfig.get("config", "petactionrate")
standactionraw=petconfig.get("config", "standaction")
standactionnumraw=petconfig.get("config", "standactionnum")
standactionrateraw=petconfig.get("config", "standactionrate")

petactions=petactionsraw.split(',')
petactionnum=petactionnumraw.split(',')
petactionrate=petactionrateraw.split(',')
standaction=standactionraw.split(',')
standactionnum=standactionnumraw.split(',')
standactionrate=standactionrateraw.split(',')

image_url = fp_dir+'/data/'+ petid +'/'
image = image_url + 'main.png'
im = Image.open(image)
petwidth=int(im.size[0]*petscale)
petheight=int(im.size[1]*petscale)
bottomfix=bottomfix*petscale
screenwidth,screenheight=0,0
deskwidth,deskheight=0,0
deskbottom=0
onfloor=1
drop=1
dropa=0
draging=0
gametick=0
standtick=0
playid=1
playtime=0
playnum=1
playstand=-1
petaction,petaction2=0,0
mouseposx1,mouseposx2,mouseposx3,mouseposx4,mouseposx5=0,0,0,0,0
mouseposy1,mouseposy2,mouseposy3,mouseposy4,mouseposy5=0,0,0,0,0
dragspeedx,dragspeedy=0,0
petleft,pettop=0,0
gameleft,gamebottom=0,0
imgpath='main.png'
forced=None   # 强制动作：{'frames':[...], 'i':当前帧号, 'left':剩余帧数}，用于喂食/摸头互动
walk_cd=0     # 走路中途小插曲（转圈圈/洗脸）的冷却计时
force_walk=None  # 右键点"走路"时，下一次选动作强制用这个方向值
dropbounces=0   # 本次掉落已反弹次数（三下递减后落定）

# ============ 问候与对话（新增） ============
catcfgpath = fp_dir + '/catcfg.json'
catcfg = {"name": "小猫咪", "base_url": "", "api_key": "", "model": ""}
if os.path.exists(catcfgpath):
    try:
        with open(catcfgpath, encoding='utf-8') as f:
            catcfg.update(json.load(f))
    except Exception as e:
        print('catcfg load failed:', e)

# 按时段的问候语（lo, hi, 语录），跨零点的时间段也能命中
greet_pools = [
    (5, 10, ['早上好呀~新的一天也要元气满满喵！', '（伸懒腰）早安，铲屎官！', '起床啦？我的早饭呢喵？']),
    (11, 13, ['该吃午饭啦，别忘了我也想吃小鱼干~', '（盯着你的饭盒）分我一口喵？']),
    (14, 17, ['好困呀...陪我玩一会儿喵？', '记得多喝水哦，我盯着你呢！', '（趴着装睡，其实在看）']),
    (18, 22, ['晚上好呀~今天辛苦啦，摸摸我放松一下喵', '（蹭蹭你的腿）今天也要开心哦喵']),
    (23, 4, ['这么晚还不睡？我先睡啦，晚安喵~', '呼噜呼噜...（已经睡着了）']),
]
idle_says = ['喵~', '（蹭你的手）', '（歪头看你）', '陪我玩！陪我玩！', '（舔毛中，勿扰）', '喵呜~~']
feed_says = ['啊呜啊呜~谢谢投喂！', '小鱼干！！最爱你了喵！', '（埋头狂吃）嗯嗯嗯~']
pat_says = ['呼噜呼噜~再摸一下嘛', '（眯眼睛享受）喵~', '（用头顶你的手）好舒服喵']

chat_rules = [
    (['名字', '叫什么'], ['我叫' + catcfg['name'] + '，是这台电脑的猫主人喵！']),
    (['你好', '在吗', 'hi', 'hello'], ['喵~我在呢！', '（抬起头看你）怎么了呀？']),
    (['饿', '吃', '小鱼干'], ['想吃小鱼干！想吃小鱼干！', '（闻闻空气）有好吃的吗喵？']),
    (['摸', 'rua', '揉'], ['快来摸摸我的头，就在屏幕上喵~']),
    (['睡', '困'], ['（打哈欠）陪我看会儿星星再睡喵~']),
    (['爱', '喜欢', '想你'], ['我也爱你喵！（用尾巴缠住你）', '哼，这还差不多喵~']),
    (['晚安', '早安', '早上好'], ['晚安，做个有红烧肉的好梦喵~']),
    (['喵'], ['喵喵喵！', '（认真地回你）喵~']),
]
chat_default = ['喵？（歪头，好像没听懂）', '（假装没听见，继续舔毛）', '喵呜？再说一遍喵？', '（尾巴拍了拍桌面）嗯，有道理喵']


def llm_reply(text):
    '''catcfg.json 里配了大模型接口就用它回答，失败返回 None'''
    if not catcfg.get('base_url') or not catcfg.get('api_key'):
        return None
    try:
        url = catcfg['base_url'].rstrip('/') + '/chat/completions'
        body = json.dumps({
            'model': catcfg.get('model', ''),
            'messages': [
                {'role': 'system', 'content': '你是' + catcfg['name'] + '，一只有点傲娇但很粘人的银色虎斑加白猫咪，住在主人的电脑桌面上。用不超过40字的可爱短句回复，结尾可以带"喵"。'},
                {'role': 'user', 'content': text},
            ],
        }).encode('utf-8')
        req = urllib.request.Request(url, data=body, headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + catcfg['api_key']})
        res = urllib.request.urlopen(req, timeout=10)
        data = json.loads(res.read().decode('utf-8'))
        return data['choices'][0]['message']['content'].strip()
    except Exception as e:
        print('llm failed:', e)
        return None


def chat_reply(text):
    '''先走本地猫语录，没匹配上再尝试大模型'''
    low = text.strip().lower()
    for keys, reps in chat_rules:
        for k in keys:
            if k in low:
                return random.choice(reps)
    r = llm_reply(text)
    if r:
        return r
    return random.choice(chat_default)


def hour_in(h, lo, hi):
    return lo <= h <= hi or (lo > hi and (h >= lo or h <= hi))


class Bubble(QLabel):
    '''宠物头顶的对话气泡。cat=True 是猫咪说的话（带头像），False 是主人说的话'''

    def __init__(self, is_cat=True):
        super().__init__()
        self.is_cat = is_cat
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        if is_cat:
            bg, border = 'rgba(255,255,255,245)', '#f5a8b8'
        else:
            bg, border = 'rgba(235,245,255,245)', '#8fb8e8'
        self.setStyleSheet(
            "background:%s;border:2px solid %s;border-radius:12px;padding:10px 16px;"
            "color:#4a3f3f;font-family:'Microsoft YaHei';font-size:18px;" % (bg, border))
        self.setWordWrap(True)
        self.setMaximumWidth(560)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.hide)

    def _pos(self, side):
        self.adjustSize()
        x = int(petleft + petwidth / 2 - self.width() / 2)
        if side == 'right':
            x = int(min(deskwidth - self.width() - 4, petleft + petwidth + 10))
            if x < gameleft + 4:
                x = int(max(gameleft + 4, petleft - self.width() - 10))
        y = int(max(0, pettop - self.height() - 12))
        return x, y

    def show_text(self, html, ms=6000, side='center'):
        self.setText(html)
        self.setTextFormat(Qt.RichText)
        x, y = self._pos(side)
        self.move(x, y)
        self.show()
        self.raise_()
        self.timer.start(ms)

    def say(self, text, ms=5000):
        #猫咪的话：头像 + 名字前缀，一眼认出是谁在说
        text = text.replace('<', '&lt;').replace('>', '&gt;')
        avatar = (fp_dir + '/data/tray.png').replace('\\', '/')
        html = ('<table><tr><td><img src="%s" width="36" height="36"></td>'
                '<td style="padding-left:8px;vertical-align:middle">'
                '<b style="color:#e0698a">%s：</b>%s</td></tr></table>'
                % (avatar, catcfg['name'], text))
        self.show_text(html, ms)


class ChatBox(QWidget):
    '''双击宠物弹出的聊天输入框'''
    def __init__(self, app):
        super().__init__()
        self.app = app
        # 注意不能用 Qt.Popup：弹窗类窗口拿不到键盘焦点，中文输入法打不了字
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.edit = QLineEdit(self)
        self.edit.setPlaceholderText('和' + catcfg['name'] + '说点什么，回车发送')
        self.edit.setStyleSheet("background:rgba(255,255,255,245);border:2px solid #f5a8b8;border-radius:14px;padding:10px 14px;color:#5a4a4a;font-family:'Microsoft YaHei';font-size:18px;min-width:300px;")
        self.edit.returnPressed.connect(self.send)
        self.edit.installEventFilter(self)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.edit)

    def eventFilter(self, obj, event):
        # 失去焦点自动收起（点别处即关闭）；Esc 也能关闭
        if obj is self.edit:
            if event.type() == QEvent.FocusOut:
                self.close()
            elif event.type() == QEvent.KeyPress and event.key() == Qt.Key_Escape:
                self.close()
        return super().eventFilter(obj, event)

    def open(self):
        self.move(int(petleft + petwidth / 2 - 140), int(max(0, pettop - 60)))
        self.show()
        self.raise_()
        self.activateWindow()
        self.edit.setFocus()

    def send(self):
        text = self.edit.text().strip()
        if not text:
            return
        self.close()
        # 双气泡对话：主人蓝色气泡在右上，猫咪回复带头像在头顶
        self.app.bubble.hide()
        self.app.ububble.show_text('<b style="color:#4a7fc1">我：</b>' +
                                   text.replace('<', '&lt;').replace('>', '&gt;'),
                                   6000, side='right')
        reply = chat_reply(text)
        QTimer.singleShot(900, lambda: self.app.bubble.say(reply, 8000))



class App(QWidget):
    def __init__(self, parent=None, **kwargs):
        super(App, self).__init__(parent)
        # initialize
        self.is_follow_mouse = False
        
        ### MAC用户看这里！！！For mac user!!!###
        # Mac用户可以把下面那行的#挪到windows那行，就可以看到猫了
        # Mac user can move the # from bottom line to the second line and you will see your pet.
        
        # Windows
        self.setWindowFlags(Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.SubWindow)
        # Mac
        #self.setWindowFlags(Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint)
        
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        #self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        
        self.repaint()
        
        screen = QDesktopWidget().screenGeometry()
        desktop = QDesktopWidget().availableGeometry()
        self.tray()
        
        #修正开始菜单在左侧时拖动的定位
        global screenwidth,screenheight,deskwidth,deskheight,petleft,pettop
        screenwidth=screen.width()
        screenheight=screen.height()
        deskwidth=desktop.width()
        deskheight=desktop.height()
        gameleft=screenwidth-deskwidth
        gamebottom=deskheight-screenheight
        #self.setGeometry(0, 0, screen.width(), screen.height())
        #print("初始化宠物")
        #print('屏幕尺寸' ,screenwidth , '-' , screenheight)
        #print('桌面尺寸' ,deskwidth, '-' , deskheight)
        #print('宠物尺寸' ,petwidth , '-' , petheight)
        if intotray!="True":
            petleft = deskwidth-petwidth
            pettop = deskheight-petheight+bottomfix
        else:
            gameleft=0
            gamebottom=0
            petleft = screenwidth-petwidth
            pettop = screenheight-petheight+bottomfix

        # initial image
        petimage = image_url + 'start.png'
        #print(petimage)
        pix = QPixmap(petimage)
        pix = pix.scaled(petwidth, petheight, aspectRatioMode=Qt.KeepAspectRatio)
        self.lb1 = QLabel(self)
        self.lb1.setPixmap(pix)
        self.lb1.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lb1.customContextMenuRequested.connect(self.rightMenu)

        # display
        #print("BeginDisplay",pettop)
        petleft = int(petleft)
        pettop = int(pettop)
        self.move(int(petleft), int(pettop))
        self.resize(petwidth, petheight)
        self.show()

        self.timer = QTimer()
        self.timer.timeout.connect(self.game)
        self.timer.start(int(gamespeed))

        # 气泡、定时问候、聊天框（新增）
        self.bubble = Bubble()
        self.ububble = Bubble(is_cat=False)   # 主人说话的气泡
        self.chatbox = ChatBox(self)
        self.greet_timer = QTimer()
        self.greet_timer.timeout.connect(self.autogreet)
        self.greet_timer.start(8 * 60 * 1000)  # 每隔几分钟到十几分钟问候一次
        QTimer.singleShot(2500, self.autogreet)  # 启动后先打个招呼

    def autogreet(self):
        if not self.isVisible() or self.bubble.isVisible():
            return
        h = time.localtime().tm_hour
        pool = idle_says
        for lo, hi, says in greet_pools:
            if hour_in(h, lo, hi):
                pool = says
                break
        self.bubble.say(random.choice(pool))

    V2COUNTS = {'sleep': 60, 'yawn': 32, 'lie': 20, 'lick': 32, 'roll': 32,
                'run': 32, 'stretch': 32, 'spin': 32}
    V2SAYS = {'sleep': 'Zzz……', 'yawn': '哈——好困喵', 'lie': '（瘫成一滩）',
              'lick': '洗把脸~', 'roll': '咕噜咕噜~', 'run': '冲鸭！！',
              'stretch': '（伸个懒腰）', 'spin': '转圈圈~'}
    FEEDSAY = {'eatbowl': '啊呜啊呜~猫粮最香了！', 'eatcan': '罐头！！开饭啦喵~',
               'eattreat': '小鱼干！！最爱你了喵！'}

    def do_action(self, pre):
        #右键指定动作：完整播一遍对应视频序列（每帧 3 tick，放慢到接近真实速度）
        n = self.V2COUNTS[pre]
        mult = 3
        frames = []
        for i in range(1, n + 1):
            frames += [pre + str(i)] * mult
        self.force_action(frames, n * mult)
        self.bubble.say(self.V2SAYS[pre])

    def do_feed(self, pre):
        # 每帧停留 3 tick(60ms)，放慢到接近真实速度
        self.force_action([pre + str(i) for i in range(1, 33) for _ in range(3)], 96)
        self.bubble.say(self.FEEDSAY[pre])

    def do_walk(self):
        global force_walk, forced
        forced = None
        force_walk = random.choice([0.93, 0.97])   # 0.93=向左区间, 0.97=向右区间
        self.bubble.say(random.choice(['出去溜达一圈喵~', '（迈着小碎步）', '散步中，勿扰~']))

    def force_action(self, frames, ticks, keep=False):
        global forced
        forced = {'frames': frames, 'i': 0, 'left': ticks, 'keep': keep}

    def maybe_interlude(self):
        #走路途中小概率停下：转个圈圈或洗把脸，然后原地继续走
        global walk_cd
        if walk_cd>0:
            walk_cd=walk_cd-1
            return
        if random.random()<0.006:
            self.force_action(random.choice([
                ['spin%d' % i for i in range(1, 33) for _ in range(3)],
                ['lickf%d' % i for i in range(1, 33) for _ in range(3)],
            ]), 96, keep=True)
            walk_cd=random.randint(80,200)

    def pat(self):
        # 每帧停留 3 tick(60ms)，放慢到接近真实速度
        self.force_action(['lickf%d' % i for i in range(1, 33) for _ in range(3)], 96)
        self.bubble.say(random.choice(pat_says))

    def feed(self):
        self.do_feed(random.choice(['eatbowl', 'eatcan', 'eattreat']))

    def mouseDoubleClickEvent(self, event):
        self.chatbox.open()
    
    def game(self):
        # 主循环加保护：任何一步出错只跳过这一帧，不让 PyQt 直接把整个进程崩掉
        try:
            return self._game()
        except Exception:
            # 异常细节写入 debug.log（pythonw 下 print 看不见）
            import traceback
            try:
                with open(fp_dir + '/../debug.log', 'a', encoding='utf-8') as lf:
                    lf.write(time.strftime('%H:%M:%S') + ' GAME-ERROR:\n' + traceback.format_exc() + '\n')
            except Exception:
                pass
            traceback.print_exc()

    def _game(self):
        #循环执行主函数
        global petwidth,playid,playtime,petaction,petaction2,playstand,playnum,petleft,pettop,imgpath,forced,walk_cd,force_walk,onfloor,dropa,standtick
        # 注意：onfloor/dropa 在下面的兜底里有赋值，必须声明 global，否则整个循环每帧 UnboundLocalError
        # 状态采样：每 50 tick(约1秒) 把全部状态写入 debug.log，用于诊断悬空等问题
        global gametick
        gametick=gametick+1
        if gametick%50==0:
            try:
                with open(fp_dir + '/../debug.log', 'a', encoding='utf-8') as lf:
                    lf.write('%s state: draging=%s onfloor=%s drop=%s forced=%s follow=%s petleft=%s pettop=%s img=%s btn=%s\n'
                             % (time.strftime('%H:%M:%S'), draging, onfloor, drop,
                                'None' if forced is None else forced['left'],
                                self.is_follow_mouse, int(petleft), int(pettop),
                                imgpath, int(QApplication.mouseButtons())))
            except Exception:
                pass
        # 防呆：处于拖拽状态但鼠标左键其实已松开（release 事件偶发丢失）→ 自动补一次松手
        if draging==1 and self.is_follow_mouse and (QApplication.mouseButtons() & Qt.LeftButton)==0:
            self.release_cat()
        # 物理兜底：不在拖拽/下落/强制动作中时，猫必须站在桌面底线上（防任何状态异常导致悬空）
        if forced is None and draging==0:
            floor_y=deskheight-petheight+gamebottom
            if (onfloor==1 and abs(pettop-floor_y)>2) or (onfloor==0 and drop==0):
                try:
                    with open(fp_dir+'/../debug.log','a',encoding='utf-8') as lf:
                        lf.write('%s snap-down: onfloor=%s drop=%s draging=%s pettop=%s floor=%s\n'
                                 % (time.strftime('%H:%M:%S'), onfloor, drop, draging, int(pettop), int(floor_y)))
                except Exception:
                    pass
                pettop=floor_y
                onfloor=1
                dropa=0
                self.move(int(petleft), int(pettop))
        #强制动作（喂食/摸头）：独占显示；被拎起或掉落会打断
        if forced is not None:
            if draging==1 or onfloor==0:
                forced=None
            else:
                imgpath=forced['frames'][forced['i']%len(forced['frames'])]
                forced['i']=forced['i']+1
                forced['left']=forced['left']-1
                if forced['left']<=0:
                    keep=forced.get('keep', False)
                    forced=None
                    if not keep:
                        playtime=0   # 喂食/摸头结束回待机重选；走路中途的小插曲则原地继续走
                pix = QPixmap(image_url + imgpath + '.png')
                pix = pix.scaled(petwidth, petheight, aspectRatioMode=Qt.KeepAspectRatio)
                self.lb1.setPixmap(pix)
                return
        ##print("loop:"+str(petaction))
        #print("Loop")
        right=0
        if drop==1 and onfloor==0:
            if draging==1:
                #print("Draging")
                playnum=int(petactionnum[3])
                if playid<int(petactionnum[3]):
                        imgpath=petactions[3]+str(playid)+'.png'
                        playid=playid+1
                else:
                    imgpath=petactions[3]+str(playid)+'.png'
                    playid=1
                
            elif draging==0:
                ##print("Falling")
                playnum=int(petactionnum[4])
                imgpath=petactions[4]+str(playid)+'.png'
                if gametick%2==0:   # 翻滚动画 2 tick/帧，更顺滑
                    if playid<int(petactionnum[4]):
                        playid=playid+1
                    else:
                        playid=1
                
            self.drop()

        if drop==0 or onfloor==1:
            
            if playtime==0:
                if force_walk is not None:
                    petaction=force_walk
                    force_walk=None
                else:
                    petaction=random.random()
                playstand=-1
                playid=1
            #print(petaction)
            #print(float(petactionrate[0])+float(petactionrate[1]))
            if petaction>=(float(petactionrate[0])+float(petactionrate[1])) and (petleft+petwidth+gameleft+petspeed)<deskwidth:
                ##print("Walking right")
                right=1
                self.maybe_interlude()
                playnum=int(petactionnum[2])
                if playid<int(petactionnum[2]):
                    imgpath=petactions[2]+str(playid)+'.png'
                    playid=playid+1
                    
                else:
                    imgpath=petactions[2]+str(playid)+'.png'
                    playid=1
                
                
                petleft=petleft+petspeed
                
                self.move(int(petleft), int(pettop))

                if playtime==0:
                    playtimemin=3
                    playtimemax=int((((deskwidth-(petleft+petwidth+gameleft)))/petspeed)/playnum)
                    if playtimemax<=3:
                        playtimemax=3
                    playtimemax=min(playtimemax, random.randint(1,3))   # 走走停停：单次走0.6~2秒
                playtime=int(playtime)-1
                #print("Right:"+str(petaction)+"."+str(playid)+"."+str(playtime))

            elif petaction<(float(petactionrate[0])+float(petactionrate[1])) and petaction>=float(petactionrate[0]) and (petleft-gameleft)>petspeed:
                right=-1
                self.maybe_interlude()
                playnum=int(petactionnum[1])
                if playid<int(petactionnum[1]):
                    imgpath=petactions[1]+str(playid)+'.png'
                    playid=playid+1
                    
                else:
                    imgpath=petactions[1]+str(playid)+'.png'
                    playid=1

                petleft=petleft-petspeed
                self.move(int(petleft), int(pettop))
                
                if playtime==0:
                    playtimemin=3
                    playtimemax=int((petleft-gameleft)/petspeed/playnum)
                    if playtimemax<=1:
                        playtimemax=1
                    playtimemax=min(playtimemax, random.randint(1,3))   # 走走停停：单次走0.6~2秒
                playtime=int(playtime)-1
                #print("Left:"+str(petaction)+"."+str(playid)+"."+str(playtime)+"playtimemax:"+str(petspeed))
                
            elif petaction<float(petactionrate[0]):
                #print("站立循环")

                if playstand==-1:
                    temp=random.random()
                    temp2=0
                    #print(temp)
                    for i in range(len(standactionrate)):
                        
                        if float(standactionrate[i])==0:
                            continue
                        temp2=temp2+float(standactionrate[i])
                        ##print("内循环："+str(i)+"累计概率："+str(temp2))
                        if temp<temp2:
                            petaction2=i
                            playnum=int(standactionnum[i])
                            playstand=1
                            ##print("GET!")
                            ##print(str(i)+":"+str(temp2))
                            break
                            
                            #playstand=random.randint(0,len(standaction))
                    if playstand==-1:
                        playnum=int(standactionnum[0])
                        playstand=1
                
                ##print("Playstand:"+str(playstand)+"Num:"+standactionnum[petaction2])
                # 待机小动作放慢：每帧停 3 tick(60ms)，视频动作和呼吸循环都接近真实速度
                standtick=standtick+1
                if standtick<3:
                    imgpath=standaction[petaction2]+str(playstand)+'.png'
                elif playstand<int(standactionnum[petaction2]):
                    standtick=0
                    imgpath=standaction[petaction2]+str(playstand)+'.png'
                    playstand=playstand+1
                else:
                    standtick=0
                    imgpath=standaction[petaction2]+str(playstand)+'.png'
                    playstand=1
                    playid=1
                
                if playtime==0:
                    playtimemin=1
                    playtimemax=3   # 慢放后每帧3tick：时长随机1~3个完整循环，动画不会被掐断
                    
                playtime=int(playtime)-1
                ##print("Stand:"+str(petaction)+".Playid:"+str(playid)+"."+str(petaction2)+".Playstand:"+str(playstand)+".Playtime:"+str(playtime)+"Playnum:"+str(playnum))
                
                
                
            else:
                petaction=random.random()
                playstand=-1
            
            if playtime==-1:
                playtime=random.randint(1,playtimemax)*playnum
                
                
        petimage = image_url + imgpath
        #petimage=petimage.mirrored(True, False)
        pix = QPixmap(petimage)
        if right==-1:
            # 素材里的猫默认朝右；向左走时镜像，让头朝着前进方向
            tempimg = pix.toImage()
            tempimg = tempimg.mirrored(True, False)
            pix=QPixmap.fromImage(tempimg)
            
        pix=pix.scaled(petwidth, petheight, aspectRatioMode=Qt.KeepAspectRatio)
        self.lb1.setPixmap(pix)
        pass
    
    def rightMenu(self):
        try:
            with open(fp_dir + '/../debug.log', 'a', encoding='utf-8') as lf:
                lf.write('%s rightmenu: draging=%s onfloor=%s drop=%s pettop=%s\n'
                         % (time.strftime('%H:%M:%S'), draging, onfloor, drop, int(pettop)))
        except Exception:
            pass
        menu = QMenu(self)
        menu.addAction(QAction(QIcon('./data/icon/deviceon.png'), '开启掉落', self, triggered=self.dropon))
        menu.addAction(QAction(QIcon('./data/icon/deviceoff.png'), '禁用掉落', self, triggered=self.dropoff))
        menu.addSeparator()
        menu.addAction(QAction(QIcon('./data/icon/collection.png'), '摸摸头', self, triggered=self.pat))
        feedm = menu.addMenu('喂小鱼干')
        feedm.addAction(QAction('吃猫粮', self, triggered=lambda _: self.do_feed('eatbowl')))
        feedm.addAction(QAction('吃罐头', self, triggered=lambda _: self.do_feed('eatcan')))
        feedm.addAction(QAction('吃冻干', self, triggered=lambda _: self.do_feed('eattreat')))
        feedm.addAction(QAction('随便来一口', self, triggered=self.feed))
        actm = menu.addMenu('做动作')
        acts = [('走路', None), ('睡觉', 'sleep'), ('打哈欠', 'yawn'), ('躺平', 'lie'),
                ('洗脸', 'lick'), ('打滚', 'roll'), ('兴奋跑', 'run'),
                ('伸懒腰', 'stretch'), ('转圈圈', 'spin')]
        for label, pre in acts:
            if pre is None:
                actm.addAction(QAction(label, self, triggered=lambda _: self.do_walk()))
            else:
                actm.addAction(QAction(label, self, triggered=lambda _, p=pre: self.do_action(p)))
        menu.addAction(QAction(QIcon('./data/icon/collection.png'), '和它聊天', self, triggered=self.chatbox.open))
        menu.addSeparator()
        menu.addAction(QAction(QIcon('./data/icon/increase.png'), '放大', self, triggered=self.increase))
        menu.addAction(QAction(QIcon('./data/icon/decrease.png'), '缩小', self, triggered=self.decrease))
        menu.addAction(QAction(QIcon('./data/icon/eye_protection.png'), '隐藏', self, triggered=self.hide))
        menu.addAction(QAction(QIcon('./data/icon/settings.png'), '设置', self, triggered=self.setting))
        menu.addAction(QAction(QIcon('./data/icon/restore.png'), '重启', self, triggered=self.restart_program))
        menu.addAction(QAction(QIcon('./data/icon/close.png'), '退出', self, triggered=self.quit))
        menu.exec_(QCursor.pos())
        
    def mousePressEvent(self, event):
        if event.button()==Qt.LeftButton:
            self.is_follow_mouse = True
            global onfloor,draging,playid
            onfloor=0
            draging=1
            playid=1
            event.accept()
            self.setCursor(QCursor(Qt.OpenHandCursor))

    def mouseMoveEvent(self, event):
        global mouseposx1,mouseposx2,mouseposx3,mouseposx4,mouseposx5
        global mouseposy1,mouseposy2,mouseposy3,mouseposy4,mouseposy5
        global petleft,pettop
        if Qt.LeftButton and self.is_follow_mouse:
            petleft = QCursor.pos().x()-petwidth/2+dragingfixx*petscale
            pettop = QCursor.pos().y()-petheight/2+dragingfixy*petscale
            #mouseposx5=mouseposx4
            mouseposx4=mouseposx3
            mouseposx3=mouseposx2
            mouseposx2=mouseposx1
            mouseposx1=QCursor.pos().x()
            #mouseposy5=mouseposy4
            mouseposy4=mouseposy3
            mouseposy3=mouseposy2
            mouseposy2=mouseposy1
            mouseposy1=QCursor.pos().y()
            ##print("Moving")
            #print(petleft)
            #print(QCursor.pos().x() , '-' , petwidth/2 , '=' , petleft,'*')
            #print(QCursor.pos().y() , '-' , petheight/2, '=' , pettop)

            self.move(int(petleft), int(pettop))
            event.accept()

    def release_cat(self):
        #松手逻辑（mouseReleaseEvent 与防呆补发共用）
        global onfloor,dropa,draging,playid,dropbounces,drop,pettop
        global dragspeedx,dragspeedy,mouseposx1,mouseposx3,mouseposy1,mouseposy3
        playid=1
        draging=0
        dropbounces=0
        self.is_follow_mouse = False
        self.setCursor(QCursor(Qt.ArrowCursor))
        dropa=1
        dragspeedx=(mouseposx1-mouseposx3)/2*fixdragspeedx
        dragspeedy=(mouseposy1-mouseposy3)/2*fixdragspeedy
        mouseposx1=mouseposx3=0
        mouseposy1=mouseposy3=0
        if drop==0:
            # 掉落被禁用时，松手直接落到桌面底部，避免悬空走路
            onfloor=1
            dropa=0
            pettop=deskheight-petheight+gamebottom
            self.move(int(petleft), int(pettop))
        else:
            onfloor=0

    def mouseReleaseEvent(self, event):
        if event.button()==Qt.LeftButton:
            self.release_cat()

    def tray(self):
        tray = QSystemTrayIcon(self)
        tray.setIcon(QIcon(traypath))
        menu = QMenu(self)

        menu.addAction(QAction(petname, self))
        menu.addAction(QAction(QIcon('./data/icon/eye_protection.png'),'显示', self, triggered=self.show))
        menu.addAction(QAction(QIcon('./data/icon/visible.png'), '隐藏', self, triggered=self.hide))
        menu.addAction(QAction(QIcon('./data/icon/deviceon.png'), '开启掉落', self, triggered=self.dropon))
        menu.addAction(QAction(QIcon('./data/icon/deviceoff.png'), '禁用掉落', self, triggered=self.dropoff))
        menu.addAction(QAction("打 * 功能有bug", self))
        menupick=QMenu(menu)
        menupick.setTitle("*选择宠物")
        
        menu.addMenu(menupick)
        #newpetid='cat1'
        #menupick.addAction(QAction(QIcon('./data/icon/collection.png'), '0', self, triggered=lambda:self.pick('0')))

        for temp in petids:
            label=temp
            try:
                pc=configparser.ConfigParser()
                pc.read(fp_dir+'/data/'+temp+'/petconfig.ini', encoding='utf-8-sig')
                label=temp+' · '+pc.get("config", "petname")
            except Exception:
                pass
            if temp==petid:
                menupick.addAction(QAction(QIcon('./data/icon/collection.png'),label, self, triggered=self.wrapped_pick(temp)))
            else:
                menupick.addAction(QAction(label, self, triggered=self.wrapped_pick(temp)))

        menu.addSeparator()
        
        #menu.addAction(QAction(QIcon('./data/icon/increase.png'), '放大', self, triggered=self.increase))
        #menu.addAction(QAction(QIcon('./data/icon/decrease.png'), '缩小', self, triggered=self.decrease))
        menu.addAction(QAction(QIcon('./data/icon/settings.png'), '设置', self, triggered=self.setting))
        menu.addAction(QAction(QIcon('./data/icon/restore.png'), '重启', self, triggered=self.restart_program))
        menu.addAction(QAction(QIcon('./data/icon/close.png'), '退出', self, triggered=self.quit))
        
        tray.setContextMenu(menu)
        tray.show()
    '''
    def nextimg(self):
        image_url = './data/'+ petid +'/'
        petimage = image_url + 'stand1.png'
        self.img = QImage()
        self.img.load(petimage)
        print(petimage)
        self.image.setPixmap(QPixmap.fromImage(self.img))
    '''
    
    def wrapped_pick(self, id):
        def _(_):
            self.pick(id)
        return _
        
    def setting(self):
        #print("Setting")
        setting.show()
        
    def drop(self):
        #掉落物理：终端限速(下落顺滑不瞬移) + 三次递减反弹 + 落地压扁
        global petleft,pettop
        global onfloor,dropa,dragspeedy,dropbounces,dragspeedx
        if onfloor==0 and draging==0:
            dropnext=pettop+dragspeedy+dropspeed
            movenext=petleft+dragspeedx
            if throwout!="True":
                if movenext<=gameleft:
                    movenext=gameleft
                elif movenext>screenwidth-petwidth:
                    movenext=(screenwidth-petwidth)

            dragspeedy=min(dragspeedy+gravity, 15)   # 终端速度
            floor_y=deskheight-petheight+gamebottom
            if dropnext>=floor_y:
                dropbounces=dropbounces+1
                if dropbounces<=3 and dragspeedy>6:
                    # 反弹三下、一次比一次低(约50px/20px/8px)，然后落定回正常姿势
                    dragspeedy=(-21,-13,-8)[dropbounces-1]
                    dragspeedx=dragspeedx*0.55
                    pettop=floor_y
                    petleft=movenext
                    self.move(int(petleft), int(pettop))
                else:
                    pettop=floor_y
                    petleft=movenext
                    self.move(int(petleft), int(pettop))
                    onfloor=1
                    dropa=0
                    dropbounces=0
                    # 直接恢复正常姿势（不再播压扁帧）
            else:
                pettop=dropnext
                petleft=movenext
                self.move(int(petleft), int(pettop))
                

    def increase(self):
        global petscale,petwidth,petheight,bottomfix
        petscale=petscale*1.1
        petwidth=int(im.size[0]*petscale)
        petheight=int(im.size[1]*petscale)
        print(petwidth)
        bottomfix=bottomfix*petscale
        self.resize(petwidth, petheight)
        self.lb1.setGeometry(0,0,petwidth, petheight)
        #restart_program(self)
        
    def decrease(self):
        global petscale,petwidth,petheight,bottomfix
        petscale=petscale*0.9
        petwidth=int(im.size[0]*petscale)
        petheight=int(im.size[1]*petscale)
        bottomfix=bottomfix*petscale
        self.resize(petwidth, petheight)
        self.lb1.setGeometry(0,0,petwidth, petheight)
        #restart_program(self)

    
    def pick(self,newpetid):
        global petid
        petid=newpetid
        config.set("config", "petid", newpetid)   # 记住选择，重启后仍生效
        config.write(open(configpath, "w", encoding="utf-8-sig"))
        setting.loadpetconfig()
        
    def switchdrop(self):
        global drop
        sender = self.sender()
        if sender.text()=="禁用掉落":
            sender.setText("开启掉落")
            drop=0
        else:
            sender.setText("禁用掉落")
            drop=1     
            
    def dropon(self):
        global drop
        drop=1
        
    def dropoff(self):
        global drop
        drop=0
        
    def quit(self):
        self.close()
        sys.exit()

    def hide(self):
        self.setVisible(False)

    def show(self):
        self.setVisible(True)
        
    def restart_program(self):
        python = sys.executable
        os.execl(python, python, * sys.argv)
        
    def quit(self):
        self.close()
        sys.exit()
    
class setting(QMainWindow, Ui_MainWindow):
    _startPos = None
    _endPos = None
    _isTracking = False
    def __init__(self, parent=None):
        super(setting, self).__init__(parent)
        
        self.setWindowFlags(Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        #self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        
        self.setupUi(self)
        
    def mouseMoveEvent(self, e: QMouseEvent):  # 重写移动事件
        self._endPos = e.pos() - self._startPos
        self.move(self.pos() + self._endPos)

    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.LeftButton:
            self._isTracking = True
            self._startPos = QPoint(e.x(), e.y())

    def mouseReleaseEvent(self, e: QMouseEvent):
        if e.button() == Qt.LeftButton:
            self._isTracking = False
            self._startPos = None
            self._endPos = None
            
    
    def readcfg(self, MainWindow):
        self.settingpetid.setText(petid)
        self.settingpetlist.setPlainText(petidraw)
        self.settingtray.setText(traypath)

        self.settingpetname.setText(petname)
        self.settingscale.setText(str(petscale))
        self.settingbottomfix.setText(str(bottomfix))
        self.settingdragingfixx.setText(str(dragingfixx))
        self.settingdragingfixy.setText(str(dragingfixy))
        self.settingpetspeed.setText(str(petspeed))
        self.settinggamespeed.setText(str(gamespeed))
        self.settingspeedx.setText(str(fixdragspeedx))
        self.settingspeedy.setText(str(fixdragspeedy))
        self.settinggravity.setText(str(gravity))
        self.settingdropspeed.setText(str(dropspeed))
        self.settingpetaction.setText(petactionsraw)
        self.settingpetactionnum.setText(petactionnumraw)
        self.settingpetactionrate.setText(petactionrateraw)
        self.settingstandaction.setText(standactionraw)
        self.settingstandactionnum.setText(standactionnumraw)
        self.settingstandactionrate.setText(standactionrateraw)

        if throwout=="True":
            self.settingthrowout.setChecked(True)
        else:
            self.settingthrowout.setChecked(False)
        
        
        if intotray=="True":
            self.settingintotray.setChecked(True)
        else:
            self.settingintotray.setChecked(False)
        
        if intotray=="True":
            self.settingmirror.setChecked(True)
        else:
            self.settingmirror.setChecked(False)
        
    def savecfg1(self):
        config.set("config", "petid", self.settingpetid.text())  
        config.set("config", "petids", self.settingpetlist.toPlainText())  
        config.set("config", "traypath", self.settingtray.text())  
        config.write(open(configpath, "w", encoding="utf-8-sig"))
        
        self.loadconfig()
        self.readcfg(self)
        
    def savecfg2(self):
        petconfig.set("config", "petname", self.settingpetname.text())  
        petconfig.set("config", "petscale", self.settingscale.text())  
        petconfig.set("config", "bottomfix", self.settingbottomfix.text()) 
        petconfig.set("config", "dragingfixx", self.settingdragingfixx.text()) 
        petconfig.set("config", "dragingfixy", self.settingdragingfixy.text()) 
        petconfig.set("config", "petspeed", self.settingpetspeed.text()) 
        petconfig.set("config", "gamespeed", self.settinggamespeed.text()) 
        petconfig.set("config", "dragspeedx", self.settingspeedx.text()) 
        petconfig.set("config", "dragspeedy", self.settingspeedy.text()) 
        petconfig.set("config", "gravity", self.settinggravity.text()) 
        petconfig.set("config", "dropspeed", self.settingdropspeed.text()) 

        
        petconfig.set("config", "petaction", self.settingpetaction.text()) 
        petconfig.set("config", "petactionnum", self.settingpetactionnum.text()) 
        petconfig.set("config", "petactionrate", self.settingpetactionrate.text()) 
        petconfig.set("config", "standaction", self.settingstandaction.text()) 
        petconfig.set("config", "standactionnum", self.settingstandactionnum.text()) 
        petconfig.set("config", "standactionrate", self.settingstandactionrate.text()) 
        
        petconfig.set("config", "throwout", str(self.settingthrowout.isChecked()))
        petconfig.set("config", "intotray", str(self.settingintotray.isChecked()))
        petconfig.set("config", "mirror", str(self.settingmirror.isChecked()))
        petconfig.write(open(petconfigpath, "w", encoding="utf-8-sig"))
        
        self.loadpetconfig()
        self.readcfg(self)
    '''
        self.readcfg(MainWindow)
        self.save1.clicked.connect(MainWindow.savecfg1)
        self.save2.clicked.connect(MainWindow.savecfg2)
    '''
    def loadconfig(self):
        global configpath,petidraw,petids,petid,traypath
        #print(fp_dir+'/config.ini')
        config = configparser.ConfigParser()
        configpath=fp_dir+'/config.ini'
        config.read(configpath, encoding="utf-8-sig")
        petidraw=config.get("config", "petids")
        petids=petidraw.split(',')
        petid=config.get("config", "petid")
        traypath=config.get("config", "traypath")
        try:
            for _d in sorted(os.listdir(fp_dir+'/data')):
                if _d not in petids and os.path.isfile(fp_dir+'/data/'+_d+'/petconfig.ini'):
                    petids.append(_d)
            petidraw=','.join(petids)
        except Exception:
            pass
    
    def loadpetconfig(self):
        print("LoadPetconfig")
        global petconfig,petname,petscale,bottomfix,gamespeed,petspeed,gravity,dragingfixx,dragingfixy,fixdragspeedx,fixdragspeedy,petactionnum,petactionrate,standaction,standactionnum,standactionrate,image_url,image,im,petwidth,petheight,petactionsraw,petactionnumraw,petactionrateraw,standactionraw,standactionnumraw,standactionrateraw,throwout,intotray,mirror,dropspeed

        # 注意：这里用脚本所在目录（模块级 fp_dir），不用 getcwd，避免从别处启动时切换宠物失败
        petconfig = configparser.ConfigParser()
        petconfig.read(fp_dir+"/data/"+petid+"/petconfig.ini", encoding="utf-8-sig")

        #print(fp_dir+"/"+petid+"/petconfig.ini")
        petconfig = configparser.ConfigParser()
        petconfig.read(fp_dir+"/data/"+petid+"/petconfig.ini", encoding="utf-8-sig")
        petname=petconfig.get("config", "petname")
        petscale=petconfig.getfloat("config", "petscale")
        bottomfix=petconfig.getfloat("config", "bottomfix")
        gamespeed=petconfig.getfloat("config", "gamespeed")
        petspeed=petconfig.getfloat("config", "petspeed")
        throwout=petconfig.get("config", "throwout")
        intotray=petconfig.get("config", "intotray")
        mirror=petconfig.get("config", "intotray")
        gravity=petconfig.getfloat("config", "gravity")
        dropspeed=petconfig.getfloat("config", "dropspeed")
        dragingfixx=petconfig.getfloat("config", "dragingfixx")
        dragingfixy=petconfig.getfloat("config", "dragingfixy")
        fixdragspeedx=petconfig.getfloat("config", "dragspeedx")
        fixdragspeedy=petconfig.getfloat("config", "dragspeedy")
        petactionsraw=petconfig.get("config", "petaction")
        petactionnumraw=petconfig.get("config", "petactionnum")
        petactionrateraw=petconfig.get("config", "petactionrate")
        standactionraw=petconfig.get("config", "standaction")
        standactionnumraw=petconfig.get("config", "standactionnum")
        standactionrateraw=petconfig.get("config", "standactionrate")
        
        petactions=petactionsraw.split(',')
        petactionnum=petactionnumraw.split(',')
        petactionrate=petactionrateraw.split(',')
        standaction=standactionraw.split(',')
        standactionnum=standactionnumraw.split(',')
        standactionrate=standactionrateraw.split(',')
        bottomfix=bottomfix*petscale
        image_url = fp_dir+'/data/'+ petid +'/'
        image = image_url + 'main.png'
        im = Image.open(image)
        petwidth=int(im.size[0]*petscale)
        petheight=int(im.size[1]*petscale)
        bottomfix=bottomfix*petscale
    
if __name__ == '__main__':
    app = QApplication(sys.argv)
    pet = App()
    setting = setting()
    sys.exit(app.exec_())
