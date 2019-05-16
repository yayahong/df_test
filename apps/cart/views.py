from django.shortcuts import render
from django.views.generic import View
from django.http import JsonResponse
from goods.models import GoodsSKU
from django_redis import get_redis_connection
from utils.mixin import LoginRequiredMixin
# Create your views here.

# 用户添加商品到购物车分析
# 购物车数据记录：redis缓存--->hash--->cart_user.id: sku_id sku_count
# 请求方式：get--->获取信息，post--->增删改信息
# 点击添加购物车按钮，部分更新页面-->异步操作-->ajax请求-->返回json数据，应答采用JsonResponse
# url:/addcart----->需传递的参数2个：sku_id sku_count，采用post传参数
# 参数传递3种方式：1.url捕获, 2.get:/index?xx=xx, 3.post传递

# ajax发起的请求都在后台，在浏览器上看不到效果---->所以添加购物车视图类不能使用继承LoginRequiredMixin


# /cart/add
class AddCartView(View):
    """添加购物车类"""
    def post(self, request):
        '''添加购物车'''
        # 获取当前用户信息
        user = request.user
        # 首先判断用户是否已登陆
        if not user.is_authenticated():
            # 用户未登陆
            return JsonResponse({'res': 0, 'errmsg': '用户未登陆'})

        # 获取数据
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        # 校验数据
        # 1.校验数据是否完整
        if not all([sku_id, count]):
            # 数据不完整
            return JsonResponse({'res':1, 'errmsg':'数据不完整'})

        # 2.校验商品id是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            # 商品id不存在
            return JsonResponse({'res':2, 'errmsg':'商品id不存在'})

        # 3.校验count是否合法-->非数字，非空
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res':3, 'errmsg':'count不合法'})

        # 4.校验count是否负数
        if count < 0:
            return JsonResponse({'res':4, 'errmsg':'count非负数'})

        # 进行业务处理：添加购物车
        # 连接redis
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id
        # 判断该商品是否已经加入过购物车
        # 如果没有所要取的值,hget()会返回None
        sku_count = conn.hget(cart_key, sku_id)
        if sku_count:
            # 购物车中已经有该商品
            count += int(sku_count)

        # 校验商品的库存
        if count > sku.stock:
            # 库存不足
            return JsonResponse({'res':5, 'errmsg': '库存不足'})

        # 更新购物车商品数量
        conn.hset(cart_key, sku_id, count)
        # 返回购物车商品条目数--->页面右上角购物车显示
        cart_goods_count = conn.hlen(cart_key)

        # 返回应答
        return JsonResponse({'res':6, 'cart_goods_count':cart_goods_count,'sucess':'加入购物车成功'})


# /cart
class CartView(LoginRequiredMixin, View):
    """购物车页面"""
    def get(self, request):
        """显示购物车页面"""
        # 获取当前用户信息
        user = request.user
        # 获取购物车商品信息
        # 连接数据库
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id

        # 初始化
        skus = []
        total_count = 0
        total_amount = 0
        # 校验当前用户购物车是否为空--->若缓存中没有当前用户购物车记录，hlen()返回0，不会报错
        cart_goods_count = conn.hlen(cart_key)

        # cart_info_dict{商品id：商品数量}
        cart_info_dict = conn.hgetall(cart_key)
        print(cart_info_dict)

        for sku_id, count in cart_info_dict.items():

            sku = GoodsSKU.objects.get(id=int(sku_id))
            count = conn.hget(cart_key, sku_id)
            print(sku)
            # 给sku动态添加属性count--商品数量；商品小计amount
            sku.count = int(count)
            sku.amount = (sku.count)*(sku.price)
            skus.append(sku)
            total_count += sku.count
            total_amount += sku.amount

        context = {'skus': skus, 'total_count': total_count, 'total_amount': total_amount}

        return render(request, 'cart.html', context)


# 购物车商品数量增加或减少--->页面部分更新
# ajax post请求
# 需传递参数：sku_id count
# /cart/update
class UpdateCartView(View):
    """购物车页面更新"""
    def post(self,request):
        """更新购物车页面"""
        # 校验登陆
        user = request.user
        if not user.is_authenticated():
            # 用户未登陆
            return JsonResponse({'res':0, 'errmsg':'请先登陆'})
        # 获取传递的参数
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        # 校验数据
        # 1.校验数据完整性
        if not all([sku_id, count]):
            return JsonResponse({'res':1, 'errmsg':'数据不完整'})
        # 2.校验商品id是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            # 商品id不存在
            return JsonResponse({'res': 2, 'errmsg': '商品id不存在'})

        # 3.校验count是否合法-->非数字，非空
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 3, 'errmsg': 'count不合法'})

        # 4.校验count是否负数
        if count < 0:
            return JsonResponse({'res': 4, 'errmsg': 'count非负数'})

        # 进行业务处理：更新redis购物车记录
        # 连接redis
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id

        # 校验商品的库存
        if count > sku.stock:
            # 库存不足
            return JsonResponse({'res': 5, 'errmsg': '库存不足'})

        # 更新购物车记录
        conn.hset(cart_key, sku_id, count)

        # 计算购物车中所有的商品总数量
        total_count = 0
        # hvals可以返回所有的count值的列表
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)
        # 返回应答
        return JsonResponse({'res': 6, 'total_count': total_count, 'sucess': '更新购物车记录成功'})

# 从购物车中删除商品
# redis删除数据--hdel()
# ajax post
# sku_id
# /cart/del
class DelCartView(View):
    """从购物车中删除商品"""
    def post(self, request):
        """从购物车中删除商品"""
        # 校验登陆
        user = request.user
        if not user.is_authenticated():
            # 用户未登陆
            return JsonResponse({'res': 0, 'errmsg': '请先登陆'})
        # 获取传递的参数
        sku_id = request.POST.get('sku_id')

        # 校验数据
        # 校验数据完整
        if not sku_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的商品id'})

        # 校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            # 商品id不存在
            return JsonResponse({'res': 2, 'errmsg': '商品id不存在'})

        # 进行业务处理：删除商品信息
        # 连接redis
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id

        conn.hdel(cart_key, sku_id)

        # 更新购物车商品总数量
        total_count = 0
        # hvals可以返回所有的count值的列表
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)
        # 返回应答
        return JsonResponse({'res': 3, 'total_count': total_count, 'sucess': '更新购物车记录成功'})
