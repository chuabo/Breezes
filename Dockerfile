#FROM registry.saintic.com/python
from qzkc/python2.7:v2

MAINTAINER chb <123141432@qq.com>

ADD src /Breezes

ADD misc/supervisord.conf /etc/supervisord.conf

ADD requirements.txt /tmp

WORKDIR /Breezes

RUN pip install --timeout 30 --index https://pypi.douban.com/simple/ -r /tmp/requirements.txt

EXPOSE 10210

ENTRYPOINT ["supervisord"]