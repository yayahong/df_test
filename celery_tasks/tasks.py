from django.conf import settings
from django.core.mail import send_mail
from django.template import loader, RequestContext
from celery import Celery
import time

# 在任务处理者一端加上一下4句:django环境的初始化设置
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "df_test.settings")
django.setup()

# 以下类的导入需写在django环境初始化的下方，
from goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner


# 创建Celery类的实例对象
app = Celery('celery_tasks.tasks', broker='redis://192.168.187.144:6379/2')
app.config_from_envvar('DJANGO_SETTINGS_MODULE')


# 定义任务函数
@app.task
def send_register_active_email(to_email, username, token):
    """发送激活邮件"""
    # 组织邮件信息
    subject = '天天生鲜会员注册激活'
    message = ''
    sender = settings.EMAIL_FROM
    receiver = [to_email]
    html_message = '<h1>%s,欢迎成为天天生鲜会员</h1>请点击以下链接完成注册激活:<br>' \
                   '<a href="http://192.168.187.144:8080/user/active/%s">' \
                   'http://192.168.187.144:8080/user/active/%s</a>' % (username, token, token)

    send_mail(subject, message, sender, receiver, html_message=html_message)
    time.sleep(5)


@app.task
def generate_static_index_html():
    """产生首页静态页面"""
    # 获取首页商品分类信息
    types = GoodsType.objects.all()

    # 获取首页轮播图商品信息
    goods_banners = IndexGoodsBanner.objects.all().order_by('index')

    # 获取首页足促销活动商品信息
    promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

    # 获取首页分类展示商品信息
    type_goods_banners_dict = {}
    type_goods_titles_dict = {}

    for type in types:
        type_goods_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type='1').order_by('index')
        type_goods_banners_dict[type] = type_goods_banners

        type_goods_titles = IndexTypeGoodsBanner.objects.filter(type=type, display_type='0').order_by('index')
        type_goods_titles_dict[type] = type_goods_titles


    # 组织模板上下文
    context = {
               'types': types,
               'goods_banners': goods_banners,
               'promotion_banners': promotion_banners,
               'type_goods_banners_dict': type_goods_banners_dict,
               'type_goods_titles_dict': type_goods_titles_dict,
               }

    # 使用模板
    # 1.加载模板文件,返回模板对象
    temp = loader.get_template('static_index.html')
    # 2.定义模板上下文
    # context = RequestContext(request, context)# 这一步可以省略
    # 3.渲染模板
    static_index_html = temp.render(context)

    # 生成首页对应的静态文件
    # print("------path------")
    save_path = os.path.join(settings.BASE_DIR, 'static/index.html')
    # print(save_path)

    with open(save_path, 'w') as f:
        f.write(static_index_html)
    # print(static_index_html)

