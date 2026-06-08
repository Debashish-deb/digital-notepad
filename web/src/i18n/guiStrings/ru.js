/** Russian GUI strings. */
export default {
  common: {
    appTitle: 'Farkki Digital Research NotePad',
    searchRegistry: 'Поиск в реестре...',
    mainNavAria: 'Основные разделы лаборатории',
    user: 'Пользователь:',
    api: 'API:',
    apiConnected: 'Подключено',
    apiUnreachable: 'Недоступно',
    apiChecking: 'Проверка…',
    dbOffline: 'БД офлайн',
    themeTitle: 'Тема: {theme}. Нажмите для переключения.',
    skipToWorkspace: 'Перейти к рабочей области',
    platformEyebrow: 'Исследовательская платформа Farkki',
    refresh: 'Обновить',
    refreshAria: 'Обновить данные проектов, команды и аудита',
    syncing: 'Синхронизация…',
    ready: 'Готово',
    projectsSynced: 'Проекты синхронизированы',
    syncWarning: 'Используется кэшированный список проектов, так как API был недоступен.',
    langLabel: 'Язык',
    documentTitleSuffix: 'Farkki Lab Assistant',
  },

  navMain: {
    overview: 'Обзор',
    orders: 'Заказы и связанная информация',
    social: 'Социальное и прочее',
    data_storage: 'Данные и хранилище',
    projects_data: 'Проекты и данные',
    wet_lab: 'Мокрая лаборатория',
    cycif: 'CyCif',
    computational: 'Вычислительный центр',
    ai_assistant: 'ИИ-ассистент лаборатории',
    administration: 'Администрирование',
  },

  navSub: {
    overview: {
      get_started: {
        label: 'Общая информация о лаборатории',
        description:
          'Введение в лабораторию Färkkilä и ONCOSYS — файлы ориентации и адаптации находятся в разделе Адаптация и выход.',
      },
      onboarding: {
        label: 'Адаптация и выход',
        description: 'Чек-листы ориентации, адаптации и выхода.',
      },
      guidelines: {
        label: 'Руководства',
        description: 'Руководства по исследованиям и повседневной работе в лаборатории.',
      },
      documents_permits: {
        label: 'Документы и разрешения',
        description: 'Разрешения, формы, паспорта и справочники.',
      },
      personnel: {
        label: 'Персонал',
        description: 'Записи о персонале и вспомогательные документы.',
      },
      cleaning: {
        label: 'Уборка лаборатории',
        description: 'Графики уборки и документы по содержанию лаборатории.',
      },
      dashboard: {
        label: 'Панель лаборатории',
        description: 'Метрики, команда, журнал аудита и готовность платформы.',
      },
      research: {
        label: 'Исследовательские материалы',
        description: 'Материалы конференций, постеры и публикации на диске.',
      },
    },
    orders: {
      billing: {
        label: 'Инструкции по выставлению счетов и заказам',
        description: 'Выставление счетов, поставщики, отправки и заказы HUS.',
      },
      archive: {
        label: 'Архив',
        description: 'Исторические заказы, котировки и архивы закупок.',
      },
      orders: {
        label: 'Реестр заказов',
        description: 'Реагенты, секвенирование и сервисные заказы.',
      },
      related: {
        label: 'Связанные записи',
        description: 'Связанные образцы, отправки и метаданные.',
      },
    },
    social: {
      lab_parties: { label: 'Вечеринки лаборатории', description: 'Хэллоуин, гриль и планирование мероприятий.' },
      winter_events: { label: 'Зимний день и сезонные события', description: 'Фото зимнего дня и сезонные встречи.' },
      lab_retreats: { label: 'Выезды лаборатории', description: 'Планирование выездов и материалы Nuuksio.' },
      lab_photos: { label: 'Фото лаборатории', description: 'Групповые фото, альбомы выездов и повседневные снимки.' },
      researcher_visits: { label: 'Визиты исследователей', description: 'Записи гостей и материалы приёма.' },
      outreach: { label: 'Просвещение и соцсети', description: 'Кампании и материалы для социальных сетей.' },
    },
    data_storage: {
      landscape: {
        label: 'Карта хранилищ',
        description:
          'Все системы хранения лаборатории — L-drive, P-drive, DataCloud, Google Drive, Allas, Databank.',
      },
      network_drives: {
        label: 'L-drive и P-drive',
        description: 'Сетевые диски HY: клинические данные (L) и активные проекты (P).',
      },
      datacloud: {
        label: 'DataCloud и Databank',
        description:
          'Услуги университета: DataCloud WebDAV /farkkila/ (~10 ТБ) и UH Databank для долгосрочного архива.',
      },
      cloud_archive: {
        label: 'CSC Allas',
        description: 'Объектное хранилище CSC (~30 ТБ активное) перед HPC-анализом.',
      },
      google_drive: {
        label: 'Google Drive',
        description: 'Журналы проектов, онбординг и совместная работа.',
      },
      local_storage: {
        label: 'Локальные и внешние диски',
        description: 'Рабочие станции, cpu1-data, холодные диски и клиническая БД HUS.',
      },
      guidelines: {
        label: 'Руководства и рабочий процесс',
        description: 'Active → CSC Allas, inactive/published → UH Databank, правила чувствительности.',
      },
      tools: {
        label: 'Инструменты передачи',
        description: 'rclone, Lumi-O, allas-conf, Cyberduck, rsync — когда использовать.',
      },
      documents: {
        label: 'Документы лаборатории',
        description: 'Все документы по хранению: onboarding, cleaning, IT и инвентарь.',
      },
    },
    projects_data: {
      portfolio: {
        label: 'Портфель проектов',
        description: 'Просмотр проектов и открытие основных показателей рабочей области.',
      },
      notebook: {
        label: 'Живой блокнот',
        description: 'Журналы лабораторного блокнота и вики протоколов.',
      },
      decisions: {
        label: 'Исследовательские решения',
        description: 'Формальный реестр решений по проектам.',
      },
      features: {
        label: 'Склад признаков',
        description: 'Клиническая матрица признаков и поиск по сходству.',
      },
    },
    wet_lab: {
      files: {
        label: 'Файлы базы данных лаборатории',
        description: 'Протоколы, инвентари и документы мокрой лаборатории на диске.',
      },
      protocols: {
        label: 'Протоколы мокрой лаборатории',
        description: 'СОП для подготовки образцов, окраски и контроля качества.',
      },
      tasks: {
        label: 'Задачи мокрой лаборатории',
        description: 'Задачи с меткой работы в мокрой лаборатории.',
      },
      inventory: {
        label: 'Реагенты и панели',
        description: 'Антителевые панели и справочники реагентов.',
      },
    },
    cycif: {
      pipeline: {
        label: 'Конвейер визуализации',
        description: 'Сшивка, сегментация и триггеры контроля качества.',
      },
      install: {
        label: 'Настройка инструментов',
        description: 'Установка Napari, Cylinter и просмотрщиков.',
      },
      structure: {
        label: 'Структура проекта',
        description: 'Проверка структуры папок t-CycIF.',
      },
      cycif_projects: { label: 'Отдельные проекты', description: 'Планы окраски и таблицы запусков по проектам.' },
      cycif_instructions: { label: 'Инструкции и СОП', description: 'Инструкции t-CycIF, шаблоны и файлы планирования.' },
      cycif_sectioning: { label: 'Срезы и H&E', description: 'Заказы на срезы и H&E после t-CycIF.' },
      cycif_inventory: { label: 'Инвентарь антител', description: 'Панели антител CyCIF и таблицы инвентаря.' },
      cycif_protocols: { label: 'Протоколы и ресурсы', description: 'Пространственные протоколы CycIF и ресурсы GeoMx/CycIF.' },
    },
    computational: {
      onboarding: { label: 'Адаптация и учётные данные' },
      lumi: {
        label: 'Суперкомпьютер LUMI',
        description: 'Задачи Slurm, установка инструментов, конвейеры и передача Lumi-O.',
      },
      pouta: {
        label: 'ВМ cPouta',
        description: 'Облачные ВМ лаборатории, руководства и conda на ВМ.',
      },
      roihu: {
        label: 'Roihu',
        description: 'Суперкомпьютер CSC Roihu — содержимое скоро.',
      },
      troubleshoot: {
        label: 'Устранение неполадок',
        description: 'Диагностика среды и анализ логов.',
      },
      utilities: {
        label: 'Утилиты',
        description: 'Операции с файлами и управление средами conda.',
      },
      tools: {
        label: 'Вычислительные инструменты лаборатории',
        description: 'Опубликованное ПО лаборатории — Tribus, CEFIIRA, SPACEstat и связанные инструменты.',
      },
    },
    ai_assistant: {
      copilot: {
        label: 'Чат-ассистент',
        description: 'RAG-вопросы и ответы по протоколам и документам проектов.',
      },
      prompts: { label: 'Шаблоны промптов' },
      ingest: { label: 'Импорт документов' },
      models: { label: 'Реестр моделей' },
    },
    administration: {
      admin: {
        label: 'Пользователи и задания',
        description: 'Состояние, коннекторы, белый список, задания импорта, аутентификация.',
      },
      connectors: {
        label: 'Коннекторы и состояние',
        description: 'Готовность GET /health и /api/platform/connectors.',
      },
    },
  },

  catGroup: {
    billing: 'Выставление счетов и финансы',
    logistics: 'Логистика и отправки',
    other: 'Прочее',
    guidelines: 'Руководства лаборатории',
    onboarding: 'Адаптация и выход',
    cleaning: 'Уборка лаборатории',
    personnel: 'Персонал',
    research: 'Исследовательские материалы',
    permits: 'Разрешения и соответствие',
    reference: 'Справочники и оборудование',
    pharma: 'Документы GSK',
    archive_finance: 'Финансы и счета лаборатории',
    archive_procurement: 'Закупки и регистры',
    archive_it: 'IT и инфраструктура',
  },

  cat: {
    biobank: {
      label: 'Запросы в биобанк',
      description: 'Запросы образцов и данных биобанка.',
    },
    bsl_forms: {
      label: 'Формы и шаблоны BSL-2',
      description: 'Формы GMM и шаблоны оценки рисков в корне BSL-2.',
    },
    bsl1_2: {
      label: 'Руководства BSL-1 и BSL-2',
      description: 'Руководства по биобезопасности, планы на ЧС, страховки и шаблоны THL.',
    },
    bsl_drafts: {
      label: 'Черновики BSL для доработки',
      description: 'Черновики руководств по биобезопасности и правил работы с клетками.',
    },
    bsl_gmo: {
      label: 'Черновики заявок на ГМО',
      description: 'Формы заявок GMM и оценки рисков.',
    },
    ethanol: {
      label: 'Разрешение на этанол (Valvira 2019)',
      description: 'Разрешения Valvira, апелляции и записи инвентаризации.',
    },
    datasheets: {
      label: 'Паспорта и справочники',
      description: 'Паспорта продуктов и справочники лаборатории.',
    },
    qiagen: {
      label: 'Справочники Qiagen',
      description: 'Справочники и протоколы наборов Qiagen.',
    },
    equipment_barcodes: {
      label: 'Штрихкоды оборудования',
      description: 'Фото штрихкодов REVCO, инкубаторов и т.д.',
    },
    root_docs: {
      label: 'Общие справочные материалы',
      description: 'Статьи по FFPE, номера комнат и прочие справочные PDF.',
    },
    gsk_nov2021: {
      label: 'GSK ноябрь 2021 (GSK3859856B)',
      description: 'Проформы, таможня и формы назначения.',
    },
    gsk_filled: {
      label: 'Заполненные формы GSK (черновики)',
      description: 'Заполненные формы RFI — Ashwini и Anastasiya.',
    },
    gsk_unfilled: {
      label: 'Незаполненные формы GSK',
      description: 'Пустые шаблоны RFI Хельсинкского университета.',
    },
    gsk_root: {
      label: 'Прочее GSK',
      description: 'MSDS и другие справочные файлы GSK.',
    },
    research: {
      label: 'Исследовательские',
      description: 'Аннотации, презентации, диссертации, встречи, гранты и аффилиации.',
    },
    work: {
      label: 'Рабочие',
      description: 'Отпуска, больничные и повседневные рабочие правила.',
    },
    orientation: {
      label: 'Ориентация и безопасность',
      description: 'Материалы адаптации, PDF ориентации и безопасность лаборатории Kauppi.',
    },
    contacts: {
      label: 'Контакты и процедуры',
      description: 'Чек-листы адаптации/выхода и важные контакты.',
    },
    cleaning_20250528: {
      label: 'День уборки — 28 мая 2025',
      description: 'Задачи дня очистки данных и комментарии к хранилищам.',
    },
    cleaning_251205: {
      label: 'День уборки — 5 дек. 2025',
      description: 'Инвентари уборки мокрой, сухой лаборатории и внешних дисков.',
    },
    roster: {
      label: 'Текущий персонал',
      description: 'Записи активных членов лаборатории.',
    },
    hiring: {
      label: 'Найм и рекрутинг',
      description: 'Объявления о вакансиях, материалы собеседований и матрицы оценки.',
    },
    lab_management: {
      label: 'Управление лабораторией',
      description: 'Структура управления, описания ролей и инструкции.',
    },
    conference: {
      label: 'Аннотации и постеры конференций',
      description: 'ESGO, AACR, European Ovarian Cancer Symposium, EMBL и др.',
    },
    phd_apps: {
      label: 'PhD и докторантура',
      description: 'Заявки в докторскую школу и связанные материалы.',
    },
    peer_review: {
      label: 'Рецензирование',
      description: 'Статьи на рецензировании.',
    },
    presentations: {
      label: 'Архив презентаций и постеров',
      description: 'Архивные презентации и файлы постеров.',
    },
    general_reference: {
      label: 'Общие справочные материалы',
      description: 'Основные адреса для счетов, информация о доставке и формы счетов университета.',
    },
    hus_finance: {
      label: 'Финансы и выставление счетов HUS',
      description: 'Инструкции HUS по счетам, бюджеты EVO и формы заказов HUSLAB.',
    },
    credentials: {
      label: 'Учётные данные и доступ',
      description: 'Логины на сайтах поставщиков (конфиденциально).',
    },
    fedex: {
      label: 'FedEx',
      description: 'Данные аккаунта FedEx и архивные авианакладные.',
    },
    ups: {
      label: 'UPS',
      description: 'Настройка курьера UPS, скриншоты и авианакладные.',
    },
    dna_shipments: {
      label: 'Отправки образцов ДНК',
      description: 'Международные отправки ДНК (Копенгаген, Myriad, Дания).',
    },
    us_customs: {
      label: 'Таможня США и проформа',
      description: 'Заявления USDA, проформы и примеры таможенного оформления.',
    },
    other_admin: {
      label: 'Администрирование и помещения',
      description: 'Бронирование комнат и прочие административные справочники.',
    },
    hus_purchases: {
      label: 'Закупки HUS Lab',
      description: 'Закупки по счёту HUSLAB и таблицы лабораторных закупок.',
    },
    fican_funding: {
      label: 'Финансирование FiCAN South',
      description: 'Регистры финансирования и бюджета программы FiCAN South.',
    },
    lab_transfers: {
      label: 'Межлабораторные переводы',
      description: 'Денежные переводы и погашение долгов между лабораториями.',
    },
    equipment_orders: {
      label: 'Подтверждения заказов оборудования',
      description: 'Подтверждения поставщиков (Fisher Scientific, оборудование ONCOSYS и др.).',
    },
    collaboration_orders: {
      label: 'Совместные закупки',
      description: 'Межлабораторные закупки (Kauppi, TERVA).',
    },
    purchase_registers: {
      label: 'Реестры закупок',
      description: 'Исторические таблицы закупок и неклассифицированные реестры.',
    },
    computer_orders: {
      label: 'Заказы компьютеров и IT',
      description: 'Заказы рабочих станций, счета Dustin и формы IT-закупок.',
    },
  },

  taskpad: {
    title: 'Taskpad',
    quickCapture: 'Быстрая запись',
    projectLog: 'Журнал проекта',
    collapse: 'Свернуть',
    close: 'Свернуть taskpad',
    targetArea: 'Целевая область',
    noteLabel: 'Заметка / задача / статус',
    notePlaceholder: 'Введите текст…',
    save: 'Сохранить',
    savedAlert: 'Сохранено в Taskpad!',
    projectLogHint: 'Журнал проекта',
    binaryFileHint:
      'Этот журнал проекта — файл {ext}. Преобразуйте его в .md для полного редактирования в Taskpad или откройте оригинал в браузере файлов вкладки Журнал.',
  },

  workspace: {
    overview: 'Обзор',
    plan: 'План',
    data: 'Данные',
    methods: 'Методы',
    writing: 'Публикации',
    archive: 'Архив',
    log: 'Журнал',
  },

  docs: {
    files: 'файлов',
    searchFiles: 'Поиск файлов',
    searchPlaceholder: 'Поиск файлов…',
    noFilesCategory: 'В этой категории нет файлов.',
    noFilesSearch: 'Нет файлов, соответствующих поиску.',
    groupTabsAria: 'Группы документов',
    groupEyebrow: 'Разделы',
    categoryTabsAria: 'Категории документов',
    subcategoryEyebrow: 'Категории',
    subfolderTabsAria: 'Подпапки документов',
    albumsEyebrow: 'Выберите альбом',
    albumFileOne: '1 файл',
    albumFileMany: '{count} файлов',
    selectFile: 'Выберите файл для предпросмотра извлечённого содержимого или открытия оригинала.',
    openOriginal: 'Открыть оригинал',
    revealSensitive: 'Показать конфиденциальное',
    hideSensitive: 'Скрыть конфиденциальное',
    sensitiveMasked: 'Конфиденциальное содержимое — предпросмотр скрыт по умолчанию.',
    loading: 'Загрузка документов…',
    loadError: 'Не удалось загрузить документы.',
    teamDirectory: 'Справочник команды',
    filesInSection: '{count} файлов',
  },
};
