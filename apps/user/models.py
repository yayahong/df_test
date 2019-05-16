from django.db import models
from django.contrib.auth.models import AbstractUser
from db.base_model import BaseModel


# Create your models here.
class User(AbstractUser, BaseModel):
    """用户模型类"""
    # django 中有抽象用户模型，可直接继承来用

    # ACTIVATE_CHOICES = (
    #     (0, '未激活')，
    #     (1, '已激活')
    # )
    # username = models.CharField(max_length=20, verbose_name='用户名')
    # password = models.CharField(max_length=20, verbose_name='密码')
    # email = models.CharField(max_length=30, verbose_name='邮箱')
    # is_active = models.SmallIntegerField(default=0, choices=ACTIVATE_CHOICES, verbose_name='激活标记')

    class Meta:
        db_table = 'df_user'
        verbose_name = '用户'
        verbose_name_plural = verbose_name


class AddressManager(models.Manager):
    """地址模型管理器类"""
    # 1.改变原有查询的结果集:all()
    # 2.封装方法：用户操作模型类对应的数据表（增删改查）
    def get_default_addr(self, user):
        """获取当前/默认地址数据"""
        # self.model 获取self对象所在的模型类
        try:
            address = self.get(user=user, is_default=True)
        except self.model.DoesNotExist:
            # 没有默认地址
            address = None
        return address
    # Address.objects.get_default_addr()


class Address(BaseModel):
    """地址模型类"""
    receiver = models.CharField(max_length=20, verbose_name='收件人')
    addr = models.CharField(max_length=256, verbose_name='收件地址')
    zip_code = models.CharField(max_length=6, null=True, verbose_name='邮政编码')# 邮政编码为6位，可以为空
    phone = models.CharField(max_length=11, verbose_name='联系电话')# 联系电话为11位
    is_default = models.BooleanField(default=False, verbose_name='是否默认')# 默认值是不默认
    user = models.ForeignKey('User', verbose_name='所属账户', on_delete=models.CASCADE)

    # 自定义一个模型管理器类的对象
    objects = AddressManager()

    class Meta:
        db_table = 'df_address'
        verbose_name = '地址'
        verbose_name_plural = verbose_name








