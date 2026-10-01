# skill-bundle

集中管理并安装个人 Agent Skills。

`skill-bundle` 把多个 Skill 统一存放在仓库中，再通过目录链接把它们暴露到 Agent 发现 Skill 的标准位置：

```text
~/.agents/skills/
```

这样既可以用 Git 统一管理全部 Skill，又不需要把文件复制出去。

## 目录结构

仓库使用「bundle」对 Skill 分组，每个 bundle 是仓库根目录下的一个文件夹：

```text
skill-bundle/
├── base/                       # 通用 Skill
│   ├── pdf/
│   │   └── SKILL.md
│   ├── docx/
│   │   └── SKILL.md
│   └── ...
├── agent-session/              # 按主题划分的 bundle
│   └── session-reliability/    # 以 submodule 形式引入
│       └── SKILL.md
├── install.sh
├── install.ps1
└── README.md
```

一个目录只有直接包含 `SKILL.md` 时才会被识别为 Skill：

```text
<bundle>/<skill-name>/SKILL.md
```

仓库内不同 bundle 下的 Skill 会被**平铺**链接到 `~/.agents/skills/`，链接名就是 Skill 目录名：

```text
~/.agents/skills/
├── pdf                 -> <repo>/base/pdf
├── docx                -> <repo>/base/docx
└── session-reliability -> <repo>/agent-session/session-reliability
```

因此不同 bundle 之间不要出现同名的 Skill。

## 安装

安装脚本会先更新子模块，然后为所有有效 Skill 创建链接。已有链接会被重建；如果目标已存在且不是链接，脚本会报错退出。

### Linux / macOS

```bash
chmod +x install.sh
./install.sh
```

使用符号链接（symlink）。

### Windows

```powershell
.\install.ps1
```

使用 Junction，适合本地目录链接，权限兼容性通常更好。

### 子模块

部分 Skill 以 Git submodule 的形式引入（例如 `agent-session/session-reliability`），其内容并不直接存放在本仓库中。安装脚本在创建链接前会自动执行：

```bash
git submodule update --init --recursive
```

如果通过 `git clone` 获取本仓库，建议直接使用：

```bash
git clone --recursive <repo-url>
```

已经 clone 过的仓库，也可以手动初始化：

```bash
git submodule update --init --recursive
```

## 添加 Skill

在任意 bundle（或新建一个 bundle 文件夹）下新增 Skill：

```text
<bundle>/my-skill/
└── SKILL.md
```

然后重新执行安装脚本，新 Skill 会自动链接到：

```text
~/.agents/skills/my-skill
```

## 更新 Skill

Skill 文件直接保存在仓库中，按常规 Git 流程更新即可：

```bash
git pull
git submodule update --init --recursive
```

链接无需重建，更新后的 Skill 会立即生效。只有新增或删除 Skill 时才需要重新运行安装脚本。

## 设计原则

仓库负责 Skill 的版本管理：

```text
skill-bundle/<bundle>/<skill>
```

Agent 从标准位置发现 Skill：

```text
~/.agents/skills/<skill>
```

两者通过目录链接连接：

```text
skill-bundle/<bundle>/<skill>
            │
            └──────────────> ~/.agents/skills/<skill>
```

通过链接而非复制，避免文件重复，同时让整个 Skill 集合通过一个 Git 仓库统一维护。
