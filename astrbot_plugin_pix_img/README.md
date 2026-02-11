# AstrBot PixImg 插件

一个用于AstrBot的随机Pixiv图片插件，调用自部署的API服务获取随机插画并发送给用户。

## 功能特性

- ✅ **API集成**: 调用自部署的Pixiv API获取随机插画
- ✅ **用户限制**: 按用户ID记录调用次数，基于时间窗口限制使用频率
- ✅ **自动下载**: 从API获取图片URL后自动下载到本地并发送
- ✅ **临时文件管理**: 图片发送后立即删除临时文件，插件卸载时清空临时目录
- ✅ **作品信息展示**: 显示作品标题、作者、Pixiv原始链接
- ✅ **线程安全**: 使用异步锁保护数据访问，避免并发问题

## 安装方法
市场安装
1. 从插件市场找到本插件，选择安装
手动安装
1. 将整个 `astrbot_plugin_pix_img` 目录放置到AstrBot的 `data/plugins/` 目录下
2. 重启AstrBot或在管理面板中重新加载插件
3. 在插件配置页面设置API地址

## 配置说明

插件提供以下可配置项（在管理面板的插件配置页面设置）：

| 配置项 | 类型 | 默认值 | 说明 |
|---------|------|---------|------|
| `api_url` | string | - | **必填**。获取随机图片的API地址（GET请求），例如：`http://localhost:3000/random` |
| `api_secret` | string | - | **可选**。API的Secret Key，会自动添加到请求头 `X-API-Key` 中用于鉴权 |
| `user_limit` | int | 5 | 每个用户在时间窗口内的最大调用次数 |
| `limit_window` | int | 3600 | 限制时间窗口长度（单位：秒），默认3600秒（1小时） |

### 使用限制

- 每个用户在时间窗口`limit_window`内（默认1分钟）最多调用 `user_limit` 次（默认5次）
- 超过时间窗口后，调用次数会自动重置
- 达到限制时会收到提示，需等待时间窗口过期后再次使用

## API要求

插件对接Pixiv 图片API：  
需提前部署好并采集图片 [PixCollector](https://github.com/AYui124/PixCollector)


## 数据存储

插件会在以下位置创建文件：

### 用户使用记录
- **路径**: `data/plugins_data/astrbot_plugin_pix_img/usage.json`
- **内容**: 记录每个用户的调用次数和时间戳
- **格式**:
```json
{
  "user_12345": {
    "timestamp": 1707556800,
    "count": 3
  }
}
```

### 临时文件
- **路径**: `data/plugins_data/astrbot_plugin_pix_img/temp/`
- **管理策略**: 
  - 图片发送成功后立即删除临时文件
  - 插件卸载时清空整个临时目录

## 支持

- 插件开发文档: https://docs.astrbot.app/dev/star/plugin-new.html

## 许可证

请参考项目根目录的 LICENSE 文件。

## 更新日志

### v1.0.0
- 初始版本发布
- 支持API调用和图片发送
- 支持用户调用次数限制
- 支持临时文件自动清理