from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db import transaction
from django.views.generic import View
from django.core.urlresolvers import reverse
from django_redis import get_redis_connection
from django.conf import settings
from goods.models import GoodsSKU
from user.models import Address
from order.models import OrderInfo, OrderGoods
from utils.mixin import LoginRequiredMixin
from datetime import datetime
from alipay import AliPay
import os



# Create your views here.
# post提交表单
# 传递参数:多个sku_ids-->list
# 购物车结算--->提交订单页
# /order/place
class PlaceOrderView(LoginRequiredMixin, View):
    """提交订单页"""
    def post(self, request):
        # 获取登陆的用户信息
        user = request.user
        # 获取传递的数据
        sku_ids = request.POST.getlist('sku_ids')
        # 校验数据
        if not sku_ids:
            # 数据为空,返回购物车页面
            return redirect(reverse('cart:cart'))

        # 获取用户地址信息
        # address = Address.objects.get_default_addr()
        addrs = Address.objects.filter(user=user)


        # 连接redis数据库
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id

        skus = []
        total_count = 0
        total_amount = 0
        # 遍历列表,获取页面需要的信息
        for sku_id in sku_ids:
            try:
                sku = GoodsSKU.objects.get(id=sku_id)
            except GoodsSKU.DoesNotExist:
                # 商品id不存在
                return redirect(reverse('cart:cart'))
            # 获取商品数目
            count = conn.hget(cart_key, sku_id)
            if not count:
                # 数据为空,返回购物车页面
                return redirect(reverse('cart:cart'))
            amount = sku.price * int(count)
            # 动态地给商品添加属性
            sku.count = int(count)
            sku.amount = amount
            total_count += sku.count
            total_amount += sku.amount
            # 添加到商品列表
            skus.append(sku)

        # 获取商品的运费
        # 实际开发的时候,运费属于一个子系统
        transit_price = 10

        # 实付款
        total_pay = total_amount + transit_price

        # 所有商品id字符串
        sku_ids = ','.join(sku_ids)


        # 组织上下文
        context = {'addrs':addrs,
                   'skus':skus,
                   'total_count':total_count,
                   'total_amount':total_amount,
                   'transit_price':transit_price,
                   'total_pay':total_pay,
                   'sku_ids':sku_ids
                   }

        return render(request, 'place_order.html', context)


# ajax post 提交订单
# 需要传递的参数：addr_id,pay_method,sku_ids
# mysql事务，一组sql操作,要么都成功，要么都失败
# /order/commit
# 高并发--->悲观锁
class OrderCommitView1(View):
    """提交订单处理，生成订单"""
    @transaction.atomic
    def post(self, request):
        """提交订单处理"""
        # 获取当前用户信息
        user = request.user
        # 判断是否登陆
        if not user.is_authenticated():
            # 用户未登陆
            return JsonResponse({'res':0, 'errmsg':'用户未登录'})

        # 获取传递的数据
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids') # '1,2,3'

        # 校验数据完整
        if not all([addr_id, pay_method, sku_ids]):
            # 数据不完整
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        # 校验支付方式
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            # 非法的支付方式
            return JsonResponse({'res': 2, 'errmsg': '非法的支付方式'})

        # 校验地址
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            # 地址不存在
            return JsonResponse({'res': 3, 'errmsg': '地址非法'})

        # 设置mysql事务保存点
        save_id = transaction.savepoint()
        try:
            # todo：进行核心业务处理：创建订单
            # 1.将订单信息写入数据库：向df_order_info中添加一条记录--->还缺的数据：order_id,total_count,total_price,transit_price
            # 2.将订单商品信息写入：df_order_gooods---->还缺的数据:sku,order
            # 组织参数
            # 订单id：201808101212 +user.id
            order_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(user.id)
            # 初始设置商品总数量和总价格为0，之后再更新
            total_count = 0
            total_price = 0
            # 运费
            transit_price = 10
            # todo：1.用户每下一个订单，就向df_order_info中添加一条记录/创建一个OrderInfo实例对象
            order = OrderInfo.objects.create(
                order_id=order_id,
                user=user,
                addr=addr,
                pay_method=pay_method,
                total_count=total_count,
                total_price=total_price,
                transit_price=transit_price
            )
            # todo：2.订单中有多少种商品，就向df_order_gooods中添加多少条记录
            # 同时校验商品id
            # 连接redis
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id

            sku_ids = sku_ids.split(',')  # [1,2,3]
            for sku_id in sku_ids:
                try:
                    # select * from df_goods_sku where id=sku_id for update;
                    sku = GoodsSKU.objects.select_for_update().get(id=sku_id)# 加上锁-->悲观锁
                except GoodsSKU.DoesNotExist:
                    # 商品不存在
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({'res': 4, 'errmsg': '商品非法'})
                print('user_%s:sku_%s:stock_%s'%(user.id,sku_id,sku.stock))
                import time
                time.sleep(10)

                # 获取商品数目
                count = conn.hget(cart_key, sku_id)
                count = int(count)
                # todo:判断商品库存--->当多人同时下单同一商品时，会发生其他人下单之后，商品库存补足，
                # 但已经加入提交订单表中的用户数据没有更新
                if count > sku.stock:
                    # 库存不足
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({'res': 6, 'errmsg': '库存不足'})

                order_sku = OrderGoods.objects.create(
                    order=order,
                    sku=sku,
                    count=count,
                    price=sku.price,
                )
                # todo:计算订单所有商品总数量和总价格
                total_count += count
                total_price += count*sku.price
                # todo：4.更新订单表中每种商品库存和总销量
                sku.stock -= count
                sku.sales += count
                sku.save() # 更新之后需要保存

            # todo:3.更新订单信息表中商品总数量和总价格
            order.total_count = total_count
            order.total_price = total_price
            order.save()# 更新之后需要保存
        except Exception as e:
            # 事务执行中出现错误
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res': 7, 'message': '下单失败'})
        # 提交事务
        transaction.savepoint_commit(save_id)

        # todo：5.清空购物车记录-->redis
        conn.hdel(cart_key, *sku_ids) #×sku_ids对[1,2,3]解包--->1,2,3

        # 返回应答
        return JsonResponse({'res': 5, 'message': '创建订单成功'})

# 高并发--->乐观锁
class OrderCommitView(View):
    """提交订单处理，生成订单"""
    @transaction.atomic
    def post(self, request):
        """提交订单处理"""
        # 获取当前用户信息
        user = request.user
        # 判断是否登陆
        if not user.is_authenticated():
            # 用户未登陆
            return JsonResponse({'res':0, 'errmsg':'用户未登录'})

        # 获取传递的数据
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids') # '1,2,3'

        # 校验数据完整
        if not all([addr_id, pay_method, sku_ids]):
            # 数据不完整
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        # 校验支付方式
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            # 非法的支付方式
            return JsonResponse({'res': 2, 'errmsg': '非法的支付方式'})

        # 校验地址
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            # 地址不存在
            return JsonResponse({'res': 3, 'errmsg': '地址非法'})

        # 设置mysql事务保存点
        save_id = transaction.savepoint()
        try:
            # todo：进行核心业务处理：创建订单
            # 1.将订单信息写入数据库：向df_order_info中添加一条记录--->还缺的数据：order_id,total_count,total_price,transit_price
            # 2.将订单商品信息写入：df_order_gooods---->还缺的数据:sku,order
            # 组织参数
            # 订单id：201808101212 +user.id
            order_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(user.id)
            # 初始设置商品总数量和总价格为0，之后再更新
            total_count = 0
            total_price = 0
            # 运费
            transit_price = 10
            # todo：1.用户每下一个订单，就向df_order_info中添加一条记录/创建一个OrderInfo实例对象
            order = OrderInfo.objects.create(
                order_id=order_id,
                user=user,
                addr=addr,
                pay_method=pay_method,
                total_count=total_count,
                total_price=total_price,
                transit_price=transit_price
            )
            # todo：2.订单中有多少种商品，就向df_order_gooods中添加多少条记录
            # 同时校验商品id
            # 连接redis
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id

            sku_ids = sku_ids.split(',')  # [1,2,3]
            for sku_id in sku_ids:
                for i in range(3):
                    # 乐观锁尝试3次下单---->下单失败的几率会很小
                    try:
                        sku = GoodsSKU.objects.get(id=sku_id)
                    except GoodsSKU.DoesNotExist:
                        # 商品不存在
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res': 4, 'errmsg': '商品非法'})



                    # 获取商品数目
                    count = conn.hget(cart_key, sku_id)
                    count = int(count)
                    # todo:判断商品库存--->当多人同时下单同一商品时，会发生其他人下单之后，商品库存补足，
                    # 但已经加入提交订单表中的用户数据没有更新
                    if count > sku.stock:
                        # 库存不足
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res': 6, 'errmsg': '库存不足'})

                    # todo：更新订单表中每种商品库存和总销量
                    origin_stock = sku.stock
                    new_stock = origin_stock - count
                    new_sales = sku.sales + count

                    print('user_%s:sku_%s:stock_%s：times：%s' % (user.id, sku_id, sku.stock,i))
                    import time
                    time.sleep(10)

                    # 使用乐观锁
                    # update df_goods_sku set stock=new_stock,sales=new_sales where id=sku_id and stock=origin_stock;
                    # res返回的是受影响的行数
                    res = GoodsSKU.objects.filter(id=sku_id,stock=origin_stock).update(stock=new_stock,sales=new_sales)
                    if res == 0:
                        # 下单失败
                        if i == 2:
                            #第3次尝试失败
                            # 事务回滚
                            transaction.savepoint_rollback(save_id)
                            return JsonResponse({'res': 8, 'errmsg': '下单失败2'})
                        # 如果不是第3次，是前2次失败的话，再继续循环尝试
                        continue

                    # sku.save()  # 更新之后需要保存

                    order_sku = OrderGoods.objects.create(
                        order=order,
                        sku=sku,
                        count=count,
                        price=sku.price,
                    )
                    # todo:计算订单所有商品总数量和总价格
                    total_count += count
                    total_price += count * sku.price

                    # res!=0---->可以成功下单，跳出尝试3次的循环
                    break

            # todo:3.更新订单信息表中商品总数量和总价格
            order.total_count = total_count
            order.total_price = total_price
            order.save()# 更新之后需要保存
        except Exception as e:
            # 事务执行中出现错误
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res': 7, 'errmsg': '下单失败'})
        # 提交事务
        transaction.savepoint_commit(save_id)

        # todo：5.清空购物车记录-->redis
        conn.hdel(cart_key, *sku_ids) #×sku_ids对[1,2,3]解包--->1,2,3

        # 返回应答
        return JsonResponse({'res': 5, 'message': '创建订单成功'})


# 订单支付处理
# ajax post :order_id
# order/pay
class OrderPayView(View):
    """订单付款处理"""
    def post(self, request):
        print("---post-----")
        # 校验用户登陆
        user = request.user
        print("---user-----")
        if not user.is_authenticated():
            # 用户未登陆
            return JsonResponse({'res':0,'errmsg':'用户未登陆'})
        # 接收参数
        print("---order_id-----")
        order_id = request.POST.get('order_id')
        print("---order_id2-----")

        # 校验参数
        if not order_id:
            # 参数无效
            return JsonResponse({'res': 1, 'errmsg': '无效的订单编号'})
        print("---order_id3-----")
        # 获取订单信息
        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          order_status=1,
                                          pay_method=3)
        except OrderInfo.DoesNotExist:
            # 订单不存在
            return JsonResponse({'res': 2, 'errmsg': '订单错误'})
        print("---order-----")
        # 获取订单总付款金额
        total_pay = order.total_price + order.transit_price
        print("---total-----")
        # 进行业务处理：付款

        # 使用python SDK调用支付宝的支付接口
        # 初始化
        print("---初始化------")
        app_private_key_url = os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem')
        alipay_public_key_url = os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem')
        app_private_key_string = open(app_private_key_url).read()
        alipay_public_key_string = open(alipay_public_key_url).read()

        alipay = AliPay(
            appid="2016100100635939",
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=alipay_public_key_string,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug = True  # 默认False,沙箱环境设置为true
        )
        print("---初始化2------")

        # 调用支付接口
        # 电脑网站支付，需要跳转到https://openapi.alipaydev.com/gateway.do? + order_string
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no = order_id, # 订单编号
            total_amount=str(total_pay), # 支付总金额
            subject='天天生鲜%s'%order_id,
            return_url= None,
            notify_url= None # 可选, 不填则使用默认notify url
        )
        print("---3------")
        # 向前端返回支付宝支付页面url
        pay_url = 'https://openapi.alipaydev.com/gateway.do?' + order_string

        # 返回应答
        return JsonResponse({'res':3, 'pay_url':pay_url})


# /order/pay/check
class PayCheckView(View):
    """订单支付结果查询"""
    def post(self, request):
        # 校验用户登陆
        user = request.user
        if not user.is_authenticated():
            # 用户未登陆
            return JsonResponse({'res': 0, 'errmsg': '用户未登陆'})
        # 接收参数
        order_id = request.POST.get('order_id')

        # 校验参数
        if not order_id:
            # 参数无效
            return JsonResponse({'res': 1, 'errmsg': '无效的订单编号'})
        # 获取订单信息
        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,# 用户也需要验证
                                          order_status=1,
                                          pay_method=3)
        except OrderInfo.DoesNotExist:
            # 订单不存在
            return JsonResponse({'res': 2, 'errmsg': '订单错误'})
        # 获取订单总付款金额
        total_pay = order.total_price + order.transit_price
        # 进行业务处理：付款
        # 初始化
        print("---初始化------")
        app_private_key_url = os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem')
        alipay_public_key_url = os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem')
        app_private_key_string = open(app_private_key_url).read()
        alipay_public_key_string = open(alipay_public_key_url).read()

        alipay = AliPay(
            appid="2016100100635939",
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=alipay_public_key_string,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False,沙箱环境设置为true
        )

        # 调用支付宝交易查询接口
        while True:
            response = alipay.api_alipay_trade_query(order_id)
            """
            "alipay_trade_query_response": {
                "trade_no": "2017032121001004070200176844", #支付宝交易号
                "code": "10000", # 网关返回码--接口调用是否成功
                "invoice_amount": "20.00",
                "open_id": "20880072506750308812798160715407",
                "fund_bill_list": [
                    {
                        "amount": "20.00",
                        "fund_channel": "ALIPAYACCOUNT"
                    }
                ],
                "buyer_logon_id": "csq***@sandbox.com",
                "send_pay_date": "2017-03-21 13:29:17",
                "receipt_amount": "20.00",
                "out_trade_no": "out_trade_no15",# 订单id
                "buyer_pay_amount": "20.00",
                "buyer_user_id": "2088102169481075",
                "msg": "Success",
                "point_amount": "0.00",
                "trade_status": "TRADE_SUCCESS",# 交易状态
                "total_amount": "20.00"
            },
        }
        """
            # 接收返回参数
            trade_no = response.get('trade_no')
            code = response.get('code')
            trade_status = response.get('trade_status')

            if code=='10000' and trade_status== "TRADE_SUCCESS":
                # 交易成功
                # 更新订单状态,添加支付宝交易号
                order.trade_no = trade_no
                order.order_status = 4 # 开发环境没有物流状态，直接调为待评价
                order.save() # 更新数据库数据后，一定要记得保存！！！！
                print(order.order_status)
                # 返回应答
                return JsonResponse({'res':3, 'message':'交易成功'})
            elif code=='40004' or (code=='10000' and trade_status== "WAIT_BUYER_PAY"):
                print(code)
                # 业务处理失败
                # 等待买家付款--->交易没有失败，等5秒后再次调用支付宝查询接口，直到交易成功或交易失败
                import time
                time.sleep(5)
                continue
            else:
                # 交易失败
                print(code)
                return JsonResponse({'res': 4, 'errmsg': '交易失败'})











