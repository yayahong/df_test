from django.db import models
from db.base_model import BaseModel
from tinymce.models import HTMLField

# Create your models here.


class GoodsType(BaseModel):
    """商品类型模型类"""
    name = models.CharField(max_length=20, verbose_name='种类名称')
    logo = models.CharField(max_length=20, verbose_name='标识')
    image = models.ImageField(upload_to='type', verbose_name='商品类型图片')

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'df_goods_type'
        verbose_name = '商品种类'
        verbose_name_plural = verbose_name


class GoodsSKU(BaseModel):
    """SKU商品模型类"""
    STATUS_CHOICES = (
        (0, '下线'),
        (1, '上线')
    )

    type = models.ForeignKey('GoodsType', verbose_name='商品种类', on_delete=models.CASCADE)
    goods = models.ForeignKey('Goods', verbose_name='商品SPU', on_delete=models.CASCADE)
    name = models.CharField(max_length=20, verbose_name='商品名称')
    desc = models.CharField(max_length=256, verbose_name='商品简介')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='商品价格')
    unit = models.CharField(max_length=20, verbose_name='商品单位')
    image = models.ImageField(upload_to='goods', verbose_name='商品图片')
    stock = models.IntegerField(default=1, verbose_name='商品库存')
    sales = models.IntegerField(default=0, verbose_name='商品销量')
    status = models.SmallIntegerField(default=1, choices=STATUS_CHOICES, verbose_name='商品状态')

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'df_goods_sku'
        verbose_name = '商品sku'
        verbose_name_plural = verbose_name


class Goods(BaseModel):
    """商品SPU模型类"""
    name = models.CharField(max_length=20, verbose_name='商品SPU名称')
    detail = HTMLField(blank=True, verbose_name='商品详情')

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'df_goods'
        verbose_name = '商品spu'
        verbose_name_plural = verbose_name


class GoodsImage(BaseModel):
    """商品图片模型类"""
    sku = models.ForeignKey('GoodsSKU', verbose_name='商品', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='goods', verbose_name='图片路径')

    def __str__(self):
        return self.sku.name

    class Meta:
        db_table = 'df_goods_image'
        verbose_name = '商品图片'
        verbose_name_plural = verbose_name


class IndexGoodsBanner(BaseModel):
    """首页轮播商品展示模型"""
    sku = models.ForeignKey('GoodsSKU', verbose_name='商品', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='banner', verbose_name='图片')
    index = models.SmallIntegerField(default=0, verbose_name='展示顺序')

    def __str__(self):
        return self.sku.name

    class Meta:
        db_table = 'df_index_banner'
        verbose_name = '首页轮播商品'
        verbose_name_plural = verbose_name


class IndexPromotionBanner(BaseModel):
    """首页促销活动模型类"""
    name = models.CharField(max_length=20, verbose_name='活动名称')
    # url = models.URLField(verbose_name='活动链接') # 后台进行添加url的时候会验证是否为一个有效的url
    url = models.CharField(max_length=256, verbose_name='活动链接')
    image = models.ImageField(upload_to='banner', verbose_name='活动图片')
    index = models.SmallIntegerField(default=0, verbose_name='展示顺序')

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'df_index_promotion'
        verbose_name = '首页促销活动'
        verbose_name_plural = verbose_name


class IndexTypeGoodsBanner(BaseModel):
    """首页分类商品展示模型表"""
    DISPLAY_TYPE_CHOICES = (
        (0, '标题'),
        (1, '图片')
    )
    type = models.ForeignKey('GoodsType', verbose_name='商品名称', on_delete=models.CASCADE)
    sku = models.ForeignKey('GoodsSKU', verbose_name='商品sku', on_delete=models.CASCADE)
    index = models.SmallIntegerField(default=0, verbose_name='展示顺序')
    display_type = models.SmallIntegerField(default=1, choices=DISPLAY_TYPE_CHOICES, verbose_name='展示类型')

    def __str__(self):
        return self.type.name

    class Meta:
        db_table = 'df_index_type_goods'
        verbose_name = '首页分类展示商品'
        verbose_name_plural = verbose_name



