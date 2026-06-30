# YouTube 下载 `geo_verification_proxy` 支持

## 背景

某些 YouTube 视频存在地区限制（region-restricted）：只有来自特定地区 IP 的请求才能通过播放校验（playability check）并取得带 `streamingData` 的播放器响应。同时，PO Token 由 YouTube 按请求来源 IP 签发，若获取 PO Token 的请求与播放器请求来自不同 IP，YouTube 可能拒绝该 Token，导致下载失败。

yt-dlp 原生提供了 `geo_verification_proxy` 选项（见 `yt_dlp/extractor/common.py` 中的 `geo_verification_headers()`），其机制是：当设置了该代理时，在请求头中附带 `Ytdl-request-proxy`，让 YouTube 通过该"干净地区"代理验证地理位置，而后续真实下载流量仍可走全局 `--proxy`。

然而上游 YouTube 提取器在多个关键请求点并未挂载 `geo_verification_headers()`，因此该选项对 YouTube 实际不生效。本项目补全了这一支持。

## 改动内容

本次改动在 YouTube 提取器的三个关键请求点上接入 `geo_verification_proxy`，使地区校验流量与真实下载流量分离：

### 1. 播放器 API 请求（`_extract_player_response`）

文件：`yt_dlp/extractor/youtube/_video.py`

在向 Innertube `player` 端点发起请求前，合并 `geo_verification_headers()`。该请求负责 playability/region 校验并返回 `streamingData`，是地区限制的核心校验点。

```python
# Route the player API request (playability/region check & streamingData) through
# geo_verification_proxy when set, so region-restricted videos can be verified via a
# "clean" region IP while the actual download still uses the global --proxy. See
# yt_dlp/extractor/common.py:geo_verification_headers for the header mechanism.
headers.update(self.geo_verification_headers())
```

### 2. PO Token 获取请求（`_fetch_po_token`）

文件：`yt_dlp/extractor/youtube/_video.py`

为 PO Token 请求选择 `request_proxy` 时，优先使用 `geo_verification_proxy`，确保 PO Token 与上方的播放器 API 请求来自同一 IP，避免 YouTube 因 IP 不一致而拒绝 Token。

```python
request_proxy=(
    # Prefer geo_verification_proxy so the PO Token is issued from the same IP
    # as the player API request above; otherwise YouTube may reject the token.
    self.get_param('geo_verification_proxy')
    or select_proxy('https://www.youtube.com', proxies)
    or select_proxy(f'https://{innertube_host}', proxies)
),
```

### 3. 观看页 / 初始网页请求（`_download_initial_webpage`）

文件：`yt_dlp/extractor/youtube/_video.py`

下载观看页（含其中内嵌的初始播放器响应）时同样挂载 `geo_verification_headers()`，与播放器 API 请求保持一致。

```python
headers={
    **traverse_obj(self._get_default_ytcfg(webpage_client), {
        'User-Agent': ('INNERTUBE_CONTEXT', 'client', 'userAgent', {str}),
    }),
    # Verify the watch page (and its embedded initial player response) via
    # geo_verification_proxy when set; consistent with the player API request.
    **self.geo_verification_headers(),
},
```

## 使用方法

通过 `--geo-verification-proxy` 指定一个位于目标地区（无封锁、可正常访问 YouTube）的代理：

```bash
yt-dlp \
  --proxy "http://全局下载代理:端口" \
  --geo-verification-proxy "http://地区校验代理:端口" \
  "https://www.youtube.com/watch?v=VIDEO_ID"
```

行为说明：

- **`--geo-verification-proxy`**：仅用于地理位置校验请求（观看页、播放器 API、PO Token）。应选择目标地区的"干净"代理。
- **`--proxy`**：用于实际视频分片下载流量，可与校验代理不同。

## 设计要点

- **流量分离**：地区校验走 `geo_verification_proxy`，实际下载走 `--proxy`，避免校验代理承担下载带宽，也避免下载代理的 IP 被 YouTube 视作校验来源。
- **IP 一致性**：播放器 API 请求与 PO Token 请求使用同一校验代理出口 IP，防止 Token 因来源 IP 不匹配被拒。
- **零侵入回退**：未设置 `geo_verification_proxy` 时，`geo_verification_headers()` 返回空字典、`get_param` 返回 `None`，行为与上游完全一致，不影响普通用户。

## 相关代码位置

- `yt_dlp/extractor/youtube/_video.py` — `_extract_player_response`、`_fetch_po_token`、`_download_initial_webpage`
- `yt_dlp/extractor/common.py:3969` — `geo_verification_headers()`（底层实现）
