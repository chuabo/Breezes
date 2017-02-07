# -*- coding: utf8 -*-

import os.path, json, requests
from utils.public import logger


class BASE_REGISTRY_API:


    def __init__(self, timeout=2, verify=False):
        self.timeout  = timeout
        self.verify   = verify

    def _checkStatus(self, url, version=1):
        """ 返回私有仓状态 """

        try:
            url = url.strip("/") + "/v1/_ping" if version == 1 else url.strip("/") + "/v2/"
            req = requests.head(url, timeout=self.timeout, verify=self.verify)
        except Exception,e:
            logger.error(e, exc_info=True)
        else:
            logger.info(req.status_code)
            return req.ok
        return False

class MultiRegistryManager(BASE_REGISTRY_API):

    def __init__(self, timeout=2, verify=False):
        self.timeout = timeout
        self.verify  = verify        
        self._BASE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._dir0   = os.path.join(self._BASE, 'logs', ".Registries.db")
        self._dir1   = os.path.join(self._BASE, 'logs', ".ActiveRegistry.db")
        self._registries  = self._unpickle
        self._active      = self._unpickleActive

    def _pickle(self, data):
        """ 序列化所有数据写入存储 """
        try:
            with open(self._dir0, "w") as f:
                json.dump(data, f)
        except Exception,e:
            logger.error(e, exc_info=True)
            res = False
        else:
            res = True

        logger.info("pickle registries data, content is %s, write result is %s" %(data, res))
        return res

    @property
    def _unpickle(self):
        """ 反序列化信息取出所有数据 """
        try:
            with open(self._dir0, "r") as f:
                    data = json.load(f)
        except Exception,e:
            logger.warn(e, exc_info=True)
            res = []
        else:
            res = data or []

        logger.info("unpickle registries data is %s" %res)
        return res

    def _pickleActive(self, data):
        """ 序列化活跃仓库数据写入存储 """
        try:
            with open(self._dir1, "w") as f:
                json.dump(data, f)
        except Exception,e:
            logger.error(e, exc_info=True)
            res = False
        else:
            res = True

        logger.info("pickle active data, content is %s, write result is %s" %(data, res))
        return res

    @property
    def _unpickleActive(self):
        """ 反序列化信息取出活跃仓库 """
        try:
            with open(self._dir1, "r") as f:
                data = json.load(f)
        except Exception,e:
            logger.warn(e, exc_info=True)
            res = {}
        else:
            res = data or {}

        logger.info("unpickle active data is %s" %res)
        return res

    @property
    def getMember(self):
        """ 查询所有仓库名称 """
        return [ _.get("name") for _ in self._registries ]

    def isMember(self, name):
        """ 查询某name的仓库是否在存储中 """
        return name in self.getMember

    def getOne(self, name):
        """ 查询某name的仓库信息 """

        if self.isMember(name):
            return ( _ for _ in self._registries if _.get("name") == name ).next()
        else:
            logger.warn("no such registry named {}, return an empty dict".format(name))
            return {}

    @property
    def getActive(self):
        """ 查询活跃仓库 """
        return self._active

    def isActive(self, name):
        """ 判断某name的仓库是否为活跃仓库 """
        return name == self.getActive.get("name")

    def setActive(self, name):
        """ 设置活跃仓库 """
        logger.info("setActive, request name that will set is %s" % name)

        if self.isActive(name):
            logger.info("The name of the request is already active, think it successfully")
        else:
            logger.info("The name of the request is not current active registry, will update it to be active.")
            self._active = self.getOne(name)
            self._pickleActive(self._active)
            if self.isActive(name):
                logger.info("setActive, the request name sets it for active, successfully")
            else:
                logger.info("setActive, the request name sets it for active, but fail")
                return False
        return True

    def getRegistries(self):
        """ 查询所有仓库信息 """
        return self._registries

    def GET(self, query, state=False):
        """ 查询 """

        res = {"msg": None, "code": 0}
        logger.info("GET: the query params is {}".format(query))

        if not isinstance(query, (str, unicode)) or not query:
            res.update(msg="GET: query params type error or none", code=10000)
        else:
            query = query.lower()
            if query == "all":
                res.update(data=self.getRegistries())
            elif query == "active":
                res.update(data=self.getActive)
            elif query == "member":
                res.update(data=self.getMember)
            else:
                if self.isMember(query):
                    res.update(data=self.getOne(query))
                else:
                    res.update(msg="No such registry", code=10001)

        logger.info(res)
        return res

    def POST(self, name, addr, version=1, auth=None):
        """ 创建 """

        res  = {"msg": None, "code": 0}
        try:
            version = int(version)
        except Exception,e:
            logger.error(e, exc_info=True)
            res.update(msg="params error", code=-10002)
            logger.info(res)
            return res
        else:
            logger.info("post a registry, name is %s, addr is %s, version is %s" %(name, addr, version))

        if not name or not addr:
            res.update(msg="params error", code=10002)
        elif not "http://" in addr and not "https://" in addr:
            res.update(msg="addr params error, must be a qualified URL(include protocol)", code=10003)
        elif self.isMember(name):
            res.update(msg="registry already exists", code=10004)
        else:
            self._registries.append(dict(name=name, addr=addr, version=version, auth=auth))
            self._pickle(self._registries)
            res.update(success=True, code=0)
            logger.info("check all pass and added")

        logger.info(res)
        return res

    def DELETE(self, name):
        """ 删除当前存储中的私有仓 """

        res = {"msg": None, "code": 0, "success": False}
        logger.info("the name that will delete is %s" %name)

        if name in ("member", "active", "all"):
            res.update(msg="name reserved for the system key words", code=10005)

        elif self.isActive(name):
            res.update(msg="not allowed to delete the active cluster", code=10006)

        elif self.isMember(name):
            registry = self.getOne(name)
            logger.info("Will delete registry is %s" %registry)
            self._registries.remove(registry)
            if self.isMember(name):
                logger.info("Delete fail")
                res.update(success=False)
            else:
                logger.info("Delete successfully, pickle current registries")
                self._pickle(self._registries)
                res.update(success=True)

        else:
            res.update(msg="This registry does not exist", code=10007)

        logger.info(res)
        return res

    def PUT(self, name, setActive=False):
        """ 设置活跃仓库 """

        res = {"msg": None, "code": 0}
        logger.info("PUT request, setActive(%s), will set %s as active" %(setActive, name))

        if setActive:
            if name and self.isMember(name):
                res.update(success=self.setActive(name))
            else:
                res.update(msg="setActive, but no name param or name non-existent", code=10008)
        else:
            pass

        logger.info(res)
        return res

class ApiRegistryManager:


    def __init__(self, timeout=2, verify=False):
        self.timeout = timeout
        self.verify  = verify
        #Base Registry info
        self._url  = Registry["RegistryAddr"]
        self._ver  = Registry["RegistryVersion"]
        self._auth = Registry["RegistryAuthentication"]
        #Instantiation the registry
        self._baseUrl = SpliceURL.Modify(self._url, path="/v1").geturl if int(self._ver) == 1 else SpliceURL.Modify(self._url, path="/v2").geturl
        logger.info("Registry API Init, registry is {}, status is {}, _baseUrl is {}".format(self._url, self.status, self._baseUrl))

    @property
    def url(self):
        """ 返回私有仓地址 """
        return self._url

    @property
    def version(self):
        """ 返回私有仓版本 """
        return self._ver

    @property
    def status(self):
        """ 返回私有仓状态 """

        try:
            code = requests.head(self._baseUrl + "/_ping", timeout=self.timeout, verify=self.verify).status_code
        except Exception,e:
            logger.error(e, exc_info=True)
        else:
            if code == 200:
                return True
        return False

    def _search_all_repository(self, q):
        """ 搜索私有仓所有镜像 """

        ReqUrl = self._baseUrl + "/search"
        logger.info("_search_all_repository for url {}".format(ReqUrl))
        try:
            Images = requests.get(ReqUrl, timeout=self.timeout, verify=self.verify, params={"q": q}).json()
        except Exception,e:
            logger.error(e, exc_info=True)
            return False
        else:
            return Images["results"]

    @property
    def _list_all_repository(self):
        """ 列出私有仓所有镜像名称 """

        return self._search_all_repository(q="")

    def _list_repository_tag(self, ImageName):
        """ 列出某个镜像所有标签 """

        ReqUrl = self._baseUrl + "/repositories/{}/tags".format(ImageName)
        logger.info("_list_repository_tag for url {}".format(ReqUrl))
        try:
            Tags = requests.get(ReqUrl, timeout=self.timeout, verify=self.verify).json()
        except Exception,e:
            logger.error(e, exc_info=True)
            return False
        else:
            return Tags

    def _get_imageId(self, ImageName, tag="latest"):
        """ 查询某个镜像tag的imageId """

        ReqUrl = self._baseUrl + "/repositories/{}/tags/{}".format(ImageName, tag)
        logger.info("_get_imageId for url {}".format(ReqUrl))
        try:
            ImageId = requests.get(ReqUrl, timeout=self.timeout, verify=self.verify).json()
        except Exception,e:
            logger.error(e, exc_info=True)
            return False
        else:
            return ImageId

    def _delete_repository_tag(self, ImageName, tag):
        """ 删除一个镜像的某个标签 """

        ReqUrl = self._baseUrl + "/repositories/{}/tags/{}".format(ImageName, tag)
        logger.info("_delete_repository_tag for url {}".format(ReqUrl))
        try:
            delete_repo_result = requests.delete(ReqUrl, timeout=self.timeout, verify=self.verify).json()
        except Exception,e:
            logger.error(e, exc_info=True)
            return False
        else:
            return delete_repo_result

    def _delete_repository(self, ImageName):
        """ 删除一个镜像 """

        ReqUrl = self._baseUrl + "/repositories/{}/".format(ImageName)
        logger.info("_delete_repository for url {}".format(ReqUrl))
        try:
            delete_repo_result = requests.delete(ReqUrl, timeout=self.timeout, verify=self.verify).json()
        except Exception,e:
            logger.error(e, exc_info=True)
            return False
        else:
            return delete_repo_result

    def _list_imageId_ancestry(self, ImageId):
        """ 列出某个镜像所有父镜像 """

        ReqUrl = self._baseUrl + "/images/{}/ancestry".format(ImageId)
        logger.info("_list_imageId_ancestry for url {}".format(ReqUrl))
        try:
            ImageIds = requests.get(ReqUrl, timeout=self.timeout, verify=self.verify).json()
        except Exception,e:
            logger.error(e, exc_info=True)
            return False
        else:
            return ImageIds

    def _get_imageId_info(self, ImageId):
        """ 查询某个镜像的信息 """

        ReqUrl = self._baseUrl + "/images/{}/json".format(ImageId)
        logger.info("_get_imageId_info for url {}".format(ReqUrl))
        try:
            ImageInfo = requests.get(ReqUrl, timeout=self.timeout, verify=self.verify).json()
        except Exception,e:
            logger.error(e, exc_info=True)
            return False
        else:
            return ImageInfo

