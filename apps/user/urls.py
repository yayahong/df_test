from django.conf.urls import url
from . import views
from user.views import RegisterView, ActiveView, LoginView, LogoutView, UserInfoView, UserAddressView, UserOrderView
from django.contrib.auth.decorators import login_required

urlpatterns = [
    # url(r'^register$', views.register, name='register'),# 注册
    url(r'^register$', RegisterView.as_view(), name='register'), # 注册
    url(r'^active/(?P<token>.*)$', ActiveView.as_view(), name='active'), #用户激活
    url(r'^login$', LoginView.as_view(), name='login'), # 登陆
    # url(r'^$', login_required(UserInfoView.as_view()), name='user_info'), # 用户中心-信息页
    # url(r'^order$', login_required(UserOrderView.as_view()), name='user_order'), # 用户中心-订单页
    # url(r'^address$', login_required(UserAddressView.as_view()), name='user_address'), # 用户中心-地址页

    url(r'^logout$', LogoutView.as_view(), name='logout'), # 退出登录
    url(r'^$', UserInfoView.as_view(), name='user_info'),  # 用户中心-信息页
    url(r'^order/(?P<page>\d+)$', UserOrderView.as_view(), name='user_order'), # 用户中心-订单页
    url(r'^address$', UserAddressView.as_view(), name='user_address'), # 用户中心-地址页
]
