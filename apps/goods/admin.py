from django.contrib import admin
from django.core.cache import cache
from goods.models import GoodsType, GoodsSKU, Goods, GoodsImage, IndexGoodsBanner,\
    IndexPromotionBanner, IndexTypeGoodsBanner


class BaseModelAdmin(admin.ModelAdmin):
    """自定义模型管理类"""
    def save_model(self, request, obj, form, change):
        # 继承父类中的原有save_model方法，保持不变
        super().save_model(request, obj, form, change)
        # 后台管理页面执行新增或更改操作后,需重新生成首页静态文件-->这也是自定义模型管理类的原因
        # 使用celery异步操作，每次更改后自动生成新的首页静态文件
        # 发出celery任务
        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()

        # 更新页面缓存--->比较简单的的做法：可直接删除缓存，在访问页面时，直接重新从数据库读取
        # 删除缓存
        cache.delete('static_index_data')

    def delete_model(self, request, obj):
        """删除表中的数据时使用"""
        super().delete_model(request, obj)

        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()

        cache.delete('static_index_data')


class GoodsTypeAdmin(BaseModelAdmin):
    pass


class GoodsSKUAdmin(BaseModelAdmin):
    pass


class GoodsAdmin(BaseModelAdmin):
    pass


class GoodsImageAdmin(BaseModelAdmin):
    pass


class IndexGoodsBannerAdmin(BaseModelAdmin):
    pass


class IndexPromotionBannerAdmin(BaseModelAdmin):
    pass


class IndexTypeGoodsBannerAdmin(BaseModelAdmin):
    pass



# Register your models here.
admin.site.register(GoodsType, GoodsTypeAdmin)
admin.site.register(GoodsSKU, GoodsSKUAdmin)
admin.site.register(Goods, GoodsAdmin)
admin.site.register(GoodsImage, GoodsImageAdmin)
admin.site.register(IndexGoodsBanner, IndexGoodsBannerAdmin)
admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin)
admin.site.register(IndexTypeGoodsBanner, IndexTypeGoodsBannerAdmin)



