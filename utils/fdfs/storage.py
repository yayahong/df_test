from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client
from django.conf import settings

class FDFSStorage(Storage):
    """FastDFS文件存储类"""
    def __init__(self, fdfs_client_conf=None, fdfs_nginx_url=None):
        """初始化"""

        if fdfs_client_conf is None:
            fdfs_client_conf = settings.FDFS_CLIENT_CONF
        if fdfs_nginx_url is None:
            fdfs_nginx_url = settings.FDFS_NGINX_URL

        self.fdfs_client_conf = fdfs_client_conf
        self.fdfs_nginx_url = fdfs_nginx_url

    def _open(self, name, mode='rb'):
        """打开文件时使用"""
        pass

    def _save(self, name, content):
        """保存文件时使用"""
        # name:所选择的上传文件的名字
        # content:所选择的包含上传文件内容的File对象

        # 创建一个fdfs_client对象
        fdfs_client = Fdfs_client(self.fdfs_client_conf)

        # 上传文件:通过文件内容上传文件
        res = fdfs_client.upload_by_buffer(content.read())

        """return dict {
            'Group name'      : group_name,
            'Remote file_id'  : remote_file_id,
            'Status'          : 'Upload successed.',
            'Local file name' : '',
            'Uploaded size'   : upload_size,
            'Storage IP'      : storage_ip
        } if success else None
        """


        if res.get('Status') != 'Upload successed.':
            # 文件上传失败,抛出异常
            raise Exception('文件上传失败')

        # 文件上传成功
        # 获取上传文件成功后返回的文件id
        filename = res.get('Remote file_id')
        # 返回文件id
        return filename

    def exists(self, name):
        """Django判断所上传的文件名是否可用"""
        return False

    def url(self, name):
        """返回访问文件的url"""
        return self.fdfs_nginx_url+name