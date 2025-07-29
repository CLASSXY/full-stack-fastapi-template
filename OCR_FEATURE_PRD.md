# OCR功能需求文档 (PRD)

## 项目概述

### 当前技术栈
- **后端**: FastAPI + SQLModel + PostgreSQL + Alembic
- **前端**: React + TypeScript + Chakra UI + TanStack Router + Vite  
- **认证**: JWT Token
- **部署**: Docker Compose

### 现有功能
- 用户管理系统 (注册/登录/权限管理)
- Items管理 (CRUD操作)
- 分页列表展示
- 响应式前端界面

## 功能需求

### 1. 后端API接口开发

#### 1.1 OCR处理接口
**接口路径**: `POST /api/v1/ocr/process`

**输入参数**:
- `device_sn` (string): 设备序列号
- `image_file` (File): 待处理图片文件
- `use_angle_cls` (boolean, 可选): 是否使用文档方向分类，默认false
- `use_dilation` (boolean, 可选): 是否使用膨胀处理，默认false
- `language` (string, 可选): 识别语言，默认'ch' (中文)
- `confidence_thresh` (float, 可选): 文本识别置信度阈值(0-1)，默认0.5

**处理逻辑**:
1. 接收图片文件和设备SN及其他参数
2. 将原图上传到Cloudflare R2存储
3. 使用PaddleOCR Python SDK直接处理图片:
   ```python
   from paddleocr import PaddleOCR
   
   # 初始化OCR引擎
   ocr = PaddleOCR(
       use_angle_cls=use_angle_cls,
       lang=language,
       use_gpu=True if available else False,
       show_log=False
   )
   
   # 直接处理图片文件
   result = ocr.ocr(image_path, cls=use_angle_cls)
   ```
4. 解析OCR结果，提取文本内容和置信度
5. 生成可视化结果图片 (可选)
6. 将可视化结果图片上传到Cloudflare R2存储
7. 将OCR记录存储到数据库
8. 返回OCR识别结果

**输出结果**:
```json
{
  "id": "uuid",
  "device_sn": "string", 
  "ocr_text": "string",
  "ocr_confidence": 0.95,
  "original_image_url": "string",
  "result_image_url": "string",
  "scan_time": "datetime",
  "status": "success|failed|processing",
  "file_size": 1048576,
  "image_format": "jpg",
  "language": "ch",
  "detection_boxes": [
    {
      "text": "识别的文本",
      "confidence": 0.95,
      "box": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    }
  ]
}
```

#### 1.2 OCR结果查询接口
**接口路径**: `GET /api/v1/ocr/results`

**查询参数**:
- `skip` (int): 分页偏移量
- `limit` (int): 每页数量  
- `device_sn` (string, optional): 设备SN筛选

**输出结果**:
```json
{
  "data": [OCRRecord],
  "count": int
}
```

#### 1.3 OCR详情接口
**接口路径**: `GET /api/v1/ocr/results/{id}`

**输出结果**: 单个OCR记录详情

#### 1.4 OCR结果下载接口
**接口路径**: `GET /api/v1/ocr/download/{id}`

**功能**: 下载OCR结果文件

### 2. 数据库设计

#### 2.1 OCR记录表 (ocr_records)
```sql
CREATE TABLE ocr_records (
    id UUID PRIMARY KEY COMMENT 'OCR记录唯一标识',
    device_sn VARCHAR(255) NOT NULL COMMENT '设备序列号',
    original_image_url VARCHAR(500) NOT NULL COMMENT '原始图片R2存储URL',
    result_image_url VARCHAR(500) COMMENT 'OCR结果图片R2存储URL',
    ocr_text TEXT COMMENT 'OCR识别的文本内容',
    ocr_confidence FLOAT COMMENT 'OCR识别置信度(0-1)',
    language VARCHAR(20) DEFAULT 'ch' COMMENT '识别语言代码',
    detection_boxes JSON COMMENT 'OCR检测框和文本详细信息',
    processing_time FLOAT COMMENT 'OCR处理耗时(秒)',
    scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '扫描时间',
    status VARCHAR(50) DEFAULT 'processing' COMMENT '处理状态: processing/success/failed',
    error_message TEXT COMMENT '错误信息',
    file_size BIGINT COMMENT '原始文件大小(字节)',
    image_format VARCHAR(20) COMMENT '图片格式: jpg/png/bmp等',
    use_angle_cls BOOLEAN DEFAULT false COMMENT '是否使用文档方向分类',
    created_by UUID COMMENT '创建用户ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间'
) COMMENT='OCR识别记录表';
```

#### 2.2 索引设计
```sql
-- 设备SN索引 (用于设备筛选)
CREATE INDEX idx_ocr_records_device_sn ON ocr_records(device_sn);

-- 扫描时间索引 (用于时间排序)
CREATE INDEX idx_ocr_records_scan_time ON ocr_records(scan_time DESC);

-- 创建用户索引 (用于用户数据过滤)
CREATE INDEX idx_ocr_records_created_by ON ocr_records(created_by);

-- 状态索引 (用于状态筛选)
CREATE INDEX idx_ocr_records_status ON ocr_records(status);

-- 语言索引 (用于语言筛选)
CREATE INDEX idx_ocr_records_language ON ocr_records(language);

-- 复合索引 (用户+时间，常用查询组合)
CREATE INDEX idx_ocr_records_user_time ON ocr_records(created_by, scan_time DESC);

-- 复合索引 (设备+状态，常用查询组合)
CREATE INDEX idx_ocr_records_device_status ON ocr_records(device_sn, status);

-- OCR文本全文搜索索引 (PostgreSQL)
CREATE INDEX idx_ocr_records_text_search ON ocr_records USING gin(to_tsvector('chinese', ocr_text));
```

### 3. 前端界面开发

#### 3.1 侧边栏菜单扩展
在 `frontend/src/components/Common/SidebarItems.tsx` 中新增:
- 菜单项: "OCR结果管理"
- 图标: FiCamera 或 FiImage
- 路由: `/ocr-results`

#### 3.2 OCR结果管理页面 (`/ocr-results`)
**页面结构**:
```
OCR结果管理
├── 页面标题
├── 筛选区域 (可选)
│   └── 设备SN筛选
├── 分页列表
│   ├── 表格列:
│   │   ├── 设备SN
│   │   ├── 原图预览 (缩略图)
│   │   ├── 结果图预览 (缩略图)  
│   │   ├── 扫描时间
│   │   └── 操作 (查看详情/下载)
│   └── 分页控件
└── 空状态提示
```

**功能特性**:
- 响应式表格设计
- 图片缩略图预览
- 时间格式化显示
- 分页加载
- 状态指示器 (成功/失败/处理中)

#### 3.3 OCR详情页面 (`/ocr-results/{id}`)
**页面结构**:
```
OCR扫描详情
├── 返回按钮
├── 基本信息区域
│   ├── 设备SN
│   ├── 扫描时间  
│   ├── 文件大小
│   ├── 图片格式
│   └── 处理状态
├── 图片预览区域
│   ├── 原图预览 (支持放大)
│   └── 结果图预览 (支持放大)
├── OCR结果区域
│   ├── 识别文本
│   ├── 置信度
│   └── 复制按钮
└── 操作按钮
    ├── 下载原图
    ├── 下载结果图
    └── 下载OCR文本
```

**功能特性**:
- 图片灯箱预览
- 文本复制功能
- 文件下载功能
- 错误状态显示

### 4. 配置和依赖

#### 4.1 后端新增依赖
```toml
# pyproject.toml 新增
"paddlepaddle>=2.5.0",
"paddleocr>=2.7.0", 
"Pillow>=10.0.0",
"opencv-python>=4.8.0",
"numpy>=1.21.0",
"aiofiles>=23.0.0"
```

#### 4.2 环境配置
```env
# .env 新增配置项
# PaddleOCR配置
PADDLEOCR_USE_GPU=false  # 是否使用GPU加速
PADDLEOCR_DEFAULT_LANG=ch  # 默认识别语言
PADDLEOCR_MODEL_DIR=/app/paddleocr_models/  # 模型存储目录
PADDLEOCR_USE_ANGLE_CLS=false  # 是否使用文档方向分类
PADDLEOCR_MAX_WORKERS=2  # OCR处理并发数

# 文件处理配置
OCR_UPLOAD_PATH=/app/uploads/ocr/
OCR_MAX_FILE_SIZE=10485760  # 10MB
OCR_ALLOWED_FORMATS=jpg,jpeg,png,bmp

# Cloudflare R2存储配置
CLOUDFLARE_R2_ACCESS_KEY_ID=your_access_key_id
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your_secret_access_key
CLOUDFLARE_R2_ENDPOINT_URL=https://your_account_id.r2.cloudflarestorage.com
CLOUDFLARE_R2_BUCKET_NAME=ocr-storage
CLOUDFLARE_R2_PUBLIC_URL=https://your_custom_domain.com  # 可选：自定义域名
```

#### 4.3 Docker配置更新
```dockerfile
# Dockerfile 需要更新以支持PaddleOCR
FROM python:3.11-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 创建模型存储目录
RUN mkdir -p /app/paddleocr_models

# 设置PaddleOCR环境变量
ENV HUB_HOME=/app/paddleocr_models
```

#### 4.4 前端新增依赖
```json
// package.json 可能新增
"react-image-gallery": "^1.3.0",  // 图片预览组件
"react-window": "^1.8.8",         // 虚拟列表组件
"react-intersection-observer": "^9.5.2"  // 图片懒加载
```

### 5. 文件存储 (Cloudflare R2)

#### 5.1 存储桶结构
```
R2 Bucket: ocr-storage
├── original/     # 原始图片
│   └── {yyyy-mm-dd}/
│       └── {uuid}.{ext}
├── results/      # OCR结果图片  
│   └── {yyyy-mm-dd}/
│       └── {uuid}_result.{ext}
└── downloads/    # 临时下载文件
    └── {uuid}/
        └── ocr_result_{device_sn}_{timestamp}.txt
```

#### 5.2 文件命名规则
- 原图: `original/{yyyy-mm-dd}/{uuid}.{original_extension}`
- 结果图: `results/{yyyy-mm-dd}/{uuid}_result.{extension}`
- 下载文件: `downloads/{uuid}/ocr_result_{device_sn}_{timestamp}.txt`

#### 5.3 访问策略
- 图片文件通过公共URL或预签名URL访问
- 下载文件通过预签名URL访问（临时有效）
- 支持自定义域名访问（可选配置）

### 6. 权限控制

#### 6.1 接口权限
- 所有OCR接口需要用户登录
- 普通用户只能查看自己上传的记录
- 超级用户可以查看所有记录

#### 6.2 前端权限
- OCR菜单对所有登录用户可见
- 根据用户权限显示不同数据范围

### 7. 错误处理

#### 7.1 后端错误
- 文件格式不支持: 400 Bad Request
- 文件过大: 413 Payload Too Large  
- OCR API调用失败: 500 Internal Server Error
- 权限不足: 403 Forbidden

#### 7.2 前端错误
- 图片加载失败显示占位图
- API调用失败显示错误提示
- 网络异常时显示重试按钮

### 8. 性能考虑

#### 8.1 后端优化
- PaddleOCR模型预加载和复用
- 图片预处理和尺寸优化
- 异步OCR处理队列
- GPU加速支持 (如果可用)
- 模型缓存和版本管理
- OCR结果缓存

#### 8.2 PaddleOCR优化配置
```python
# OCR引擎配置优化
ocr_config = {
    'use_angle_cls': False,  # 根据需求开启文档方向分类
    'lang': 'ch',            # 根据主要使用语言设置
    'use_gpu': False,        # 根据服务器硬件配置
    'enable_mkldnn': True,   # CPU优化
    'cpu_threads': 4,        # CPU线程数
    'det_limit_side_len': 960,  # 检测模型输入尺寸
    'det_limit_type': 'max',    # 限制类型
}
```

#### 8.3 前端优化
- 图片懒加载
- 虚拟列表 (数据量大时)
- 缩略图生成
- 分页缓存

### 9. 开发计划

#### 阶段一 (后端开发)
1. 数据库模型设计和迁移
2. OCR API集成
3. 文件上传和存储逻辑
4. REST API接口开发

#### 阶段二 (前端开发)  
1. 菜单和路由配置
2. OCR结果列表页面
3. OCR详情页面
4. 图片预览组件

#### 阶段三 (集成测试)
1. 端到端功能测试
2. 性能测试和优化
3. 错误处理测试
4. 用户体验优化

### 10. 验收标准

#### 10.1 功能验收
- [ ] 用户可以通过API上传图片进行OCR
- [ ] OCR结果正确存储到数据库
- [ ] 前端列表页面正确显示OCR记录
- [ ] 详情页面图片和文本显示正常
- [ ] 下载功能正常工作
- [ ] 分页和筛选功能正常

#### 10.2 性能验收
- [ ] OCR处理时间 < 10秒 (CPU模式)
- [ ] OCR处理时间 < 5秒 (GPU模式，如果可用)
- [ ] 图片上传响应时间 < 5秒
- [ ] 列表页面加载时间 < 3秒
- [ ] 支持10MB以内图片文件
- [ ] 支持并发OCR处理 (最多2个并发任务)
- [ ] 内存使用控制在合理范围内

#### 10.3 OCR功能验收
- [ ] 支持中文、英文等多语言识别
- [ ] 文档方向分类功能正常 (可选)
- [ ] 置信度阈值过滤功能正常
- [ ] 检测框坐标信息准确
- [ ] 可视化结果图片生成正常
- [ ] OCR模型正确加载和初始化

#### 10.4 安全验收
- [ ] 文件类型和大小验证
- [ ] 用户权限控制正确
- [ ] 敏感信息不泄露
- [ ] 文件访问权限控制

---

## 附录

### 技术选型说明
- **PaddleOCR**: 基于飞桨的开源OCR解决方案，支持80+种语言识别，直接集成到后端代码中
- **本地部署**: 不依赖外部API服务，提高稳定性和响应速度
- **多语言支持**: 支持中文、英文、日文、韩文等多种语言
- **GPU加速**: 可选的GPU加速支持，提升处理性能
- **Cloudflare R2**: 高性能对象存储，兼容S3 API，全球CDN加速
- **SQLModel**: 与现有技术栈保持一致
- **Chakra UI**: 与现有前端组件库保持一致
- **TanStack Router**: 与现有路由方案保持一致

### 风险评估
- **模型文件大小**: PaddleOCR模型文件较大，需要考虑Docker镜像大小和下载时间
- **内存使用**: OCR处理需要较多内存，建议服务器至少4GB内存
- **CPU性能**: 不使用GPU时OCR处理速度较慢，建议使用多核CPU
- **并发处理**: 需要控制并发OCR处理数量，避免内存溢出
- **模型更新**: PaddleOCR模型版本更新时需要重新部署
- **Cloudflare R2成本**: 存储和流量成本需要监控，建议设置预算警报
- **图片存储管理**: 需要定期清理过期图片文件，避免存储成本过高
- **性能瓶颈**: 大文件处理可能影响性能，建议添加文件大小限制
- **用户体验**: 图片加载和预览的性能优化，特别是移动端体验 