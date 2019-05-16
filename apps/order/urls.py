from django.conf.urls import url
from order.views import PlaceOrderView, OrderCommitView, OrderPayView, PayCheckView


urlpatterns = [
    url(r'^place$', PlaceOrderView.as_view(), name='place'), # 提交订单页面显示
    url(r'^commit$', OrderCommitView.as_view(), name='commit'), # 提交订单处理，生成订单
    url(r'^pay$', OrderPayView.as_view(), name='pay'), # 订单交易处理
    url(r'^pay/check$', PayCheckView.as_view(), name='pay_check'), # 订单支付结果查询
]
