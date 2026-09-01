知学AI — 项目问题与解决方案记录

一、开发环境问题

1.1 TypeScript 构建错误

问题描述：前端 Docker 构建时出现多个 TypeScript 错误，导致 npm run build 失败。

错误列表：
src/views/CourseDetail.vue: Property 'content' does not exist on type 'MessageHandler'
src/views/HomeworkPage.vue: Object literal may only specify known properties, and 'homework_id' does not exist in type
src/views/TeacherDashboard.vue: Type 'number | null' is not assignable to type 'null'

解决方案：

1. MessageHandler.content 不存在 — Element Plus 的 ElMessage.info() 返回的 MessageHandler 对象没有 content 属性。不能直接修改已显示的消息内容。改为关闭旧消息并创建新消息：
   // 修改前
   toast.content = `正在排队... ${elapsed}s`
   // 修改后
   toast.close()
   toast = ElMessage.info(`正在排队... ${elapsed}s`)
   同时将 const toast 改为 let toast 以支持重新赋值。

2. homework_id 类型不匹配 — 新老两套 AI API 的参数不同。旧版用 homework_id，新版用 question。HomeworkPage.vue 使用了新版 gradeHomework API：
   // 修改前 传递了旧版参数
   grade.value = await gradeHomework({ homework_id: 1, student_answer: answer.value })
   // 修改后 使用新版参数
   const question = '请说明机器学习中过拟合的原因和解决办法。'
   grade.value = await gradeHomework({ question, student_answer: answer.value })

3. price 类型推断为 null — Vue ref 初始化时 price: null 被 TypeScript 推断为 null 类型而非 number | null：
   // 修改前 price 类型为 null
   const form = ref({ title: '', ..., price: null, ... })
   // 修改后 显式声明联合类型
   const form = ref({ title: '', ..., price: null as number | null, ... })

经验教训：使用 TypeScript 的 ref 初始化时，如果预期会有多种类型的值，务必使用类型断言或显式泛型。


1.2 异步上下文中的数据库会话问题

问题描述：在后台任务（如秒杀异步处理）中，SQLAlchemy 异步会话在首次 await 后报 Instance <Model> is not bound to a Session 错误。

解决方案：在异步任务函数内部创建独立的数据库会话，避免跨协程共享会话：

  # 正确做法 — 每个异步任务使用独立会话
  async def seckill_consumer():
      while True:
          async with AsyncSessionLocal() as db:
              # 处理任务
              await db.commit()


二、功能问题

2.1 秒杀课程主页显示不全

问题描述：HomePage 秒杀专区只显示了 4 门秒杀课程，但实际上有 8 门。

根因：前端代码中使用 .slice(0, 4) 限制了显示数量。

解决方案：移除切片限制，显示所有有效秒杀课程。同时添加以下优化：

1. 15 秒自动刷新：setInterval 定时重新加载秒杀数据
2. 到期自动隐藏：每 1 秒检查活动是否过期，过期实时隐藏
3. 动态倒计时：每个秒杀卡片单独显示倒计时
4. 库存百分比进度条：直观展示剩余库存比例
5. N+1 查询优化：后端 attach_seckill_bulk() 一次性查询所有课程的秒杀信息，避免逐条查询

  # 优化后 — 批量查询秒杀信息
  async def attach_seckill_bulk(db, courses):
      course_ids = [c.id for c in courses]
      result = await db.execute(
          select(SeckillActivity)
          .options(selectinload(SeckillActivity.sku))
          .join(CourseSKU, CourseSKU.id == SeckillActivity.sku_id)
          .where(CourseSKU.course_id.in_(course_ids), ...)
      )
      # 构建 course_id 到 seckill 的映射
      seckill_map = {}
      for act in result.scalars().all():
          cid = act.sku.course_id
          if cid not in seckill_map:
              seckill_map[cid] = act


2.2 游客可以直接观看课程视频

问题描述：未登录/未购买的游客可以直接通过课程详情页访问视频播放页面。

解决方案：在 CourseDetail.vue 添加购买状态判断：

  <button v-if="isPurchased" @click="startLearning">开始学习</button>
  <button v-else @click="buyNow">
    {{ isFree ? '加入课程' : '立即购买' }}
  </button>

并在 CourseLearning.vue 页面加载时校验用户是否有观看权限：
- 已购买用户：完整播放权限
- 未购买用户：仅限免费试看课程，显示"试看"标记


2.3 秒杀结束后仍显示在列表中

问题描述：秒杀活动结束时间已过，课程仍然显示在秒杀专区。

解决方案：前端每 1 秒执行过期过滤 + 后端返回时已过滤过期活动：

  // 每秒更新的倒计时逻辑中加入过期检查
  const now = Date.now()
  seckillItems.value = rawData.filter(item => {
    const end = new Date(item.end_time).getTime()
    return end > now
  })


2.4 管理员订单页缺少用户名

问题描述：管理员查看订单列表时，所有订单都显示相同的用户信息，无法区分。

解决方案：在 OrderOut schema 中添加 user_id 和 username 字段，后台查询时使用 selectinload(Order.user) 预加载关联用户：

  # OrderOut schema 新增字段
  class OrderOut(BaseModel):
      user_id: int | None = None
      username: str | None = None
  # 查询时预加载用户关联
  stmt = select(Order).options(selectinload(Order.items), selectinload(Order.user))


2.5 免费课程显示"立即购买"

问题描述：免费课程（价格 0 元）在详情页按钮显示"立即购买"，容易造成混淆。

解决方案：判断课程 SKU 价格是否为 0，如果是免费课程则：

  <button class="pc-btn pc-btn-primary" @click="buyNow">
    <span class="material-symbols-outlined">{{ isFree ? 'library_add' : 'shopping_cart' }}</span>
    {{ isFree ? '加入课程' : '立即购买' }}
  </button>
  <button v-if="!isFree" class="pc-btn pc-btn-ghost" @click="addToCart">加入购物车</button>


三、部署问题

3.1 Docker 镜像下载超时（中国网络环境）

问题描述：在阿里云 ECS（Ubuntu）上执行 docker compose up 时，从 Docker Hub 拉取镜像极其缓慢或超时。

解决方案：经过了多次尝试：

1. 尝试 Docker 镜像加速器（修改 /etc/docker/daemon.json）：
   - docker.1ms.run → 部分层拉取失败
   - docker.xuanyuan.me → 不稳定
   - registry.cn-hangzhou.aliyuncs.com → 需要同步配置
   - 最终可用 docker.m.daocloud.io → 稳定可用

2. Dockerfile 使用国内镜像源：
   # npm (前端)
   RUN npm config set registry https://registry.npmmirror.com
   # pip (后端)
   ENV PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
   ENV PIP_TRUSTED_HOST=mirrors.aliyun.com
   # apt (后端)
   RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list

经验教训：在中国服务器部署时，一定要提前配置好所有国内镜像源，否则构建过程将极其缓慢。推荐使用 DaoCloud 镜像加速器 + 各语言包管理器的国内镜像组合。


3.2 Docker 未安装/版本问题

问题描述：新服务器上 Docker 未安装，且 yum 命令在 Ubuntu 上不可用。

解决方案：使用 apt 安装（对应 Ubuntu 系统）而非 yum：

  # 使用 Aliyun 镜像源的安装方式
  apt install -y docker.io docker-compose
  # 而非 curl 安装方式（在中国可能被墙）
  # curl -fsSL https://get.docker.com | bash


3.3 前端容器运行开发服务器而非生产模式

问题描述：部署后访问 http://47.113.221.92:8080 无法打开页面。检查发现前端容器运行的 Vite 开发服务器（端口 5173）而非 Nginx（端口 80）。

根因：docker compose up -d 自动合并了 docker-compose.override.yml，该覆写文件将前端配置为开发模式：
- 使用 Dockerfile.dev（而非 Dockerfile）
- 运行 npm run dev -- --host 0.0.0.0（而非 nginx）
- 端口映射 5173:5173（而非 8080:80）

解决方案：
1. 修改 deploy.sh 明确指定生产配置文件：
   # 修改前 会自动合并 override
   docker-compose up --build -d
   # 修改后 只使用生产配置
   docker-compose -f docker-compose.yml up --build -d
2. 临时测试可访问 http://47.113.221.92:5173


3.4 MySQL 密码不匹配

问题描述：后端提示 Access denied for user 'knowai'@'172.18.0.7'。

解决方案（多次迭代）：

1. 首次修复 — 删除 MySQL 数据卷重新初始化：
   docker volume rm knowai_mysql_data

2. 根本原因 — docker-compose.yml 中 MySQL 环境变量使用了 shell 变量替换 ${MYSQL_PASSWORD:-knowai_pass}，但 docker-compose 从 .env 文件读取变量进行替换，而非 .env.docker。服务器上缺少 .env 文件，导致使用了默认值。

   最终解决：将 .env.docker 复制为 .env：
   cp .env.docker .env

经验教训：docker-compose 的变量替换机制复杂：
- ${VAR:-default} 替换从 shell 环境变量或 .env 文件读取
- env_file 配置是将变量传入容器，不参与 compose 文件的变量替换
- 生产部署时需要确保 .env 文件存在


3.5 安全组端口未开放

问题描述：所有容器正常运行，但无法通过浏览器访问网站。

解决方案：在阿里云控制台配置安全组规则：

1. 登录阿里云 ECS 控制台
2. 找到实例 → 安全组
3. 添加入方向规则：
   - 端口范围：8080/8080
   - 授权对象：0.0.0.0/0
   - 优先级：1

同样需要放行的端口：8000（后端 API，按需开放）、443（HTTPS）、80（HTTP）


3.6 容器构建内存不足导致 SSH 卡死

问题描述：在低配 ECS 上执行 docker-compose build frontend 时，服务器内存耗尽，SSH 完全卡死。

解决方案：
1. 阿里云控制台强制重启 ECS
2. 使用 docker-compose up -d（不传 --build）直接使用已有镜像
3. 如果必须重新构建，增加 ECS 内存或使用 SWAP


四、API 密钥管理问题

4.1 敏感信息被 .gitignore 排除

问题描述：AI 功能、短信等 API 密钥配置在 .env 文件中，但 .env 被 .gitignore 排除，推送到 Gitee/GitHub 时丢失。服务器上的 .env.docker 中密钥为空。

解决方案：
1. 将 .env.docker.example 作为模板保留在版本控制中
2. 在服务器上手动填写 .env.docker 和 .env
3. 通过 SSH 执行 sed 命令批量替换配置值：
   sed -i 's|^OPENAI_API_KEY=.*|OPENAI_API_KEY=your_key|' .env.docker

经验教训：对于多环境部署，建议使用 CI/CD 的密钥管理功能或 Docker Secrets，而非手动管理服务器上的配置文件。


4.2 验证码 Mock 模式在 Docker 中不可见

问题描述：本地开发时 SMS_MOCK=true 将验证码打印到控制台，开发者在终端可见。但在 Docker 生产环境下，控制台日志无法被普通用户查看。

解决方案：修改后端返回验证码到前端：

  # auth.py — send-code 和 send-login-code 端点
  resp = {"message": "验证码已发送"}
  if settings.sms_mock:
      resp["mock_code"] = code  # 将验证码返回前端
  return resp

同时更新前端 API 类型定义，在前端展示 mock 验证码：

  // auth.ts
  export function sendCode(data: { target: string }) {
    return request.post<unknown, { message: string; mock_code?: string }>('/auth/send-code', data)
  }
  // LoginPage.vue — 显示验证码
  if (result.mock_code) {
    ElMessage.success(`验证码已发送至 ${target}（测试验证码：${result.mock_code}）`)
  }


五、总结与最佳实践

5.1 开发流程建议

1. 本地 TypeScript 校验：在提交前运行 npm run build 确保无 TS 错误
2. Docker 构建测试：本地先执行 docker compose build 验证 Dockerfile 正确性
3. 敏感信息分离：密钥不提交到版本控制，使用 CI/CD Secrets 或 Docker Secrets

5.2 部署清单

1. 服务器环境准备（Docker、Docker Compose）
2. Docker 镜像加速器配置（中国服务器必须）
3. .env 和 .env.docker 配置（核对所有密钥）
4. 安全组端口开放
5. 数据卷创建
6. 使用 -f docker-compose.yml 避免合并开发配置
7. 运行种子数据脚本初始化演示数据

5.3 故障恢复流程

1. SSH 连接不上 → 阿里云控制台强制重启
2. 502 Bad Gateway → docker logs knowai_backend 查看后端日志
3. 前端白屏 → docker logs knowai_frontend 查看 nginx 日志
4. 数据库错误 → 检查 MySQL/MongoDB/Redis 容器状态
5. AI 功能异常 → 检查 API 密钥和 SiliconFlow/OpenAI 可用性
