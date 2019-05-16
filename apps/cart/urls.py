from django.conf.urls import url
from cart.views import AddCartView, CartView, UpdateCartView,DelCartView

urlpatterns = [
    url(r'^$', CartView.as_view(), name='cart'), # 显示购物车页面
    url(r'^add$', AddCartView.as_view(), name='add'), # 添加购物车
    url(r'^update$', UpdateCartView.as_view(), name='update'), # 更新购物车页面
    url(r'^del$', DelCartView.as_view(), name='delete'), # 删除购物车中的商品
]
