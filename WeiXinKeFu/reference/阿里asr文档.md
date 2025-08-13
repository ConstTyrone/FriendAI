# Python SDK

更新时间：2025-01-06 13:49:18

我的appkey：NM5zdrGkIl8xqSzO

AccessToken: 9dadd6de5f8b458a852f45a2538bd602

[产品详情](https://ai.aliyun.com/nls)

[我的收藏](https://help.aliyun.com/my_favorites.html)

本文介绍如何使用智能语音交互一句话识别的Python SDK，包括SDK的安装方法及SDK代码示例等。

## 前提条件

- 在使用SDK前，请先阅读接口说明，详情请参见[接口说明](https://help.aliyun.com/zh/isi/developer-reference/api-reference-1#topic-1917909)。
- SDK仅支持Python3，暂不支持Python2。
- 已安装Python包管理工具setuptools。如果未安装，请在终端执行以下命令安装。

  ```python
  pip install setuptools
  ```

## 下载安装

**说明**

以下命令均需要在SDK根目录中执行。

1. 下载Python SDK。

   从[Github](https://github.com/aliyun/alibabacloud-nls-python-sdk)获取Python SDK，或直接下载[streamInputTts-github-python](https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20241203/tbjics/alibabacloud-nls-python-sdk-dev-20241203.zip)。
2. 安装SDK依赖。

   进入SDK根目录使用如下命令安装SDK依赖：

   ```python
   python -m pip install -r requirements.txt
   ```
3. 安装SDK。

   依赖安装完成后使用如下命令安装SDK：

   ```python
   python -m pip install .
   ```
4. 安装完成后通过以下代码导入SDK。

   ```python
   # -*- coding: utf-8 -*-
   import nls
   ```

## 多线程和多并发

在CPython中，由于存在[全局解释器锁](https://docs.python.org/zh-cn/3/glossary.html#term-global-interpreter-lock)，同一时刻只有一个线程可以执行Python代码（虽然某些性能导向的库可能会去除此限制）。如果您想更好地利用多核心计算机的计算资源，推荐您使用[multiprocessing](https://docs.python.org/zh-cn/3.11/library/multiprocessing.html#module-multiprocessing)或[concurrent.futures.ProcessPoolExecutor](https://docs.python.org/zh-cn/3.11/library/concurrent.futures.html#concurrent.futures.ProcessPoolExecutor)。 如果您想要同时运行多个I/O密集型任务，则多线程仍然是一个合适的模型。

如果单解释器有太多线程，将会在线程间切换造成更多消耗，有可能会导致SDK出现错误。不建议使用超过200线程，推荐使用[multiprocessing](https://docs.python.org/zh-cn/3.11/library/multiprocessing.html#module-multiprocessing)技术或者手动使用脚本创建多个解释器。

## 关键接口

一句话识别对应的类为**nls.NlsSpeechRecognizer**，其核心方法如下：

### 1. 初始化（__init__）

- 参数说明
  |  |  |  |
  | - | - | - |
  |  |  |  |

  | **参数**    | **类型** | **参数说明**                                                                                                                                                    |
  | ----------------- | -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
  | url               | String         | 网关WebSocket URL地址，默认为 `wss://nls-gateway-cn-shanghai.aliyuncs.com/ws/v1`。                                                                                  |
  | appkey            | String         | Appkey，获取方式请参见[管理项目](https://help.aliyun.com/zh/isi/getting-started/manage-projects)。                                                                       |
  | token             | String         | 访问Token，详情可参见[获取Token概述](https://help.aliyun.com/zh/isi/overview-of-obtaining-an-access-token#587dee8029x7r)。                                               |
  | on_start          | Function       | 当一句话识别就绪时的回调参数。回调参数包含以下两种：JSON形式的字符串用户自定义参数其中，用户自定义参数为下方**callback_args**字段中返回的参数内容。             |
  | on_result_changed | Function       | 当一句话识别返回中间结果时的回调参数。回调参数包含以下两种：JSON形式的字符串用户自定义参数其中，用户自定义参数为下方**callback_args**字段中返回的参数内容。     |
  | on_completed      | Function       | 当一句话识别返回最终识别结果时的回调参数。回调参数包含以下两种：JSON形式的字符串用户自定义参数其中，用户自定义参数为下方**callback_args**字段中返回的参数内容。 |
  | on_error          | Function       | 当SDK或云端出现错误时的回调参数。回调参数包含以下两种：JSON形式的字符串用户自定义参数其中，用户自定义参数为下方**callback_args**字段中返回的参数内容。          |
  | on_close          | Function       | 当和云端连接断开时的回调参数。回调参数为用户自定义参数，即用户自定义参数为下方**callback_args**字段中返回的参数内容。                                           |
  | callback_args     | List           | 用户自定义参数列表，列表中的内容会打包（pack）成List数据结构传递给各个回调的最后一个参数。                                                                            |
- 返回值：无

### 2. start

同步开始一句话识别，该方法会阻塞当前线程直到一句话识别就绪（**on_start**回调返回）。

- 参数说明
  |  |  |  |
  | - | - | - |
  |  |  |  |

  | **参数**                    | **类型** | **参数说明**                                                                                                                                                                                            |
  | --------------------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
  | aformat                           | String         | 要识别音频格式，支持PCM，OPUS，OPU，默认值：PCM。SDK不会自动将PCM编码成OPUS或OPU，如果需要使用OPUS或OPU，您可自行编码实现。                                                                                   |
  | sample_rate                       | Integer        | 识别音频采样率，默认值：16000 Hz。                                                                                                                                                                            |
  | ch                                | Integer        | 音频通道数，默认值：1，目前仅支持单通道。                                                                                                                                                                     |
  | enable_intermediate_result        | Boolean        | 是否返回中间结果，默认值：False。                                                                                                                                                                             |
  | enable_punctuation_prediction     | Boolean        | 是否进行识别结果标点预测，默认值：False。                                                                                                                                                                     |
  | enable_inverse_text_normalization | Boolean        | ITN（逆文本inverse text normalization）中文数字转换阿拉伯数字。设置为True时，中文数字将转为阿拉伯数字输出，默认值：False。                                                                                    |
  | timeout                           | Integer        | 阻塞超时，默认值：10秒。                                                                                                                                                                                      |
  | ping_interval                     | Integer        | Ping包发送间隔，默认值：8秒。无需间隔可设置为0或None。                                                                                                                                                        |
  | ping_timeout                      | Integer        | 设置ping包超时时间，默认为0，即不检查ping包超时。如果设置为x>0，则ping包发出后x秒未收到ping包则报错超时。单位：秒。                                                                                           |
  | ex                                | Dict           | 用户提供的额外参数，该字典内容会以 `key:value`形式合并进请求的payload段中，具体可参见[2.开始识别](https://help.aliyun.com/zh/isi/developer-reference/api-reference-1#sectiondiv-yq4-576-gfd)章节中的请求数据。 |
- 返回值：Boolean类型，False为失败，True为成功。

### 3. stop

停止一句话识别，并同步等待**on_completed**回调结束。

- 参数说明
  |  |  |  |
  | - | - | - |
  |  |  |  |

  | **参数** | **类型** | **参数说明**       |
  | -------------- | -------------- | ------------------------ |
  | timeout        | Integer        | 阻塞超时，默认值：10秒。 |
- 返回值：Boolean类型，False为失败，True为成功。

### 4. shutdown

强行关闭当前请求，重复调用无副作用。

- 参数说明：无
- 返回值：无

### 5. send_audio

发送二进制音频数据，发送数据的格式需要和[start](https://help.aliyun.com/zh/isi/developer-reference/sdk-for-python?spm=a2c4g.11186623.0.i3#sectiondiv-971-l0a-puc)中的**aformat**对应。

- 参数说明
  |  |  |  |
  | - | - | - |
  |  |  |  |

  | **参数** | **类型** | **参数说明**                                                                                                                               |
  | -------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
  | pcm_data       | Bytes          | 要发送的二进制音频数据，格式需要和上一次调用时start中的aformat相对应。SDK不会自动将PCM编码成OPUS或OPU，如果需要使用OPUS或OPU，您可自行编码实现。 |
- 返回值：Boolean类型，False为失败，True为成功。

## 代码示例

**说明**

- 本示例中使用的音频文件为16000 Hz采样率，PCM格式，您可以使用*tests*文件夹下的test1.pcm，请在智能语音交互管控台将Appkey对应项目的模型设置为**通用**模型，以获取准确的识别结果；如果使用其他音频，请设置为支持该音频场景的模型。关于模型设置，请参见[管理项目](https://help.aliyun.com/zh/isi/getting-started/manage-projects#topic-1917901)。
- 本示例中使用SDK内置的默认外网访问服务端URL，如果您使用阿里云上海地域的ECS，并需要通过内网访问服务端URL，请使用如下URL：`URL="ws://nls-gateway-cn-shanghai-internal.aliyuncs.com/ws/v1"`。

```python
import time
import threading
import sys

import nls


URL="wss://nls-gateway-cn-shanghai.aliyuncs.com/ws/v1"
TOKEN="yourToken"   #参考https://help.aliyun.com/document_detail/450255.html获取token
APPKEY="yourAppkey"      #获取Appkey请前往控制台：https://nls-portal.console.aliyun.com/applist

#以下代码会根据音频文件内容反复进行一句话识别
class TestSr:
    def __init__(self, tid, test_file):
        self.__th = threading.Thread(target=self.__test_run)
        self.__id = tid
        self.__test_file = test_file
   
    def loadfile(self, filename):
        with open(filename, "rb") as f:
            self.__data = f.read()
  
    def start(self):
        self.loadfile(self.__test_file)
        self.__th.start()

    def test_on_start(self, message, *args):
        print("test_on_start:{}".format(message))

    def test_on_error(self, message, *args):
        print("on_error args=>{}".format(args))

    def test_on_close(self, *args):
        print("on_close: args=>{}".format(args))

    def test_on_result_chg(self, message, *args):
        print("test_on_chg:{}".format(message))

    def test_on_completed(self, message, *args):
        print("on_completed:args=>{} message=>{}".format(args, message))


    def __test_run(self):
        print("thread:{} start..".format(self.__id))
      
        sr = nls.NlsSpeechRecognizer(
                    url=URL,
                    token=TOKEN,
                    appkey=APPKEY,
                    on_start=self.test_on_start,
                    on_result_changed=self.test_on_result_chg,
                    on_completed=self.test_on_completed,
                    on_error=self.test_on_error,
                    on_close=self.test_on_close,
                    callback_args=[self.__id]
                )

        print("{}: session start".format(self.__id))
        r = sr.start(aformat="pcm", ex={"hello":123})
          
        self.__slices = zip(*(iter(self.__data),) * 640)
        for i in self.__slices:
            sr.send_audio(bytes(i))
            time.sleep(0.01)

        r = sr.stop()
        print("{}: sr stopped:{}".format(self.__id, r))
        time.sleep(1)

def multiruntest(num=500):
    for i in range(0, num):
        name = "thread" + str(i)
        t = TestSr(name, "tests/test1.pcm")
        t.start()

# 设置打开日志输出
nls.enableTrace(False)
multiruntest(1)
```
