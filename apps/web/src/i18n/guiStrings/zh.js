/** Chinese (Simplified) GUI strings. */
export default {
  common: {
    appTitle: 'Farkki Digital Research NotePad',
    searchRegistry: '搜索注册表...',
    mainNavAria: '实验室主要分区',
    user: '用户：',
    api: 'API：',
    apiConnected: '已连接',
    apiUnreachable: '无法访问',
    apiChecking: '检查中…',
    dbOffline: '数据库离线',
    themeTitle: '主题：{theme}。点击切换。',
    skipToWorkspace: '跳转到工作区',
    platformEyebrow: 'Farkki 研究平台',
    refresh: '刷新',
    refreshAria: '刷新项目、团队和审计数据',
    syncing: '同步中…',
    ready: '就绪',
    projectsSynced: '项目已同步',
    syncWarning: 'API 不可用时使用缓存的项目列表。',
    langLabel: '语言',
    documentTitleSuffix: 'Farkki Lab Assistant',
  },

  navMain: {
    overview: '概览',
    orders: '订单及相关信息',
    social: '社交与杂项',
    data_storage: '数据与存储',
    projects_data: '项目与数据',
    wet_lab: '湿实验室',
    cycif: 'CyCif',
    computational: '计算中心',
    ai_assistant: 'AI 实验室助手',
    administration: '管理',
  },

  navSub: {
    overview: {
      get_started: {
        label: '实验室一般信息',
        description:
          'Färkkilä 实验室与 ONCOSYS 简介 — 入职与导向文件见「入职与离职」标签页。',
      },
      onboarding: {
        label: '入职与离职',
        description: '导向及入职/离职检查清单。',
      },
      guidelines: {
        label: '指南',
        description: '研究与工作相关的实验室指南。',
      },
      documents_permits: {
        label: '文件与许可',
        description: '许可、表格、数据表与手册。',
      },
      personnel: {
        label: '人员',
        description: '人员记录与支持文件。',
      },
      cleaning: {
        label: '实验室清洁',
        description: '清洁计划与实验室维护文件。',
      },
      dashboard: {
        label: '实验室仪表板',
        description: '指标、团队、审计记录与平台就绪状态。',
      },
      research: {
        label: '研究材料',
        description: '会议材料、海报与磁盘上的出版物。',
      },
    },
    orders: {
      billing: {
        label: '账单与订购说明',
        description: '账单、供应商、货运与 HUS 订购。',
      },
      archive: {
        label: '档案',
        description: '历史订单、报价与采购档案。',
      },
      orders: {
        label: '订单登记',
        description: '试剂、测序与服务订单。',
      },
      related: {
        label: '相关记录',
        description: '关联样本、货运与元数据。',
      },
    },
    social: {
      lab_parties: { label: '实验室聚会', description: '万圣节、烧烤及其他活动策划文件。' },
      winter_events: { label: '冬日活动', description: '实验室冬日照片与季节性聚会。' },
      lab_retreats: { label: '实验室团建', description: '团建计划与 Nuuksio 团建资料。' },
      lab_photos: { label: '实验室照片', description: '合影、团建相册与日常照片。' },
      researcher_visits: { label: '研究员来访', description: '访客记录与接待资料。' },
      outreach: { label: '外展与社交媒体', description: '外展活动与社交媒体素材。' },
    },
    data_storage: {
      landscape: {
        label: '存储全景',
        description: '全部实验室存储 — L 盘、P 盘、DataCloud、Google Drive、Allas、Databank。',
      },
      network_drives: {
        label: 'L 盘与 P 盘',
        description: '赫尔辛基大学网络盘：敏感临床（L）与活跃项目（P）。',
      },
      datacloud: {
        label: 'DataCloud 与 Databank',
        description: '大学服务：DataCloud WebDAV /farkkila/（约 10 TB）与 UH Databank 长期归档。',
      },
      cloud_archive: {
        label: 'CSC Allas',
        description: 'CSC 对象存储（约 30 TB 活跃），用于 HPC 分析前暂存。',
      },
      google_drive: {
        label: 'Google Drive',
        description: '项目日志、入职文档与协作。',
      },
      local_storage: {
        label: '本地与外部磁盘',
        description: '工作站、cpu1-data、冷存储盘与 HUS 临床数据库。',
      },
      guidelines: {
        label: '指南与工作流',
        description: 'Active → CSC Allas，inactive/published → UH Databank，敏感性规则。',
      },
      tools: {
        label: '传输工具',
        description: 'rclone、Lumi-O、allas-conf、Cyberduck、rsync — 使用场景与传输模式。',
      },
      documents: {
        label: '实验室文档',
        description: '所有与存储相关的 onboarding、清理、IT 和清单文档。',
      },
    },
    projects_data: {
      portfolio: {
        label: '项目组合',
        description: '浏览项目并打开工作区关键信息。',
      },
      notebook: {
        label: '活页笔记本',
        description: '实验室笔记本日志与协议维基。',
      },
      decisions: {
        label: '研究决策',
        description: '跨项目的正式决策登记。',
      },
      features: {
        label: '特征仓库',
        description: '临床特征矩阵与相似性搜索。',
      },
    },
    wet_lab: {
      files: {
        label: '实验室数据库文件',
        description: '协议、库存与湿实验室磁盘文档。',
      },
      protocols: {
        label: '湿实验室协议',
        description: '样本制备、染色制备与质控 SOP。',
      },
      tasks: {
        label: '湿实验室任务',
        description: '标记为湿实验室工作的任务。',
      },
      inventory: {
        label: '试剂与面板',
        description: '抗体面板与试剂参考。',
      },
    },
    cycif: {
      pipeline: {
        label: '成像流程',
        description: '拼接、分割与质控触发。',
      },
      install: {
        label: '工具安装',
        description: 'Napari、Cylinter 与查看器安装。',
      },
      structure: {
        label: '项目结构',
        description: 't-CycIF 文件夹布局验证。',
      },
      cycif_projects: { label: '单个项目', description: '各项目的染色计划与运行表格。' },
      cycif_instructions: { label: '说明与 SOP', description: 't-CycIF 工作流说明、模板与规划文件。' },
      cycif_sectioning: { label: '切片与 H&E', description: '切片订单与 t-CycIF 后 H&E 染色记录。' },
      cycif_inventory: { label: '抗体库存', description: 'CyCIF 抗体面板与库存表。' },
      cycif_protocols: { label: '协议与资源', description: '空间 CycIF 协议与 GeoMx/CycIF 资源。' },
    },
    computational: {
      onboarding: { label: '入职与凭据' },
      lumi: {
        label: 'LUMI 超算',
        description: 'Slurm 作业、工具安装、流程与 Lumi-O 传输。',
      },
      pouta: {
        label: 'cPouta 虚拟机',
        description: '实验室云 VM、配置指南与 VM 端 Conda。',
      },
      roihu: {
        label: 'Roihu',
        description: 'CSC Roihu 超算 — 内容即将添加。',
      },
      troubleshoot: {
        label: '故障排除',
        description: '环境诊断与日志分析。',
      },
      utilities: {
        label: '实用工具',
        description: '文件操作与 Conda 环境管理。',
      },
      tools: {
        label: '实验室计算工具',
        description: '已发布的实验室软件 — Tribus、CEFIIRA、SPACEstat 及相关空间分析工具。',
      },
    },
    ai_assistant: {
      copilot: {
        label: '聊天助手',
        description: '针对协议与项目文档的 RAG 问答。',
      },
      prompts: { label: '提示模板' },
      ingest: { label: '导入文档' },
      models: { label: '模型注册表' },
    },
    administration: {
      admin: {
        label: '用户与作业',
        description: '健康状态、连接器、白名单、导入作业、认证。',
      },
      connectors: {
        label: '连接器与健康',
        description: 'GET /health 与 /api/platform/connectors 就绪状态。',
      },
    },
  },

  catGroup: {
    billing: '账单与财务',
    logistics: '物流与货运',
    other: '其他',
    guidelines: '实验室指南',
    onboarding: '入职与离职',
    cleaning: '实验室清洁',
    personnel: '人员',
    research: '研究材料',
    permits: '许可与合规',
    reference: '参考与设备',
    pharma: 'GSK 文件',
    archive_finance: '实验室财务与账户',
    archive_procurement: '采购记录',
    archive_it: 'IT 与基础设施',
  },

  cat: {
    biobank: {
      label: '生物样本库申请',
      description: '生物样本库样本与数据申请。',
    },
    bsl_forms: {
      label: 'BSL-2 表格与模板',
      description: 'GMM 表格与 BSL-2 根目录风险评核模板。',
    },
    bsl1_2: {
      label: 'BSL-1 与 BSL-2 手册',
      description: '生物安全手册、应急计划、保险与 THL 模板。',
    },
    bsl_drafts: {
      label: '待修改 BSL 草稿',
      description: '生物安全手册与细胞规则草稿。',
    },
    bsl_gmo: {
      label: '转基因申请草稿',
      description: 'GMM 申请与风险评核表格。',
    },
    ethanol: {
      label: '乙醇许可（Valvira 2019）',
      description: 'Valvira 许可、申诉与库存记录。',
    },
    datasheets: {
      label: '数据表与手册',
      description: '产品数据表与实验室手册。',
    },
    qiagen: {
      label: 'Qiagen 手册',
      description: 'Qiagen 试剂盒手册与协议。',
    },
    equipment_barcodes: {
      label: '设备条形码',
      description: 'REVCO、培养箱等条形码照片。',
    },
    root_docs: {
      label: '一般参考',
      description: 'FFPE 文章、房间编号及其他参考 PDF。',
    },
    gsk_nov2021: {
      label: 'GSK 2021年11月（GSK3859856B）',
      description: '形式发票、海关与用途表格。',
    },
    gsk_filled: {
      label: 'GSK 已填表格（草稿）',
      description: '已完成的 RFI 表格 — Ashwini 与 Anastasiya。',
    },
    gsk_unfilled: {
      label: 'GSK 空白表格',
      description: '赫尔辛基大学空白 RFI 模板。',
    },
    gsk_root: {
      label: 'GSK 其他',
      description: 'MSDS 及其他 GSK 参考文件。',
    },
    research: {
      label: '研究相关',
      description: '摘要、演示、论文、会议、资助与隶属关系。',
    },
    work: {
      label: '工作相关',
      description: '假期、病假与日常工作指南。',
    },
    orientation: {
      label: '导向与安全',
      description: '入职材料、导向 PDF 与 Kauppi 实验室安全。',
    },
    contacts: {
      label: '联系人与流程',
      description: '入职/离职检查清单与重要联系人。',
    },
    cleaning_20250528: {
      label: '清洁日 — 2025年5月28日',
      description: '数据清洁日任务与存储单元备注。',
    },
    cleaning_251205: {
      label: '清洁日 — 2025年12月5日',
      description: '湿实验室、干实验室与外部硬盘清洁清单。',
    },
    roster: {
      label: '现任人员',
      description: '在职实验室成员记录。',
    },
    hiring: {
      label: '招聘',
      description: '招聘广告、面试材料与评分矩阵。',
    },
    lab_management: {
      label: '实验室管理',
      description: '管理结构、角色说明与指示。',
    },
    conference: {
      label: '会议摘要与海报',
      description: 'ESGO、AACR、欧洲卵巢癌研讨会、EMBL 等。',
    },
    phd_apps: {
      label: '博士与博士学校',
      description: '博士学校申请及相关材料。',
    },
    peer_review: {
      label: '同行评审',
      description: '审稿中的论文。',
    },
    presentations: {
      label: '演示与海报存档',
      description: '存档演示与海报文件。',
    },
    general_reference: {
      label: '一般参考',
      description: '核心账单地址、配送信息与大学发票表格。',
    },
    hus_finance: {
      label: 'HUS 财务与账单',
      description: 'HUS 账单说明、EVO 预算与 HUSLAB 订单表格。',
    },
    credentials: {
      label: '凭据与访问',
      description: '供应商网站登录与账户凭据（敏感）。',
    },
    fedex: {
      label: 'FedEx',
      description: 'FedEx 账户详情与存档空运单。',
    },
    ups: {
      label: 'UPS',
      description: 'UPS 快递设置、截图与空运单。',
    },
    dna_shipments: {
      label: 'DNA 样本货运',
      description: '国际 DNA 货运（哥本哈根、Myriad、丹麦）。',
    },
    us_customs: {
      label: '美国海关与形式发票',
      description: 'USDA 声明、形式发票与海关示例。',
    },
    other_admin: {
      label: '行政与设施',
      description: '会议室预订及其他行政参考。',
    },
    hus_purchases: {
      label: 'HUS 实验室采购',
      description: 'HUSLAB 账户采购及实验室采购表格。',
    },
    fican_funding: {
      label: 'FiCAN South 经费',
      description: 'FiCAN South 项目经费与预算登记表。',
    },
    lab_transfers: {
      label: '实验室间转账',
      description: '实验室账户间的资金转移与债务结算。',
    },
    equipment_orders: {
      label: '设备订单确认',
      description: '供应商订单确认（Fisher Scientific、ONCOSYS 设备等）。',
    },
    collaboration_orders: {
      label: '合作采购订单',
      description: '跨实验室合作采购（Kauppi、TERVA）。',
    },
    purchase_registers: {
      label: '采购登记表',
      description: '历史采购电子表及未分类登记文件。',
    },
    computer_orders: {
      label: '计算机与 IT 订单',
      description: '工作站订单、Dustin 发票及 IT 采购表格。',
    },
  },

  taskpad: {
    title: 'Taskpad',
    quickCapture: '快速记录',
    projectLog: '项目日志',
    collapse: '收起',
    close: '收起 taskpad',
    targetArea: '目标区域',
    noteLabel: '备注 / 任务 / 状态',
    notePlaceholder: '在此输入…',
    save: '保存',
    savedAlert: '已保存到 Taskpad！',
    projectLogHint: '项目日志',
    binaryFileHint:
      '此项目日志为 {ext} 文件。请转换为 .md 以在 Taskpad 中完整编辑，或从日志标签页文件浏览器打开原文件。',
  },

  workspace: {
    overview: '概览',
    plan: '计划',
    data: '数据',
    methods: '方法',
    writing: '写作',
    archive: '归档',
    log: '日志',
  },

  docs: {
    files: '个文件',
    searchFiles: '搜索文件',
    searchPlaceholder: '搜索文件…',
    noFilesCategory: '此类别中没有文件。',
    noFilesSearch: '没有匹配搜索的文件。',
    groupTabsAria: '文档分组',
    groupEyebrow: '分区',
    categoryTabsAria: '文档类别',
    subcategoryEyebrow: '类别',
    subfolderTabsAria: '文档子文件夹',
    albumsEyebrow: '选择相册',
    albumFileOne: '1 个文件',
    albumFileMany: '{count} 个文件',
    selectFile: '选择文件以预览提取内容或打开原文件。',
    openOriginal: '打开原文件',
    revealSensitive: '显示敏感内容',
    hideSensitive: '隐藏敏感内容',
    sensitiveMasked: '敏感内容 — 预览默认已遮盖。',
    loading: '正在加载文档…',
    loadError: '加载文档失败。',
    teamDirectory: '团队名录',
    filesInSection: '{count} 个文件',
  },
};
