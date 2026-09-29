# 测试说明

本项目用 [Playwright](https://playwright.dev/) 做端到端测试，覆盖 TodoMVC 的核心交互：
新增、完成状态切换、编辑、删除、过滤器、Clear completed，共 30 个用例。

这 30 个用例有 **JavaScript 和 Python 两个等价实现**，跑任意一个即可：

| 实现 | 用例文件 | 跑法 | 本机耗时 |
| --- | --- | --- | --- |
| JavaScript | `tests/todo.spec.js` | `npm test` | 5.6–7s |
| Python | `tests_py/test_todo.py` | `python -m pytest` | 8.6–13.3s |

耗时会随 `demo.playwright.dev` 的网络状况波动，上表是本地多次实测的区间，不是单次结果。

两者都跑在官方的线上 Demo 站点 `https://demo.playwright.dev/todomvc/` 上，**不需要本地起服务**，
但需要能访问外网（见下方「常见问题 › 网络 / 代理」）。

---

## JavaScript 版

### 前置条件

- Node.js 18 及以上（Playwright 1.63 的要求）
- 首次使用需要安装依赖和浏览器内核：

```bash
npm install
npx playwright install chromium
```

`npx playwright install chromium` 只装 chromium，因为 `playwright.config.js` 里目前只配置了 chromium 一个 project。
若之后新增了 firefox / webkit 的 project，用 `npx playwright install` 装全部内核。

### 跑测试

```bash
# 跑全部用例（等价于 npx playwright test）
npm test

# 只跑某个文件
npx playwright test tests/todo.spec.js

# 按用例名过滤（支持正则）
npx playwright test -g "过滤器"

# 只跑某一个用例，按行号定位
npx playwright test tests/todo.spec.js:352

# 打开有头浏览器，观察真实操作过程
npx playwright test --headed

# UI 模式：可视化列表 + 时间旅行回放，调试时最顺手
npx playwright test --ui

# 单步调试（会打开 Playwright Inspector）
npx playwright test --debug
```

`playwright.config.js` 里设置了 `fullyParallel: true`，用例之间并行执行，
整个套件在本机 5.6–7 秒跑完（受网络波动影响）。

---

## Python 版

测试逻辑与 JS 版一一对应，`tests/todo.spec.js` 顶部那段 check()/click() 的项目知识
同样适用于 Python 版，已原样搬到 `tests_py/test_todo.py` 的模块 docstring 里。

### 前置条件

- Python 3.13（实测 3.13.7）
- **必须用 `python`，不要用 `python3`**，原因见「常见问题 › 7」
- Python 依赖：

```bash
python -m pip install playwright pytest pytest-playwright pytest-xdist
```

| 包 | 实测版本 | 作用 |
| --- | --- | --- |
| `playwright` | 1.63.0 | Python 版 Playwright |
| `pytest` | 8.4.2 | 测试框架 |
| `pytest-playwright` | 0.9.0 | 提供 `page` / `expect` fixture |
| `pytest-xdist` | 3.8.0 | 并行跑用例（对应 JS 端的 `fullyParallel`） |

- 浏览器内核：

```bash
python -m playwright install chromium
```

**本机已经装过，通常不需要再跑。** JS 端是 `@playwright/test@1.63.0`，Python 端是
`playwright 1.63.0`，版本号一致，两边共用 `%LOCALAPPDATA%\ms-playwright\chromium-1243`
这一份内核。只有 firefox / webkit 没装，而两边的配置都只用 chromium。

### 跑测试

`pytest.ini` 里写了 `testpaths = tests_py`，所以在仓库根目录直接跑 `python -m pytest`
只会收集 Python 版用例，不会去碰 JS 套件。

```bash
# 跑全部 30 个用例（等价于 python -m pytest -n 4）
python -m pytest

# 只跑某个文件
python -m pytest tests_py/test_todo.py

# 按类名 / 用例名过滤
python -m pytest -k "TestFilters"
python -m pytest -k "filter and reload"

# 串行 + 详细输出，调试时读 traceback 更清楚
python -m pytest -n 0 -v

# 打开有头浏览器，观察真实操作过程
python -m pytest --headed

# 放慢每个操作，肉眼跟得上
python -m pytest --headed --slowmo 500

# 录 trace，失败后回放
python -m pytest --tracing on
python -m playwright show-trace test-results/<目录>/trace.zip
```

可用的 Playwright 相关命令行参数（由 `pytest-playwright` 提供）：
`--browser`、`--browser-channel`、`--device`、`--headed`、`--slowmo`、`--output`、
`--tracing`、`--video`、`--screenshot`、`--full-page-screenshot`、`--playwright-debug`。

### 并行度调优

`pytest.ini` 的默认值是 `-n 4`，**刻意不用 `-n auto`**。实测数据（30 个用例，
Windows 11 / 16 核 / chromium-1243，各取三次里最快的一次）：

| 并行方式 | 耗时 |
| --- | --- |
| `-n auto`（16 worker） | 14.1s |
| `-n 4` | **9.0s** |
| `-n 0`（串行） | 26.4s |

注意这只比的是**同一台机器上的相对快慢**，绝对值受网络波动影响明显：`-n 4` 多次跑
实测在 8.6s ~ 13.3s 之间浮动。所以结论是「4 个 worker 优于开满」，而不是「一定 9 秒」。

瓶颈不是用例数量，而是**每个 xdist worker 都要冷启一个 chromium**。16 个 worker
各自付一遍浏览器启动开销，并行收益被吃掉大半；4 个刚好把启动开销和并行度平衡掉。
换一台核数不同的机器，最优值会变，可以自己扫一遍：

```bash
for n in 2 4 6 8; do echo "n=$n"; python -m pytest -n $n -q; done
```

---

## 环境变量

两个实现读取的环境变量不完全一样。

**JS 版**（`playwright.config.js`）会读：

| 变量 | 作用 | 说明 |
| --- | --- | --- |
| `CI` | 任意非空值即视为 CI 环境 | 开启后 `forbidOnly` 生效（禁止提交 `test.only`），失败重试次数从 0 提升到 2 |
| `HTTP_PROXY` / `HTTPS_PROXY` | 走代理访问外网 | 四个大小写变体都会被读取（`HTTP_PROXY`、`HTTPS_PROXY`、`http_proxy`、`https_proxy`），命中后自动注入到 `use.proxy` |

**Python 版**（`tests_py/conftest.py`）只读代理，两个差异要注意：

- `HTTP_PROXY` / `HTTPS_PROXY` 四个大小写变体同样都认，但 **playwright-python 本身
  不会读环境变量走代理**，是 conftest 里的 `browser_context_args` fixture 显式注入到
  `new_context()` 的。如果自己新写 context，得手动传 `proxy`，否则会直连。
- `CI` 在 Python 端**没有对应行为**：没有 `forbidOnly`、也没有自动重试的等价配置。

此外 Playwright 本身还认一些官方变量，两个实现通用：

| 变量 | 作用 |
| --- | --- |
| `DEBUG=pw:api` | 打印每个 Playwright API 调用及其耗时，排查「卡在哪一步」很有效 |
| `PLAYWRIGHT_BROWSERS_PATH` | 指定浏览器内核的安装目录（默认在用户目录下，CI 上常配合缓存使用） |
| `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1` | 安装依赖时跳过浏览器下载，适合已有缓存镜像的环境 |

不同 shell 的设置方式：

```bash
# bash / Git Bash
CI=1 npm test
HTTPS_PROXY=http://127.0.0.1:7890 npm test
DEBUG=pw:api python -m pytest

HTTPS_PROXY=http://127.0.0.1:7890 python -m pytest
```

```powershell
# PowerShell
$env:CI = "1"; npm test
$env:HTTPS_PROXY = "http://127.0.0.1:7890"; npm test
$env:HTTPS_PROXY = "http://127.0.0.1:7890"; python -m pytest
```

```cmd
:: cmd.exe
set CI=1 && npm test
```

## 测试产物

- 失败时的 trace：JS 版配置为 `trace: 'on-first-retry'`，即**只在重试时**录制。
  本地默认 `retries: 0`，不重试也就不会产生 trace；想拿到 trace 可以跑
  `npx playwright test --retries=1`，或用 `--trace on` 强制每次都录。
  Python 版默认不录，需要时显式加 `--tracing on`（或 `--tracing retain-on-failure`）。
- 产物落在 `test-results/` 目录，这个目录已在 `.gitignore` 里忽略，不要提交。
- pytest 自己的缓存目录 `.pytest_cache/` 同样已忽略。
- 想生成 HTML 报告：

```bash
# JS
npx playwright test --reporter=html
npx playwright show-report

# Python
python -m pytest --html=report.html
```

## 常见问题

### 1. 报错 `Executable doesn't exist at ...` / `browserType.launch: Executable not found`

浏览器内核没装，或者装的内核版本和当前 Playwright 对不上（升级过依赖后容易出现）。

```bash
npx playwright install chromium        # JS
python -m playwright install chromium  # Python
```

### 2. 所有用例都超时，报 `page.goto: net::ERR_...` / 一直卡在打开页面

测试要访问线上站点，网络不通是最常见的原因。按顺序排查：

1. 本机能否直接打开 `https://demo.playwright.dev/todomvc/`；
2. 如果必须走代理，设置 `HTTPS_PROXY`（注意大小写变体都行）后重跑；
3. 代理只对部分流量生效时，确认 `demo.playwright.dev` 在直连白名单里。

Python 版多一个排查点：代理变量是靠 `tests_py/conftest.py` 的 fixture 注入的，
确认自己没绕开它新建 context（见「环境变量」一节）。

### 3. `page.goto('/')` 打开的页面不对（仅 JS 版）

`playwright.config.js` 里的 `baseURL` 是 `https://demo.playwright.dev/todomvc/`，**带路径**。
按 URL 解析规则，以 `/` 开头会从域名根开始拼接，`page.goto('/')` 实际会跑到
`https://demo.playwright.dev/`，于是所有选择器都找不到元素。

**用例里请用 `page.goto('./')`。**

Python 版不存在这个问题：`tests_py/conftest.py` 里的 `todo_page` fixture 直接用绝对
地址 `BASE_URL`，站点地址全项目只有一处定义。

### 4. `check()` 一直重试到超时（而不是快速失败）

这是本项目踩过的坑，具体场景写在 `tests/todo.spec.js` 顶部注释里。

`check()` / `uncheck()` 点击之后还会回读并断言元素处于目标状态。如果这次操作会让元素
立刻从 DOM 中消失（例如 Active 视图下勾选完成，该条被过滤掉），那个「已勾选」的状态
永远不会出现，`check()` 就会一直重试到超时，报错信息还只指向 `check` 本身，容易误导。

判断标准：**操作之后元素是否还在页面上**。

- 还在 → 用 `check()` / `uncheck()`，语义更强；
- 会被移除 → 改用 `click()`，再用业务结果（条目数量、列表内容）做断言。

Python 版的 `locator.check()` 行为完全一致，同一个坑同样存在
（`tests_py/test_todo.py` 里的 `test_completing_item_in_active_view_removes_it`）。

### 5. 用例偶发失败（flaky）

先确认不是上面的第 2 条（网络抖动会让整批用例一起挂）。若只是个别用例偶发，
用 `--repeat-each=10` 反复跑定位：

```bash
npx playwright test -g "过滤器" --repeat-each=10
```

Python 版没有内置重复跑的参数，装 `pytest-repeat` 后用 `--count=10`，或者直接
`for i in 1 2 3; do python -m pytest -k TestFilters; done`。

本地拿到 trace 后用 `npx playwright show-trace test-results/<目录>/trace.zip` 回放，能看到
每一步的 DOM 快照，比读日志快得多。

### 6. 提交前忘了去掉 `test.only`（仅 JS 版）

CI 上 `forbidOnly` 会直接让整个流程失败，避免只跑了一个用例却以为全绿。
本地想模拟这个检查，`CI=1 npm test` 即可。Python 端没有这个机制，
`pytest.ini` 里也没有配 `--strict-markers` 之类的护栏，靠自觉。

### 7. `No module named playwright`（Python 版）

本机有**两个 Python**，装依赖的是哪一个很关键：

| 命令 | 实际解释器 | 装没装 playwright |
| --- | --- | --- |
| `python` | `C:\Users\Hannah\AppData\Local\Programs\Python\Python313\python.exe`（3.13.7） | ✅ 装了 |
| `python3` | `C:\Users\Hannah\AppData\Local\Microsoft\WindowsApps\python3.exe`（微软商店版 3.13.14） | ❌ 没装 |

所以跑测试一律写 `python -m pytest`。想确认当前用的是哪个解释器：

```bash
python -c "import sys; print(sys.executable)"
```

## 目录结构

```
playwright.config.js     # JS 测试配置：baseURL、并行、重试、代理、chromium project
tests/
  todo.spec.js           # JS 版 30 个用例 + 定位/操作辅助函数

pytest.ini               # Python 测试配置：testpaths、并行 worker 数（-n 4）
tests_py/
  conftest.py            # Python 版共享配置：BASE_URL、代理、todo_page fixture
  test_todo.py           # Python 版 30 个用例 + 定位/操作辅助函数

test-results/            # Playwright 运行产物（已 gitignore）
.pytest_cache/           # pytest 运行产物（已 gitignore）
```
