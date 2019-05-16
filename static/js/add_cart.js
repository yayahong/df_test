/**
 * Created by python on 19-5-6.
 */

$(function(){
    //更新商品总价
    update_goods_amount();
    //定义更新商品总价函数
    function update_goods_amount(){
        //获取商品单价和数量
        price = $('.show_pirze em').text();
        count = $('.num_show').val();
        console.log(price);
        price = parseFloat(price);
        count = parseInt(count);
        console.log(price);
        console.log(count);
        amount = price * count;
        console.log(amount);
        //更新商品总价
        $('.total').children('em').text(amount.toFixed(2)+'元');
    };

    //点击加号增加商品数量
    $('.add').click(function(){
       //获取商品数量
        count = $('.num_show').val();
        count = parseInt(count) + 1;
        //更新商品数量
        $('.num_show').val(count);
        //更新商品总价
        update_goods_amount();
    })



    //点击减号减少商品数量
    $('.minus').click(function(){
        //获取商品数量
        count = $('.num_show').val();
        count = parseInt(count) - 1;
        if(count<=0){
            count = 1;
        }
         //更新商品数量
        $('.num_show').val(count);
        //更新商品总价
        update_goods_amount();
    })

    //用户手动输入之前的商品数量
    $('.num_show').focus(function(){
        prev_count = $(this).val();
    })

    //手动输入商品数量
    $('.num_show').blur(function(){
        //获取输入的商品数量
        count = $(this).val();
        //校验输入的商品数量:非数字、为空、负数
        if(isNaN(count) || count.trim().length==0 ||parseInt(count)<=0){
            //输入数据不合法-->显示用户输入之前的值-->退出blur事件
            $(this).val(prev_count);
            return
        }
        //更新商品数量
        $('.num_show').val(parseInt(count));
        //更新商品总价
        update_goods_amount();
    })




    var $add_x = $('#add_cart').offset().top;
    var $add_y = $('#add_cart').offset().left;

    var $to_x = $('#show_count').offset().top;
    var $to_y = $('#show_count').offset().left;

    //点击加入购物车
    $('#add_cart').click(function(){
        //获取数据
        //获取自定义的属性使用attr(),获取已有的属性使用prop()
        sku_id = $(this).attr('sku_id');
        count = $('.num_show').val();
        //某个特定的名字的input元素
        csrf = $('input[name="csrfmiddlewaretoken"]').val();
        //组织参数
        params = {'sku_id': sku_id, 'count': count, 'csrfmiddlewaretoken': csrf};
        //发起 ajax post请求
        $.post('/cart/add', params, function (data) {
            //获取返回数据
            if (data.res == 6) {
                //添加购物车成功
                //进行添加购物车动画
                $(".add_jump").css({'left': $add_y + 80, 'top': $add_x + 10, 'display': 'block'});
                $(".add_jump").stop().animate({
                        'left': $to_y + 7,
                        'top': $to_x + 7
                    },
                    "fast", function () {
                        //加入购物车动画回调函数--->动画圆点消失
                        $(".add_jump").fadeOut('fast', function () {
                            //动画圆点消失回调函数--->购物车商品条目数更新
                            $('#show_count').html(data.cart_goods_count);
                        });
                    })
            }
            else {
                //添加购物车失败
                alert(data.errmsg)
            }
        })
    })
})
