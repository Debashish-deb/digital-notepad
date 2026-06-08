/** Spanish GUI strings. */
export default {
  common: {
    appTitle: 'Farkki Digital Research NotePad',
    searchRegistry: 'Buscar en el registro...',
    mainNavAria: 'Secciones principales del laboratorio',
    user: 'Usuario:',
    api: 'API:',
    apiConnected: 'Conectado',
    apiUnreachable: 'Inaccesible',
    apiChecking: 'Comprobando…',
    dbOffline: 'BD sin conexión',
    themeTitle: 'Tema: {theme}. Haga clic para cambiar.',
    skipToWorkspace: 'Ir al espacio de trabajo',
    platformEyebrow: 'Plataforma de investigación Farkki',
    refresh: 'Actualizar',
    refreshAria: 'Actualizar datos de proyectos, equipo y auditoría',
    syncing: 'Sincronizando…',
    ready: 'Listo',
    projectsSynced: 'Proyectos sincronizados',
    syncWarning: 'Se usa la lista de proyectos en caché porque la API no estaba disponible.',
    langLabel: 'Idioma',
    documentTitleSuffix: 'Farkki Lab Assistant',
  },

  navMain: {
    overview: 'Resumen',
    orders: 'Pedidos e información relacionada',
    social: 'Social y varios',
    data_storage: 'Datos y almacenamiento',
    projects_data: 'Proyectos y datos',
    wet_lab: 'Laboratorio húmedo',
    cycif: 'CyCif',
    computational: 'Centro computacional',
    ai_assistant: 'Asistente de IA del laboratorio',
    administration: 'Administración',
  },

  navSub: {
    overview: {
      get_started: {
        label: 'Información general del laboratorio',
        description:
          'Introducción al laboratorio Färkkilä y ONCOSYS — los archivos de orientación e incorporación están en Incorporación y salida.',
      },
      onboarding: {
        label: 'Incorporación y salida',
        description: 'Listas de verificación de orientación, incorporación y salida.',
      },
      guidelines: {
        label: 'Directrices',
        description: 'Directrices del laboratorio relacionadas con la investigación y el trabajo.',
      },
      documents_permits: {
        label: 'Documentos y permisos',
        description: 'Permisos, formularios, fichas técnicas y manuales.',
      },
      personnel: {
        label: 'Personal',
        description: 'Registros de personal y documentos de apoyo.',
      },
      cleaning: {
        label: 'Limpieza del laboratorio',
        description: 'Calendarios de limpieza y documentos de mantenimiento del laboratorio.',
      },
      dashboard: {
        label: 'Panel del laboratorio',
        description: 'Métricas, equipo, registro de auditoría y estado de la plataforma.',
      },
      research: {
        label: 'Materiales de investigación',
        description: 'Materiales de congresos, pósters y publicaciones en disco.',
      },
    },
    orders: {
      billing: {
        label: 'Instrucciones de facturación y pedidos',
        description: 'Facturación, proveedores, envíos y pedidos HUS.',
      },
      archive: {
        label: 'Archivo',
        description: 'Pedidos históricos, presupuestos y archivos de adquisiciones.',
      },
      orders: {
        label: 'Registro de pedidos',
        description: 'Pedidos de reactivos, secuenciación y servicios.',
      },
      related: {
        label: 'Registros relacionados',
        description: 'Muestras, envíos y metadatos vinculados.',
      },
    },
    social: {
      lab_parties: { label: 'Fiestas del laboratorio', description: 'Halloween, barbacoas y planificación de eventos.' },
      winter_events: { label: 'Día de invierno y eventos', description: 'Fotos del día de invierno y reuniones estacionales.' },
      lab_retreats: { label: 'Retiros del laboratorio', description: 'Planificación de retiros y materiales de Nuuksio.' },
      lab_photos: { label: 'Fotos del laboratorio', description: 'Fotos de grupo, álbumes de retiros e imágenes del día a día.' },
      researcher_visits: { label: 'Visitas de investigadores', description: 'Registros de visitantes y materiales de acogida.' },
      outreach: { label: 'Divulgación y redes sociales', description: 'Campañas de divulgación y recursos para redes.' },
    },
    data_storage: {
      landscape: {
        label: 'Panorama de almacenamiento',
        description:
          'Todos los sistemas — L-drive, P-drive, DataCloud, Google Drive, Allas, Databank.',
      },
      network_drives: {
        label: 'L-drive y P-drive',
        description: 'Unidades de red UH: clínico sensible (L) y proyectos activos (P).',
      },
      datacloud: {
        label: 'DataCloud y Databank',
        description:
          'Servicios universitarios: DataCloud WebDAV /farkkila/ (~10 TB) y Databank UH para archivos a largo plazo.',
      },
      cloud_archive: {
        label: 'CSC Allas',
        description: 'Almacenamiento de objetos CSC (~30 TB activo) antes del análisis HPC.',
      },
      google_drive: {
        label: 'Google Drive',
        description: 'Registros de proyecto, incorporación y colaboración.',
      },
      local_storage: {
        label: 'Discos locales y externos',
        description: 'Estaciones de trabajo, cpu1-data, discos fríos y base clínica HUH.',
      },
      guidelines: {
        label: 'Directrices y flujo de trabajo',
        description: 'Active → CSC Allas, inactive/published → UH Databank, reglas de sensibilidad.',
      },
      tools: {
        label: 'Herramientas de transferencia',
        description: 'rclone, Lumi-O, allas-conf, Cyberduck, rsync — cuándo usar cada una.',
      },
      documents: {
        label: 'Documentos del laboratorio',
        description: 'Todos los documentos de almacenamiento: onboarding, limpieza, IT e inventario.',
      },
    },
    projects_data: {
      portfolio: {
        label: 'Cartera de proyectos',
        description: 'Explorar proyectos y abrir datos vitales del espacio de trabajo.',
      },
      notebook: {
        label: 'Cuaderno vivo',
        description: 'Registros del cuaderno de laboratorio y wiki de protocolos.',
      },
      decisions: {
        label: 'Decisiones de investigación',
        description: 'Registro formal de decisiones entre proyectos.',
      },
      features: {
        label: 'Almacén de características',
        description: 'Matriz de características clínicas y búsqueda por similitud.',
      },
    },
    wet_lab: {
      files: {
        label: 'Archivos de la base de datos del laboratorio',
        description: 'Protocolos, inventarios y documentos del laboratorio húmedo en disco.',
      },
      protocols: {
        label: 'Protocolos del laboratorio húmedo',
        description: 'SOP para preparación de muestras, tinción y control de calidad.',
      },
      tasks: {
        label: 'Tareas del laboratorio húmedo',
        description: 'Tareas etiquetadas para trabajo en laboratorio húmedo.',
      },
      inventory: {
        label: 'Reactivos y paneles',
        description: 'Paneles de anticuerpos y referencias de reactivos.',
      },
    },
    cycif: {
      pipeline: {
        label: 'Flujo de imagen',
        description: 'Unión, segmentación y activadores de control de calidad.',
      },
      install: {
        label: 'Configuración de herramientas',
        description: 'Instalación de Napari, Cylinter y visores.',
      },
      structure: {
        label: 'Estructura del proyecto',
        description: 'Validación del diseño de carpetas t-CycIF.',
      },
      cycif_projects: { label: 'Proyectos individuales', description: 'Planes de tinción y hojas de ejecución por proyecto.' },
      cycif_instructions: { label: 'Instrucciones y SOP', description: 'Instrucciones t-CycIF, plantillas y archivos de planificación.' },
      cycif_sectioning: { label: 'Seccionado y H&E', description: 'Órdenes de seccionado y H&E tras t-CycIF.' },
      cycif_inventory: { label: 'Inventario de anticuerpos', description: 'Paneles CyCIF y hojas de inventario.' },
      cycif_protocols: { label: 'Protocolos y recursos', description: 'Protocolos espaciales CycIF y recursos GeoMx/CycIF.' },
    },
    computational: {
      onboarding: { label: 'Incorporación y credenciales' },
      lumi: {
        label: 'HPC LUMI',
        description: 'Trabajos Slurm, instalación de herramientas, flujos y transferencias Lumi-O.',
      },
      pouta: {
        label: 'Máquinas virtuales cPouta',
        description: 'VM en la nube del laboratorio, guías y conda en VM.',
      },
      roihu: {
        label: 'Roihu',
        description: 'Supercomputador CSC Roihu — contenido próximamente.',
      },
      troubleshoot: {
        label: 'Resolución de problemas',
        description: 'Diagnóstico del entorno y análisis de registros.',
      },
      utilities: {
        label: 'Utilidades',
        description: 'Operaciones con archivos y gestión de entornos conda.',
      },
      tools: {
        label: 'Herramientas computacionales del laboratorio',
        description: 'Software publicado del laboratorio — Tribus, CEFIIRA, SPACEstat y herramientas espaciales relacionadas.',
      },
    },
    ai_assistant: {
      copilot: {
        label: 'Copiloto de chat',
        description: 'Preguntas y respuestas RAG sobre protocolos y documentos de proyectos.',
      },
      prompts: { label: 'Plantillas de prompts' },
      ingest: { label: 'Ingerir documentos' },
      models: { label: 'Registro de modelos' },
    },
    administration: {
      admin: {
        label: 'Usuarios y trabajos',
        description: 'Estado, conectores, lista permitida, trabajos de ingesta, autenticación.',
      },
      connectors: {
        label: 'Conectores y estado',
        description: 'Disponibilidad de GET /health y /api/platform/connectors.',
      },
    },
  },

  catGroup: {
    billing: 'Facturación y finanzas',
    logistics: 'Logística y envíos',
    other: 'Otros',
    guidelines: 'Directrices del laboratorio',
    onboarding: 'Incorporación y salida',
    cleaning: 'Limpieza del laboratorio',
    personnel: 'Personal',
    research: 'Materiales de investigación',
    permits: 'Permisos y cumplimiento',
    reference: 'Referencia y equipamiento',
    pharma: 'Documentos GSK',
    archive_finance: 'Finanzas y cuentas del laboratorio',
    archive_procurement: 'Registros de compras',
    archive_it: 'TI e infraestructura',
  },

  cat: {
    biobank: {
      label: 'Solicitudes al biobanco',
      description: 'Solicitudes de muestras y datos del biobanco.',
    },
    bsl_forms: {
      label: 'Formularios y plantillas BSL-2',
      description: 'Formularios GMM y plantillas de evaluación de riesgos en la raíz BSL-2.',
    },
    bsl1_2: {
      label: 'Manuales BSL-1 y BSL-2',
      description: 'Manuales de bioseguridad, planes de emergencia, seguros y plantillas THL.',
    },
    bsl_drafts: {
      label: 'Borradores BSL para modificación',
      description: 'Borradores de manuales de bioseguridad y normas de células.',
    },
    bsl_gmo: {
      label: 'Borradores de solicitud OGM',
      description: 'Formularios de solicitud GMM y evaluación de riesgos.',
    },
    ethanol: {
      label: 'Permiso de etanol (Valvira 2019)',
      description: 'Permisos Valvira, apelaciones y registros de inventario.',
    },
    datasheets: {
      label: 'Fichas técnicas y manuales',
      description: 'Fichas técnicas de productos y manuales del laboratorio.',
    },
    qiagen: {
      label: 'Manuales Qiagen',
      description: 'Manuales y protocolos de kits Qiagen.',
    },
    equipment_barcodes: {
      label: 'Códigos de barras de equipos',
      description: 'Fotos de códigos de barras de REVCO, incubadoras, etc.',
    },
    root_docs: {
      label: 'Referencia general',
      description: 'Artículos FFPE, números de sala y PDF de referencia varios.',
    },
    gsk_nov2021: {
      label: 'GSK nov. 2021 (GSK3859856B)',
      description: 'Facturas proforma, aduanas y formularios de finalidad.',
    },
    gsk_filled: {
      label: 'Formularios GSK completados (borradores)',
      description: 'Formularios RFI completados — Ashwini y Anastasiya.',
    },
    gsk_unfilled: {
      label: 'Formularios GSK sin completar',
      description: 'Plantillas RFI en blanco de la Universidad de Helsinki.',
    },
    gsk_root: {
      label: 'GSK otros',
      description: 'MSDS y otros archivos de referencia GSK.',
    },
    research: {
      label: 'Relacionados con la investigación',
      description: 'Resúmenes, presentaciones, tesis, reuniones, subvenciones y afiliaciones.',
    },
    work: {
      label: 'Relacionados con el trabajo',
      description: 'Vacaciones, bajas por enfermedad y directrices laborales diarias.',
    },
    orientation: {
      label: 'Orientación y seguridad',
      description: 'Materiales de incorporación, PDF de orientación y seguridad del laboratorio Kauppi.',
    },
    contacts: {
      label: 'Contactos y procedimientos',
      description: 'Listas de verificación de incorporación/salida y contactos importantes.',
    },
    cleaning_20250528: {
      label: 'Día de limpieza — 28 may 2025',
      description: 'Tareas del día de limpieza de datos y comentarios de unidades de almacenamiento.',
    },
    cleaning_251205: {
      label: 'Día de limpieza — 5 dic 2025',
      description: 'Inventarios de limpieza del laboratorio húmedo, seco y unidades externas.',
    },
    roster: {
      label: 'Personal actual',
      description: 'Registros de miembros activos del laboratorio.',
    },
    hiring: {
      label: 'Contratación y reclutamiento',
      description: 'Anuncios de empleo, materiales de entrevista y matrices de puntuación.',
    },
    lab_management: {
      label: 'Gestión del laboratorio',
      description: 'Estructura de gestión, descripciones de roles e instrucciones.',
    },
    conference: {
      label: 'Resúmenes y pósters de congresos',
      description: 'ESGO, AACR, European Ovarian Cancer Symposium, EMBL, etc.',
    },
    phd_apps: {
      label: 'Doctorado y escuela doctoral',
      description: 'Solicitudes a la escuela doctoral y materiales relacionados.',
    },
    peer_review: {
      label: 'Revisión por pares',
      description: 'Artículos en revisión por pares.',
    },
    presentations: {
      label: 'Archivo de presentaciones y pósters',
      description: 'Presentaciones archivadas y archivos de pósters.',
    },
    general_reference: {
      label: 'Referencia general',
      description: 'Direcciones de facturación, información de entrega y formularios de factura universitarios.',
    },
    hus_finance: {
      label: 'Finanzas y facturación HUS',
      description: 'Instrucciones de facturación HUS, presupuestos EVO y formularios de pedido HUSLAB.',
    },
    credentials: {
      label: 'Credenciales y acceso',
      description: 'Inicios de sesión en sitios de proveedores (sensible).',
    },
    fedex: {
      label: 'FedEx',
      description: 'Datos de cuenta FedEx y guías aéreas archivadas.',
    },
    ups: {
      label: 'UPS',
      description: 'Configuración de mensajería UPS, capturas de pantalla y guías aéreas.',
    },
    dna_shipments: {
      label: 'Envíos de muestras de ADN',
      description: 'Envíos internacionales de ADN (Copenhague, Myriad, Dinamarca).',
    },
    us_customs: {
      label: 'Aduanas de EE. UU. y proforma',
      description: 'Declaraciones USDA, facturas proforma y ejemplos aduaneros.',
    },
    other_admin: {
      label: 'Administración e instalaciones',
      description: 'Reserva de salas y otras referencias administrativas.',
    },
    hus_purchases: {
      label: 'Compras HUS Lab',
      description: 'Compras de cuenta HUSLAB y hojas de adquisiciones del laboratorio.',
    },
    fican_funding: {
      label: 'Financiación FiCAN South',
      description: 'Registros de financiación y presupuesto del programa FiCAN South.',
    },
    lab_transfers: {
      label: 'Transferencias entre laboratorios',
      description: 'Transferencias de dinero y liquidación de deudas entre cuentas.',
    },
    equipment_orders: {
      label: 'Confirmaciones de pedidos de equipos',
      description: 'Confirmaciones de proveedores (Fisher Scientific, equipos ONCOSYS, etc.).',
    },
    collaboration_orders: {
      label: 'Pedidos de colaboración',
      description: 'Adquisiciones entre laboratorios (Kauppi, TERVA).',
    },
    purchase_registers: {
      label: 'Registros de compras',
      description: 'Hojas históricas de compras y registros sin clasificar.',
    },
    computer_orders: {
      label: 'Pedidos de informática e IT',
      description: 'Pedidos de estaciones de trabajo, facturas Dustin y formularios IT.',
    },
  },

  taskpad: {
    title: 'Taskpad',
    quickCapture: 'Captura rápida',
    projectLog: 'Registro del proyecto',
    collapse: 'Contraer',
    close: 'Contraer taskpad',
    targetArea: 'Área de destino',
    noteLabel: 'Nota / tarea / estado',
    notePlaceholder: 'Escriba aquí…',
    save: 'Guardar',
    savedAlert: '¡Guardado en Taskpad!',
    projectLogHint: 'Registro del proyecto',
    binaryFileHint:
      'Este registro del proyecto es un archivo {ext}. Conviértalo a .md para editar completamente en Taskpad, o abra el original desde el explorador de archivos de la pestaña Registro.',
  },

  workspace: {
    overview: 'Resumen',
    plan: 'Plan',
    data: 'Datos',
    methods: 'Métodos',
    writing: 'Redacción',
    archive: 'Archivo',
    log: 'Registro',
  },

  docs: {
    files: 'archivos',
    searchFiles: 'Buscar archivos',
    searchPlaceholder: 'Buscar archivos…',
    noFilesCategory: 'No hay archivos en esta categoría.',
    noFilesSearch: 'Ningún archivo coincide con la búsqueda.',
    groupTabsAria: 'Grupos de documentos',
    groupEyebrow: 'Secciones',
    categoryTabsAria: 'Categorías de documentos',
    subcategoryEyebrow: 'Categorías',
    subfolderTabsAria: 'Subcarpetas de documentos',
    albumsEyebrow: 'Elegir álbum',
    albumFileOne: '1 archivo',
    albumFileMany: '{count} archivos',
    selectFile: 'Seleccione un archivo para previsualizar el contenido extraído o abrir el original.',
    openOriginal: 'Abrir original',
    revealSensitive: 'Mostrar sensible',
    hideSensitive: 'Ocultar sensible',
    sensitiveMasked: 'Contenido sensible — vista previa oculta por defecto.',
    loading: 'Cargando documentos…',
    loadError: 'Error al cargar los documentos.',
    teamDirectory: 'Directorio del equipo',
    filesInSection: '{count} archivos',
  },
};
