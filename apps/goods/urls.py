from django.conf.urls import url
from goods.views import IndexView, DetailView, ListView

urlpatterns = [
    url(r'^index$', IndexView.as_view(), name='index'),# 显示首页
    url(r'^goods/(?P<goods_id>\d+)$', DetailView.as_view(), name='detail'),# 显示商品详情页
    url(r'^list/(?P<type_id>\d+)/(?P<page>\d+)$', ListView.as_view(), name='list'), # 显示分类商品列表页
]
