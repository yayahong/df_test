from django.shortcuts import render,redirect
from django.core.urlresolvers import reverse
from django.views.generic import View
from django.core.cache import cache
from django.core.paginator import Paginator
from django_redis import get_redis_connection
from goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner,GoodsSKU
from order.models import OrderGoods

# Create your views here.

# http://127.0.0.1:8000/
# def index(request):
#     """显示首页"""
#     return render(request, 'index.html')


# http://http://192.168.187.140:8080/
class IndexView(View):
    """首页类"""
    def get(self, request):
        """显示首页"""

        # 先尝试获取缓存
        context = cache.get('static_index_data')
        # print(context)

        if context is None:
            # 没有页面缓存数据
            print('没有缓存数据')
            # 从数据库获取页面信息
            # 获取首页商品分类信息
            types = GoodsType.objects.all()

            # 获取首页轮播图商品信息
            goods_banners = IndexGoodsBanner.objects.all().order_by('index')

            # 获取首页足促销活动商品信息
            promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

            # 获取首页分类展示商品信息
            # type_goods_banners_dict = {}
            # type_goods_titles_dict = {}
            # for type in types:
            #     # type_goods_banners = IndexTypeGoodsBanner.objects.get(type=type, display_type=1).order_by('index')
            #     type_goods_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type='1').order_by('index')
            #     type_goods_banners_dict[type] = type_goods_banners
            #     # type_goods_titles = IndexTypeGoodsBanner.objects.get(type=type, display_type=0).order_by('index')
            #     type_goods_titles = IndexTypeGoodsBanner.objects.filter(type=type, display_type='0').order_by('index')
            #     type_goods_titles_dict[type] = type_goods_titles

            # 采用动态的给type添加属性的方法
            for type in types:
                type_goods_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type='1').order_by('index')
                # 给type动态添加goods_banners属性
                type.goods_banners = type_goods_banners
                type_goods_titles = IndexTypeGoodsBanner.objects.filter(type=type, display_type='0').order_by('index')
                # 给type动态添加goods_titles属性
                type.goods_titles = type_goods_titles

            context = {
                       'types': types,
                       'goods_banners': goods_banners,
                       'promotion_banners': promotion_banners,
                       'type_goods_banners': type_goods_banners,
                       'type_goods_titles': type_goods_titles,
                       }

            # 设置缓存(key,value,timeout)
            cache.set('static_index_data', context, 3600)



        # 获取购物车商品数量
        # 使用redis数据库存储购物车商品数量记录
        # 创建redis客户端链接对象
        conn = get_redis_connection('default')
        # 获取当前登陆的用户
        user = request.user
        # 购物车商品数量默认设为0
        cart_goods_count = 0
        if user.is_authenticated():
            # 用户已登陆
            cart_key = 'cart_%d'%user.id
            cart_goods_count = conn.hlen(cart_key)

        # 组织模板上下文
        # update()可增加或新增context
        context.update(cart_goods_count=cart_goods_count)

        return render(request, 'index.html', context)


# /goods/商品id
class DetailView(View):
    """商品详情页"""
    def get(self,request, goods_id):
        """显示商品详情页"""
        # 获取商品信息
        try:
            sku = GoodsSKU.objects.get(id=goods_id)
        except GoodsSKU.DoesNotExist:
            # 商品id不存在，返回首页
            return redirect(reverse('goods:index'))

        # 获取商品分类信息
        types = GoodsType.objects.all()

        # 获取同一spu的其他规格商品
        same_spu_goods = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=sku.id)

        # 获取商品评论信息,商品评论位于订单商品表中
        order_skus = OrderGoods.objects.filter(sku=sku).exclude(comment='')

        # 获取新品推荐信息-->即同类商品信息--->新品：需要排序-->降序
        new_skus = GoodsSKU.objects.filter(type=sku.type).order_by('-create_time')[:2]

        # 获取购物车商品数量信息
        cart_goods_count = 0
        # 获取当前登陆的用户信息
        user = request.user
        if user.is_authenticated():
            # 用户已登陆
            # 从缓存数据库中获取用户购物车商品数量
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_goods_count = conn.hlen(cart_key)

            # 添加用户历史浏览记录
            history_key = 'history_%d'%user.id
            # 1.删除这个商品之前的浏览记录
            conn.lrem(history_key, 0, goods_id)
            # 2.添加这个商品的浏览记录,从左向右添加--->最新的浏览记录
            conn.lpush(history_key, goods_id)
            # 3.只保留最新的5条浏览记录
            conn.ltrim(history_key, 0, 4)

        context = {'sku': sku,
                   'types':types,
                   'order_skus':order_skus,
                   'new_skus':new_skus,
                   'cart_goods_count':cart_goods_count,
                   'same_spu_goods':same_spu_goods
                   }

        return render(request, 'detail.html', context)


# /list/种类id/页码？sort=排序
class ListView(View):
    """列表详情页"""
    def get(self, request, type_id, page):
        """显示列表页"""
        # 获取商品分类信息
        types = GoodsType.objects.all()

        # 判断type是否存在
        print(type_id)

        try:
            type_id = int(type_id)
            type = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            # 所选的类别不存在,返回首页
            print('type不存在')
            return redirect(reverse('goods:index'))

        # 获取当前商品类别的所有商品信息--->按照排序方式
        # sort=‘default'---->默认排序，按照id降序
        # sort=’price‘--->按照价格升序
        # sort='hot'--->按照销量降序
        # 获取sort
        print('----sort----')
        sort = request.GET.get('sort', 'default')
        print(sort)
        if sort == 'price':
            skus = GoodsSKU.objects.filter(type=type).order_by('price')
        elif sort == 'hot':
            skus = GoodsSKU.objects.filter(type=type).order_by('-sales')
        else:
            skus = GoodsSKU.objects.filter(type=type).order_by('-id')

        # 获取新品推荐信息-->同一类别的其他商品--->按创建时间降序---->最新的2个
        new_skus = GoodsSKU.objects.filter(type=type).order_by('-create_time')[:2]

        # 使用django分页类
        paginator = Paginator(skus, 1)

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
        skus_page = paginator.page(page)

        # 对页面的页码进行控制：最多显示5页页码
        # 1.如果总页数<=5,显示所有页码
        # 2.当前页是前3页，显示页码前5页页码
        # 3.当前页是后3页，显示最后5页页码
        # 4.显示当前页前2页，当前页,当前页后2页页码
        current_page = skus_page.number
        num_pages = paginator.num_pages
        if num_pages <= 5:
            pages = paginator.page_range
        elif current_page <= 3:
            pages = range(1,6)
        elif current_page >= num_pages-2:
            pages = range(num_pages-4, num_pages+1)
        else:
            pages = range(current_page-2, current_page+3)

        # 获取购物车商品数量
        cart_goods_count = 0
        # 获取当前登陆的用户信息
        user = request.user
        if user.is_authenticated():
            # 用户已登陆
            # 从缓存数据库中获取用户购物车商品数量
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_goods_count = conn.hlen(cart_key)
            print(cart_goods_count)

        print(cart_goods_count)
        context = {
            'types':types,
            'skus':skus,
            'new_skus':new_skus,
            'skus_page':skus_page,
            'cart_goods_count': cart_goods_count,
            'type': type,
            'sort':sort,
            'pages':pages
        }

        return render(request, 'list.html', context)

