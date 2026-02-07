# UI 开发规范 - ImGui Tailwind 风格设计系统

## ⚠️ 重要：本项目使用 Tailwind 风格的样式系统

本项目已经实现了类似 Tailwind CSS 的 ImGui 样式系统。**禁止**硬编码样式值。

## 📐 ImGui vs CSS 布局模型 - 必读

**ImGui 不是 CSS！** 在写代码前必须理解以下概念差异：

### 容器层级与间距来源

```
┌─────────────────────────────────────────────────────────────┐
│ Window / Child (由 begin_child 创建)                         │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │← WindowPadding →                     ← WindowPadding →│ │
│ │                                                         │ │
│ │  ┌─────────────────┐                                   │ │
│ │  │ Frame (按钮/输入框)│ ← FramePadding 是控件内部间距    │ │
│ │  └─────────────────┘                                   │ │
│ │          ↕ ItemSpacing.y (元素之间的垂直间距)            │ │
│ │  ┌─────────────────┐                                   │ │
│ │  │ Frame            │                                   │ │
│ │  └─────────────────┘                                   │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### CSS vs ImGui 间距对照表

| CSS 概念 | ImGui 概念 | tw/ly 映射 | 作用对象 |
|----------|------------|------------|----------|
| `padding` (容器内边距) | `WindowPadding` | `tw.p_*` | Child 窗口、弹窗 |
| `padding` (控件内边距) | `FramePadding` | `tw.frame_p_*` | 按钮、输入框内部 |
| `gap` (flex/grid 间距) | `ItemSpacing` | `ly.hstack(gap=N)` | 相邻元素之间 |
| `margin` | **不存在** | `ly.gap_y(N)` | 需手动插入 dummy |
| `border-radius` | `FrameRounding` / `ChildRounding` | `tw.rounded_*` | Frame/Child |

### ⚠️ Padding 设计 (重要)

```python
# tw.p_* 只设置 WindowPadding (容器内边距)
# tw.frame_p_* 设置 FramePadding (控件内边距)

# ✅ 容器 padding - 用 p_*
with tw.p_4:
    ly.card("my_card"):     # Card (Child) 内部 padding = 16px
        imgui.text("内容")

# ✅ 控件 padding 通常由 btn_* 预设内置
if (tw.btn_primary | tw.btn_md)(imgui.button)("确定"):
    ...

# ⚠️ 需要手动控制控件 padding 时 (罕见)
with tw.frame_p_2:
    imgui.button("自定义 padding")
```

### 容器类型速查

| 容器 | 创建方式 | 有自己的 Padding? | 有自己的背景? | 用途 |
|------|----------|-------------------|---------------|------|
| **Window** | `begin()` | ✅ WindowPadding | ✅ | 顶层窗口 |
| **Child** | `begin_child()` / `ly.card()` | ✅ WindowPadding | ✅ 可选 | 滚动区域、卡片 |
| **Group** | `begin_group()` / `ly.hstack()` | ❌ | ❌ | 仅逻辑分组 |
| **Table** | `begin_table()` / `ly.grid()` | ✅ CellPadding | ❌ | 多列布局 |

### 嵌套容器的间距叠加

```python
# ⚠️ 间距会叠加！
with tw.p_4:                    # 外层：WindowPadding = 16px
    with ly.card("card"):       # ly.card 是 begin_child
        with tw.p_2:            # 内层：再加 WindowPadding = 8px
            imgui.text("嵌套")  # 实际距离外边 = 16 + 8 = 24px
```

### 正确的容器使用模式

```python
# ✅ 正确：样式放在容器外部，控制容器本身
with tw.bg_abyss_800 | tw.rounded_lg | tw.p_3:
    with ly.card("my_card", height=20):
        # 这里的内容会有 12px 的内边距
        imgui.text("内容")

# ❌ 错误：样式放在容器内部，无法影响容器
with ly.card("my_card", height=20):
    with tw.bg_abyss_800 | tw.p_3:  # 太晚了！card 已经创建
        imgui.text("内容")

# ✅ 理解 Group vs Child
with ly.hstack(gap=2):          # hstack 用 Group，无 padding
    with ly.slot():
        imgui.button("A")       # 按钮之间间距 = gap
    with ly.slot():
        imgui.button("B")

with ly.scroll_y(height=50):    # scroll_y 用 Child，有 padding
    # 内容距离边缘有 WindowPadding (如果设置了 tw.p_*)
    for item in items:
        imgui.text(item)
```

## 🧠 UI 设计思路 - 先想 Tailwind，再写 ImGui

设计新 UI 时，请按以下步骤思考：

### 1. 先用 Tailwind 思维设计

假设你在写 React + Tailwind，这个组件会怎么写？

```jsx
// 例：项目信息表单
<div className="flex flex-col gap-4">
  {/* 路径提示 */}
  <div className="bg-slate-800 rounded-md px-3 py-2 flex items-center gap-2">
    <FolderIcon className="text-stone-500" />
    <span className="text-stone-300">{path}</span>
  </div>

  {/* 2列表单 */}
  <div className="grid grid-cols-2 gap-4">
    <div className="flex flex-col gap-0.5">
      <label className="text-stone-400 text-sm">名称</label>
      <input className="bg-slate-900 border border-slate-600 rounded-md p-2" />
    </div>
    ...
  </div>
</div>
```

### 2. 映射到我们的系统

| Tailwind | 我们的系统 |
|----------|------------|
| `flex flex-col gap-4` | `with ly.vstack(gap=4):` |
| `flex items-center gap-2` | `with ly.hstack(gap=2):` |
| `grid grid-cols-2 gap-4` | `with ly.grid(cols=2, gap=4):` |
| `bg-slate-800` | `tw.bg_abyss_800` |
| `rounded-md` | `tw.rounded_md` |
| `p-3` | `tw.p_3` |
| `text-stone-400` | `tw.text_parchment_500` |
| `border border-slate-600` | `tw.border_abyss_600 \| tw.frame_border_size(1)` |
| `overflow-y-auto h-48` | `with ly.scroll_y(height=48):` |
| `w-60` | `with ly.fixed_width(60):` |

### 3. 在代码注释中记录映射

```python
def _draw_path_bar():
    """路径提示条

    Tailwind: bg-slate-800 rounded-md px-3 py-2 flex items-center gap-2
    """
    with ly.hstack(gap=2):
        ...
```

这样做的好处：
- 设计意图清晰，便于 review
- 后续修改时知道原始设计
- 新人可以通过 Tailwind 文档理解布局

## � 关键文件

| 文件 | 用途 | 备注 |
|------|------|------|
| `ui/tw.py` | Tailwind 风格预设 tokens | **主要使用此文件** |
| `ui/layout.py` | 布局 helpers | 间距、居中、按钮等 |
| `ui/styles.py` | 底层构建函数 | 仅在扩展时使用 |
| `ui/theme.py` | **主题色定义** | crystal/goldrim/abyss/parchment/blood |
| `codegen/generate_tailwind_tokens.py` | tw.py 生成器 | **添加新 token 必须修改此文件** |

## ⚠️ 添加新 Token 的正确方式

**禁止**直接编辑 `ui/tw.py`！它是自动生成的文件。

```bash
# 1. 修改 codegen/generate_tailwind_tokens.py
# 2. 运行生成器
python codegen/generate_tailwind_tokens.py
```

## �📦 核心导入

```python
from ui import tw        # Tailwind 风格预设 tokens
from ui import layout as ly  # 布局 helpers
from ui import styles    # 底层构建函数 (仅在创建新 token 时使用)
```

## 🎨 样式使用规范

### ⭐ 推荐：函数调用式（精确控制，无扩散）

```python
# 🎯 最佳实践：样式精确绑定到单个函数调用
tw.text_parchment_100(imgui.text)("Hello")

# 组合多个样式
(tw.bg_abyss_800 | tw.rounded_lg | tw.p_3)(imgui.begin_child)("panel", 0, 200)
imgui.text("内容不受上面样式影响")
imgui.end_child()

# 按钮样式 + 尺寸（推荐写法）
(tw.btn_primary | tw.btn_md)(imgui.button)("确定")

# 保存为 styled 组件复用
primary_btn = tw.btn_primary | tw.btn_md
if primary_btn(imgui.button)("确定"):
    save()
if primary_btn(imgui.button)("应用"):
    apply()
```

### ⚠️ Context Manager（限定场景）

仅用于"多个元素确实需要相同样式"的场景：

```python
# ✅ 合理：一组相关文字
with tw.text_muted:
    imgui.text("提示行 1")
    imgui.text("提示行 2")
    imgui.text("提示行 3")

# ❌ 危险：可能意外影响其他元素
with tw.text_blood_500:
    imgui.text("错误信息")
    imgui.button("确定")  # 按钮文字也变红了！可能非预期
```

### ❌ 禁止 Context Manager 的 Token

以下 token 只能用函数调用式，使用 `with` 会抛出 `RuntimeError`：

```python
# 尺寸类 token
tw.w_*    # 宽度
tw.h_*    # 高度
tw.btn_xs / btn_sm / btn_md / btn_lg / btn_xl  # 按钮尺寸预设

# ❌ 这会报错
with tw.w_40:
    imgui.button("确定")

# ✅ 正确用法
(tw.w_40 | tw.h_9)(imgui.button)("确定")
```

### ❌ 禁止的做法

```python
# ❌ 硬编码颜色值
imgui.push_style_color(imgui.COLOR_TEXT, 0.9, 0.9, 0.9, 1.0)

# ❌ 使用 styles.py 底层函数重新实现 tw.py 已有的 token
with styles.text((0.9, 0.9, 0.9, 1.0)):  # 应该用 tw.text_gray_200
    ...

# ❌ 硬编码间距
imgui.set_cursor_pos_y(imgui.get_cursor_pos_y() + 16)  # 应该用 ly.gap_y(4)

# ❌ 硬编码尺寸
imgui.button("OK", width=160, height=36)  # 应该用 (tw.btn_* | tw.btn_md)(imgui.button)("OK")
```

## 📐 布局使用规范

### 间距 - 使用 ly.gap_y / ly.gap_x

```python
# ✅ 正确
ly.gap_y(4)  # 16px 垂直间距
ly.gap_x(2)  # 8px 水平间距 (在 same_line 后)

# ❌ 禁止
imgui.dummy(0, 16)
imgui.set_cursor_pos_y(imgui.get_cursor_pos_y() + 16)
```

### 居中 - 使用自动布局

```python
# ✅ 自动水平居中 (不需要计算宽度)
with ly.auto_hcenter():
    (tw.btn_primary | tw.btn_md)(imgui.button)("Button A")
    imgui.same_line()
    (tw.btn_secondary | tw.btn_md)(imgui.button)("Button B")

# ✅ 完全居中
with ly.auto_center():
    imgui.text("Centered content")
```

### 按钮 - 样式 + 尺寸组合

```python
# ✅ 推荐 - 样式和尺寸都是 token
if (tw.btn_primary | tw.btn_md)(imgui.button)("确定"):
    do_something()

# 预设尺寸:
# btn_xs = 96px × 28px
# btn_sm = 128px × 32px
# btn_md = 160px × 36px (常用)
# btn_lg = 192px × 40px
# btn_xl = 224px × 44px

# 自定义尺寸
if (tw.btn_primary | tw.w_60 | tw.h_12)(imgui.button)("大按钮"):
    ...

# 保存为预设复用
danger_btn = tw.btn_danger | tw.btn_md
if danger_btn(imgui.button)("删除"):
    delete()

# ❌ 废弃的用法 (ly.btn 将被废弃)
if ly.btn("确定", 40, 9):
    ...
```

## 🔧 高阶函数用法 (@ 装饰器)

样式可以用 `@` 运算符创建样式化函数：

```python
# 创建样式化组件
styled_button = tw.btn_primary @ ly.btn

# 使用
if styled_button("确定", 40, 9):
    ...

# 等价于
with tw.btn_primary:
    if ly.btn("确定", 40, 9):
        ...
```

## 🎨 主题色参考

本项目使用 **暗黑2 + 紫水晶** 风格 (详见 `ui/theme.py`)：

| 语义名 | Token | 用途 | Hex (代表色) |
|--------|-------|------|-----|
| 紫水晶 Crystal | `tw.btn_crystal` / `tw.text_crystal_*` | 冷饱和紫，主按钮/强调 | #9a79dd |
| 金边 Goldrim | `tw.text_goldrim_*` | 暗黑2经典金色，次强调/警告 | #d1a22e |
| 深渊 Abyss | `tw.bg_abyss_*` | 冷蓝紫中性暗色背景 | #1e1c2b |
| 羊皮纸 Parchment | `tw.text_parchment_*` | 温暖米黄色文字 | #e7ddca |
| 血红 Blood | `tw.text_blood_*` / `tw.btn_danger` | 危险/错误 | #c92821 |
| 岩石 Stone | `tw.border_stone_*` | 中性暖灰，边框/分隔线 | #44403c |

语义别名：
- `tw.btn_primary` = `tw.btn_crystal`
- `tw.btn_secondary` = `tw.btn_abyss`
- 文字层级: `tw.text_bright` / `text_default` / `text_muted` / `text_subtle` / `text_faint`
- 强调文字: `tw.text_accent` = `tw.text_crystal_400`
- 背景层级: `tw.bg_app` / `bg_surface` / `bg_elevated` / `bg_input`
- 语义边框: `tw.border_subtle` / `border_default` / `border_strong` / `border_interactive`

## ⚡ Preflight 注意事项

本项目使用 `apply_preflight()` 清空了 ImGui 默认样式。这意味着：
- **必须**显式设置所有需要的样式（颜色、间距、圆角等）
- 不要假设任何默认样式存在
- 像写 Tailwind CSS 一样，需要完整声明样式

## 📝 添加新 Helper 的原则

如果需要新的样式或布局 helper：

1. **原子化** - 每个 helper 只做一件事
2. **正交化** - 不同 helper 之间不重叠
3. **可组合** - 使用 `|` 运算符组合
4. **DPI 感知** - 使用 `dpi_scale()` 处理缩放

```python
# ✅ 好的 helper - 原子化
def scroll_area_y(height: float) -> StyleContext:
    """垂直滚动区域高度"""
    return StyleContext(...)

# ❌ 坏的 helper - 做太多事情
def fancy_card_with_title_and_border():  # 这是 widget，不是 helper
    ...
```

## 🔍 快速参考

### tw.py 常用 tokens

- 文字: `tw.text_{color}_{shade}` (例: `tw.text_parchment_200`)
- 背景: `tw.bg_{color}_{shade}` (例: `tw.bg_abyss_800`)
- 输入框背景: `tw.frame_bg_{color}_{shade}` (例: `tw.frame_bg_abyss_800`)
- 边框: `tw.border_{color}_{shade}`
- 内边距: `tw.p_0` ~ `tw.p_16` (p_1 = 4px)
- 圆角: `tw.rounded_none/sm/md/lg/xl/2xl/full`
- 按钮: `tw.btn_primary/secondary/danger/success`
- 按钮尺寸: `tw.btn_xs/sm/md/lg/xl` (btn_md = 160×36px)
- 宽度: `tw.w_0` ~ `tw.w_96` (w_40 = 160px) **禁止 CM**
- 高度: `tw.h_0` ~ `tw.h_96` (h_9 = 36px) **禁止 CM**
- 颜色常量: `tw.ABYSS_700` 等 (用于 `list_item` 等需要 tuple 的场景)
- 控件内边距: `tw.frame_p_0` ~ `tw.frame_p_16` (罕用，btn_* 已内置)

### layout.py 常用函数

#### 基础布局
- `ly.gap_y(n)` / `ly.gap_x(n)` - 间距
- `ly.btn(label, w, h)` - 按钮
- `ly.same_line(gap)` - 同行
- `ly.sz(n)` - Tailwind 单位转像素 (n * 4 * dpi_scale)

#### 自动居中
- `ly.auto_hcenter()` / `ly.auto_vcenter()` / `ly.auto_center()` - 自动居中
- `ly.text_center(text)` / `ly.text_right(text)` - 对齐文本

#### Flex 布局
```python
# 推荐方式 - 使用 slot() 包装每个子元素
with ly.hstack(gap=2):
    with ly.slot():
        imgui.text("左")
    ly.spacer()  # 弹性空间，推后续元素到右侧
    with ly.slot():
        imgui.text("右")

# 传统方式 - 使用 item() (仍然支持)
with ly.hstack(gap=2):
    ly.item(); imgui.text("左")
    ly.item(); imgui.text("右")

# 垂直排列
with ly.vstack(gap=1):
    with ly.slot():
        imgui.text("行1")
    with ly.slot():
        imgui.text("行2")
```

#### ⚠️ hstack/vstack 的限制

`hstack` 使用 `same_line()` 实现，当 slot 内包含垂直内容时会错位：
```python
# ❌ 错误：slot 内有垂直布局会导致错位
with ly.hstack(gap=4):
    with ly.slot():
        imgui.text("Label")
        ly.gap_y(1)
        imgui.input_text("##input", ...)  # 错位！
```

解决方案：使用 `ly.columns()` 代替。

#### Columns 多列布局 (推荐用于表单)
```python
# ✅ 正确：columns 支持每列独立的垂直内容
with ly.columns(2, gap=4) as c:
    with c.col(0):
        imgui.text("名称")
        ly.gap_y(1)
        imgui.input_text("##name", name)

    with c.col(1):
        imgui.text("版本")
        ly.gap_y(1)
        imgui.input_text("##version", version)

# 指定列宽
with ly.columns(2, widths=[30, 50]) as c:
    with c.col(0):
        imgui.text("短标签")
    with c.col(1):
        # c.col_width 获取当前列宽度
        imgui.push_item_width(c.col_width)
        imgui.input_text("##input", value)
        imgui.pop_item_width()
```

#### Grid 布局
```python
# 2 列网格（类似 CSS grid-cols-2）
with ly.grid(cols=2, gap=4):
    with ly.grid_item():
        imgui.text("Label 1")
    with ly.grid_item():
        imgui.input_text("##input1", value)

    with ly.grid_item():
        imgui.text("Label 2")
    with ly.grid_item():
        imgui.input_text("##input2", value)
```

#### 表单布局
```python
# 标准表单行：左侧标签 + 右侧输入
with ly.form_row("名称", required=True):
    _, value = imgui.input_text("##name", value)

with ly.form_row("描述", help_text="简短描述"):
    _, value = imgui.input_text_multiline("##desc", value)

# 表单分区
with ly.form_section("基本信息"):
    with ly.form_row("类型"):
        ...
```

#### 滚动区域
```python
# 固定高度的垂直滚动区域
with ly.scroll_y(height=50):  # 200px
    for item in long_list:
        imgui.text(item)

# 水平滚动
with ly.scroll_x():
    with ly.hstack(gap=2):
        for img in images:
            draw_thumbnail(img)
```

#### 固定尺寸容器
```python
with ly.fixed_width(60):   # 240px 宽
    imgui.text("固定宽度")

with ly.fixed_height(25):  # 100px 高
    imgui.text("固定高度")

with ly.fixed_size(60, 25):  # 240px × 100px
    imgui.text("固定尺寸")
```

#### 比例分割
```python
# 左右分割 (30% / 70%)
with ly.split_h(left_ratio=0.3, gap=4) as (left, right):
    with left:
        draw_sidebar()
    with right:
        draw_main_content()

# 上下分割
with ly.split_v(top_ratio=0.2, gap=2) as (top, bottom):
    with top:
        draw_header()
    with bottom:
        draw_content()
```

#### 条件渲染
```python
# 比 if 语句更优雅
with ly.visible_if(has_items):
    draw_items_list()

with ly.hidden_if(is_empty):
    draw_content()
```

#### 底部对齐
```python
with ly.fixed_height(50):
    imgui.text("顶部内容")
    with ly.align_bottom():
        (tw.btn_secondary | tw.btn_sm)(imgui.button)("底部按钮")
```

#### 列表项
```python
with ly.list_item(
    "item_id",
    selected=is_active,
    hover_color=tw.ABYSS_600,
    selected_color=tw.ABYSS_500,
) as state:
    imgui.text("物品名称")

if state.clicked:
    select_item()
```

#### 双槽行 - 左右两端对齐
```python
with ly.split_row("section_id", hover_color=tw.ABYSS_600) as row:
    with row.left:
        imgui.text("左侧内容")
    with row.right:
        ly.icon_btn(FA_PLUS, "add")

if row.state.clicked:
    toggle_section()
```

#### 图标按钮
```python
if ly.icon_btn(FA_PLUS, "add_btn", size=5, tooltip_text="添加"):
    add_item()
```

#### 右键菜单
```python
with ly.context_menu("item_ctx") as opened:
    if opened:
        if ly.menu_item("复制", icon=FA_COPY):
            copy_item()
        ly.menu_separator()
        if ly.menu_item("删除", icon=FA_TRASH, danger=True):
            delete_item()
```

#### 右对齐
```python
# 自动测量宽度的右对齐
with ly.auto_right_slot():
    ly.icon_btn(FA_GEAR, "settings")
```

## 🔧 布局选择指南

| 场景 | 推荐方案 |
|------|----------|
| 水平排列元素 (单行) | `ly.hstack(gap=N)` |
| 垂直排列元素 | `ly.vstack(gap=N)` |
| **多列表单 (有垂直内容)** | **`ly.columns(N)`** ⭐ |
| 简单网格 | `ly.grid(cols=N)` |
| 标签+输入行 | `ly.form_row(label)` |
| 左右分栏 | `ly.split_h(ratio)` 或 `ly.split_row()` |
| 可滚动列表 | `ly.scroll_y(height=N)` |
| 固定尺寸区域 | `ly.fixed_width/height/size()` |
| 行内右对齐 | `ly.auto_right_slot()` |
| 可交互列表项 | `ly.list_item()` |
| 可折叠区域 | `ly.collapsible()` |

## 🐛 调试技巧

```python
# 查看当前样式
style = imgui.get_style()
print(f"FramePadding: {style.frame_padding}")

# 样式按 push 顺序叠加，后者覆盖前者
with tw.text_red_500:       # push 1
    with tw.text_blue_500:  # push 2 - 覆盖红色
        imgui.text("蓝色")  # 显示蓝色
    imgui.text("红色")      # 回到红色

# 使用 imgui.show_style_editor() 调试整体主题
```

## 🔧 扩展 Token 的规范 (codegen/generate_tailwind_tokens.py)

### 添加新 Token 的原则

1. **原子化** - 每个 token 只做一件事
2. **正交化** - 不与现有 token 功能重叠
3. **命名规范** - 遵循 Tailwind 命名: `{type}_{color}_{shade}` 或 `{property}_{value}`
4. **分类放置** - 放在对应的 section 注释下
5. **运行生成器** - 修改后执行 `python codegen/generate_tailwind_tokens.py`

### Token 类型参考

| 类型 | 命名模式 | 示例 |
|------|----------|------|
| 文字色 | `text_{color}_{shade}` | `text_parchment_100` |
| 背景色 | `bg_{color}_{shade}` | `bg_abyss_800` |
| 边框色 | `border_{color}_{shade}` | `border_stone_700` |
| 输入框背景 | `frame_bg_{color}_{shade}` | `frame_bg_abyss_700` |
| 间距 | `p_{n}` / `gap_{n}` | `p_4`, `gap_2` |
| 圆角 | `rounded_{size}` | `rounded_lg` |
| 语义层级 | `bg_{layer}` | `bg_surface`, `bg_elevated` |
| 语义边框 | `border_{semantic}` | `border_subtle`, `border_default` |
| 组件预设 | `{component}_default` | `card_default`, `input_default` |

### 语义 Token 层级

```
bg_app        最深层 (窗口底色)
  ↓
bg_surface    面板/卡片
  ↓
bg_elevated   浮层/弹窗
  ↓
bg_input      输入框
```

## 🔧 扩展 Layout 组件的规范 (ui/layout.py)

### 添加新组件的要求

1. **标注容器类型** - 必须在 docstring 中标明:
   ```python
   def my_component():
       """描述

       ⚠️ 容器类型: Child | Group | Table
       """
   ```

2. **DPI 感知** - 所有像素值必须使用 `sz(n)` 或 `dpi_scale()`

3. **返回类型** - 标注返回值类型 (Generator, bool, namedtuple 等)

4. **更新 __all__** - 添加到文件顶部的 `__all__` 列表

5. **遵循函数签名约定**:
   - 尺寸参数用 Tailwind 单位 (1 = 4px): `height: float`
   - 颜色参数用 tuple: `color: tuple[float, float, float, float]`
   - ID 参数放第一个: `id: str`

### 容器类型速查

| 类型 | ImGui 函数 | 有 Padding | 有背景 | 用于 |
|------|------------|------------|--------|------|
| Child | `begin_child()` | ✅ | ✅ | 滚动区域、卡片 |
| Group | `begin_group()` | ❌ | ❌ | 逻辑分组、flex |
| Table | `begin_table()` | ✅ CellPadding | ❌ | 网格布局 |

## 🔧 扩展 Widget 组件的规范 (ui/widgets.py)

### 添加新 Widget 的要求

1. **使用 tw/ly** - 新组件必须使用 `tw.*` 和 `ly.*` (参见文件头 LEGACY 注释)

2. **状态管理** - 如需状态，使用 dataclass + dict 模式:
   ```python
   @dataclass
   class _MyWidgetState:
       value: int = 0

   _my_widget_states: dict[str, _MyWidgetState] = {}
   ```

3. **返回变更信号** - 遵循 `(changed: bool, value: T)` 模式

4. **ID 规范** - 接受 `##id` 格式的 ImGui ID

5. **样式参数化** - 允许通过参数覆盖默认样式:
   ```python
   def my_widget(id: str, *, style: StyleContext = tw.noop):
       with tw.input_default | style:
           ...
   ```

## 🚧 例外情况 - 允许直接操作

某些场景确实需要直接使用底层 API：

```python
# ✅ 自定义绘制 (DrawList)
draw_list = imgui.get_window_draw_list()
draw_list.add_circle(...)

# ✅ 性能关键路径（避免 StyleContext 开销）
# 但应该封装到专用组件中

# ✅ ImGui 特殊控件内部（如 Plot、Table）
```

## ❌ 禁止的 cursor 操作

```python
# ❌ 手动计算位置 - 应该用 split_row
btn_x = start_cursor.x + avail_width - btn_size
imgui.set_cursor_pos((btn_x, y))

# ❌ 手动实现 hover 背景 - 应该用 list_item
if imgui.is_item_hovered():
    draw_list.add_rect_filled(...)

# ❌ 手动管理缓存 - 原语已内置缓存
_cache[id] = (was_hovered, height)
```

## 🧩 表单控件样式

使用 `tw.*` token 组合样式，直接调用 imgui 函数：

```python
# 输入框样式
with tw.frame_bg_abyss_800 | tw.border_abyss_600 | tw.rounded_sm:
    changed, value = imgui.input_text("##name", value, 256)

# 按钮样式 (推荐函数调用式)
if (tw.btn_primary | tw.btn_md)(imgui.button)("确定"):
    save()
if (tw.btn_danger | tw.btn_md)(imgui.button)("删除"):
    delete()

# 复选框
with tw.frame_bg_abyss_800 | tw.text_parchment_200:
    changed, checked = imgui.checkbox("启用", checked)
```
