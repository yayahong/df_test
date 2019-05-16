from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse
from django.views.generic import View
from django_redis import get_redis_connection
from user.models import User, Address
from goods.models import GoodsSKU
from order.models import OrderInfo, OrderGoods
from df_test import settings
from celery_tasks.tasks import send_register_active_email
from utils.mixin import LoginRequiredMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired

import re


# Create your views here.


# /user/register
class RegisterView(View):
    """注册视图类"""
    def get(self,request):
        """显示注册页面"""
        return render(request, "register.html")

    def post(self,request):
        """进行注册处理"""
        # 获取提交的注册信息/接收数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        check_password = request.POST.get('cpwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        # 校验数据是否完整
        if not all([username, password, email]):
            # 数据不完整
            return render(request, "register.html", {'errormsg': '数据不完整'})

        # 校验邮箱
        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            # 邮箱格式不正确
            return render(request, "register.html", {'errormsg': '邮箱格式不正确'})

        # 校验用户协议
        if allow != 'on':
            # 未同意协议
            return render(request, "register.html", {'errormsg': '请同意用户协议'})

        # 校验用户名是否已存在
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 用户名不存在
            user = None

        if user:
            # 用户名已存在
            return render(request, "register.html", {'errormsg': '用户名已存在'})

        # 业务处理：若通过注册校验，则新建uesr信息，保存进数据库
        # user = User()
        # user.username = username
        # user.password = password
        # user.save()

        user = User.objects.create_user(username, email, password)
        # 用户认证系统默认新注册的用户是激活状态，应设为未激活
        user.is_active = 0
        user.save()

        # 发送激活邮件，包含激活链接：http://127.0.0.1:8080/user/active/id
        # 激活链接中包含加密的用户身份信息

        # 加密用户信息，生成激活的token
        serializer = Serializer(settings.SECRET_KEY, 3600)
        # user_id = user.get('id')
        info = {'confirm': user.id}
        token = serializer.dumps(info)# bytes
        token = token.decode()

        # 发送激活邮件
        send_register_active_email.delay(email, username, token)

        # 并返回首页页面
        return redirect(reverse('goods:index'))


# /user/active/...
class ActiveView(View):
    """用户激活"""

    def get(self,request,token):
        # 进行解密，获取用户信息
        serializer = Serializer(settings.SECRET_KEY, 3600)

        try:
            info = serializer.loads(token)

        except SignatureExpired:
            # 激活链接已过期
            return HttpResponse("激活链接已过期，请重新发送邮件验证！")

        else:
            user_id = info['confirm']
            # 激活用户
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()
            # 跳转到登陆页面
            return redirect(reverse('user:login'))


# /user/login
class LoginView(View):
    """用户登录"""

    def get(self, request):
        """显示登陆页面"""
        # 判断是否记住用户名
        if 'username' in request.COOKIES:
            username = request.COOKIES['username']
            checked = 'checked'
        else:
            username = ''
            checked = ''

        return render(request, 'login.html', {'username': username, 'checked': checked})

    def post(self, request):
        """登陆处理"""
        # 1.获取用户名等数据
        username = request.POST.get('username')
        password = request.POST.get('pwd')
        remember = request.POST.get('remember')
        # 2.校验数据
        # 校验数据是否完整
        if not all([username, password]):
            return render(request, 'login.html', {"errmsg": "数据不完整"})
        # 3.进行业务处理：登陆
        # 4.返回应答
        # User.objects.get(username=username, password=password)
        user = authenticate(username=username, password=password)
        if user is not None:
            # 用户名，密码正确
            if user.is_active:
                # 用户已激活
                # 记录用户的登陆状态：login()使用Django的session框架来将用户的ID保存在session中
                login(request, user)

                # 获取登陆后需跳转的页面的url,默认值设为首页
                next_url = request.GET.get('next', reverse('goods:index'))
                response = redirect(next_url)

                # 校验记住用户名
                if remember == 'on':
                    # 记住用户名：设置cookies
                    response.set_cookie('username', username, max_age=7 * 24 * 3600)
                else:
                    # 不记住用户名:删除记录用户名的cookies
                    response.delete_cookie('username')

                # 登陆，返回首页
                return response

            else:
                # 用户未激活
                return render(request, 'login.html', {"errmsg": "用户未激活"})
        else:
            # 用户名或密码错误
            return render(request, 'login.html', {"errmsg": "用户名或密码错误"})


class LogoutView(View):
    """退出登陆"""
    def get(self, request):
        # 清除用户的session等对话信息，调用logout()
        logout(request)
        return redirect(reverse("goods:index"))


# /user
class UserInfoView(LoginRequiredMixin, View):
    """用户中心-信息页"""
    def get(self, request):
        """显示用户中心-信息页"""
        page_title = 'info'
        # 获取基本信息
        user = request.user
        address = Address.objects.get_default_addr(user)

        # 获取用户最近浏览信息
        # 使用redis数据库存储历史浏览记录
        # 创建redis数据库客户端对象
        # from redis import StrictRedis
        # st = StrictRedis(host='192.168.187.140:6379', port='6379', db='3')
        con = get_redis_connection("default")
        history_key = "history_%d" % user.id
        # 从redis数据库获取存储的历史浏览记录
        goods_ids = con.lrange(history_key, 0, 4) # 取出来的数据goods_ids为一个查询集
        # 根据id从数据库获取id对应的商品对象
        goods_list = []
        for goods_id in goods_ids:
            goods = GoodsSKU.objects.get(id=goods_id)
            goods_list.append(goods)

        # 组织模板上下文
        context = {'page_title': page_title, 'address': address, 'goods_list': goods_list}
        # 返回应答
        # 除了视图类返回的模板变量，django框架也会把request.user传递给模板文件
        return render(request, 'user_center_info.html', context)


# /user/order/页码
class UserOrderView(LoginRequiredMixin, View):
    """用户中心-订单页"""
    def get(self, request, page):
        """显示用户中心-订单页"""
        page_title = "order"

        # 获取页面所需的数据：order_info, order_sku,分页paginator
        # 获取当前用户信息
        user = request.user

        # 获取订单数据
        orders = OrderInfo.objects.filter(user=user).order_by('-update_time')

        # 获取订单商品数据
        for order in orders:
            order_skus = OrderGoods.objects.filter(order=order).order_by('-update_time')

            for order_sku in order_skus:
                # 计算商品数量小计
                order_sku_amount = (order_sku.count)*(order_sku.price)
                # 给order_sku动态的添加属性amount
                order_sku.amount = order_sku_amount
            # 给order动态添加属性skus,订单实付款total_pay
            order.skus = order_skus
            order.total_pay = order.total_price + order.transit_price
            # 获取订单状态,动态添加属性status,保存订单状态名
            order.status_name = OrderInfo.ORDER_STATUS[order.order_status]
        # 分页
        # 使用django分页类
        paginator = Paginator(orders, 1)

        # 获取页码信息,校验页码
        try:
            page = int(page)
        except Exception as e:
            page = 1
            print('page无效')
        if page > paginator.num_pages:
            # 页码超出最大页码范围
            page = 1

        # 获取当前页码/第page页的页面实例对象
        order_page = paginator.page(page)

        # 对页面的页码进行控制：最多显示5页页码
        # 1.如果总页数<=5,显示所有页码
        # 2.当前页是前3页，显示页码前5页页码
        # 3.当前页是后3页，显示最后5页页码
        # 4.显示当前页前2页，当前页,当前页后2页页码
        current_page = order_page.number
        num_pages = paginator.num_pages
        if num_pages <= 5:
            pages = paginator.page_range
        elif current_page <= 3:
            pages = range(1, 6)
        elif current_page >= num_pages - 2:
            pages = range(num_pages - 4, num_pages + 1)
        else:
            pages = range(current_page - 2, current_page + 3)

        context = {
            'page_title': page_title,
            'orders':orders,
            'order_page':order_page,
            'pages':pages
        }

        return render(request, 'user_center_order.html', context)


# /user/address
class UserAddressView(LoginRequiredMixin, View):
    """用户中心-地址页"""
    def get(self, request):
        """显示用户中心-地址页"""
        page_title = 'address'

        # django在每个请求上提供一个request.user属性，表示当前的用户,
        # 如果当前的用户没有登入，该属性将设置成AnonymousUser的一个实例，否则它将是User的实例
        # 获取当前用户数据/登陆用户对应的User对象
        user = request.user

        # # 获取当前/默认地址数据
        # try:
        #     address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     # 没有默认地址
        #     address = None

        address = Address.objects.get_default_addr(user)

        return render(request, 'user_center_site.html', {'page_title': page_title, 'address': address})

    def post(self, request):
        """添加地址"""
        # 1.获取提交数据
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')

        # 获取当前用户数据/登陆用户对应的User对象
        user = request.user

        # 2.校验数据
        # 校验数据是否完整
        if not all([receiver, addr, phone]):
            return render(request, 'user_center_site.html', {'errmsg': '数据不完整'})

        # 校验phone
        res = re.match(r'^1[34578]\d{9}$', phone)
        if res is None:
            return render(request, 'user_center_site.html', {'errmsg': '手机号码格式不正确'})

        # 3.进行业务处理:添加地址
        # 若用户不存在默认收货地址，则添加为默认地址，否则添加为普通地址

        # 获取当前/默认地址数据
        # try:
        #     address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     # 没有默认地址
        #     address = None

        address = Address.objects.get_default_addr(user)

        if address:
            is_default = False
        else:
            is_default = True

        Address.objects.create(receiver=receiver,
                               addr=addr,
                               zip_code=zip_code,
                               phone=phone,
                               user=user,
                               is_default=is_default
                               )

        # 4.返回应答
        return redirect(reverse('user:user_address'))




