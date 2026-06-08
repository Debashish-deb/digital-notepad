/** Swedish GUI strings. */
import en from './en.js';
import { mergeLocale } from '../mergeLocale.js';

export default mergeLocale(en, {
  common: {
    appTitle: 'Farkki Digital Research NotePad',
    searchRegistry: 'Sök i registret...',
    mainNavAria: 'Laboratoriets huvudsektioner',
    user: 'Användare:',
    api: 'API:',
    apiConnected: 'Ansluten',
    apiUnreachable: 'Ej nåbar',
    apiChecking: 'Kontrollerar…',
    dbOffline: 'Databas offline',
    themeTitle: 'Tema: {theme}. Klicka för att byta.',
    skipToWorkspace: 'Hoppa till arbetsytan',
    platformEyebrow: 'Farkki-forskningsplattform',
    refresh: 'Uppdatera',
    refreshAria: 'Uppdatera projekt-, team- och revisionsdata',
    syncing: 'Synkroniserar…',
    ready: 'Klar',
    projectsSynced: 'Projekt synkroniserade',
    syncWarning: 'Använder cachad projektlista eftersom API:et inte var tillgängligt.',
    langLabel: 'Språk',
    documentTitleSuffix: 'Farkki Lab Assistant',
  },

  navMain: {
    overview: 'Översikt',
    orders: 'Beställningar och relaterad information',
    social: 'Socialt och övrigt',
    data_storage: 'Data och lagring',
    projects_data: 'Projekt och data',
    wet_lab: 'Våtlaboratorium',
    cycif: 'CyCif',
    computational: 'Beräkningsnav',
    ai_assistant: 'AI-labbassistent',
    administration: 'Administration',
  },

  navSub: {
    overview: {
      get_started: {
        label: 'Allmän labbinformation',
        description:
          'Introduktion till Färkkilä-labbet och ONCOSYS — orienterings- och introduktionsfiler finns under Introduktion och avslut.',
      },
      onboarding: {
        label: 'Introduktion och avslut',
        description: 'Orienterings- och introduktions-/avslutningschecklistor.',
      },
      guidelines: {
        label: 'Riktlinjer',
        description: 'Forsknings- och arbetsrelaterade labbriktlinjer.',
      },
      documents_permits: {
        label: 'Dokument och tillstånd',
        description: 'Tillstånd, formulär, datablad och handböcker.',
      },
      personnel: {
        label: 'Personal',
        description: 'Personalregister och stöddokument.',
      },
      cleaning: {
        label: 'Labbstädning',
        description: 'Städscheman och dokument för labbunderhåll.',
      },
      dashboard: {
        label: 'Labböversikt',
        description: 'Mätvärden, team, revisionslogg och plattformsberedskap.',
      },
      research: {
        label: 'Forskningsmaterial',
        description: 'Konferensmaterial, posters och publikationer på disk.',
      },
    },
    orders: {
      billing: {
        label: 'Fakturerings- och beställningsinstruktioner',
        description: 'Fakturering, leverantörer, leveranser och HUS-beställningar.',
      },
      archive: {
        label: 'Arkiv',
        description: 'Historiska beställningar, offerter och upphandlingsarkiv.',
      },
      orders: {
        label: 'Beställningsregister',
        description: 'Reagens, sekvensering och tjänstebeställningar.',
      },
      related: {
        label: 'Relaterade poster',
        description: 'Länkade prover, leveranser och metadata.',
      },
    },
    social: {
      lab_parties: {
        label: 'Labbkalas',
        description: 'Halloween-, grill- och andra festplaneringsdokument.',
      },
      winter_events: {
        label: 'Vinterdag och säsongsevenemang',
        description: 'Bilder från labbens vinterdag och säsongssammankomster.',
      },
      lab_retreats: {
        label: 'Labbretreater',
        description: 'Retreatplanering och material från Nuuksio-retreater.',
      },
      lab_photos: {
        label: 'Labbilder',
        description: 'Gruppbilder, retreatalbum och bilder från labblivet.',
      },
      researcher_visits: {
        label: 'Forskarbesök',
        description: 'Besöksregister och värdskapsmaterial.',
      },
      outreach: {
        label: 'Utåtriktat arbete och sociala medier',
        description: 'Utåtriktade kampanjer och material för sociala medier.',
      },
    },
    data_storage: {
      landscape: {
        label: 'Lagringsöversikt',
        description:
          'Alla labblagringssystem — L-enhet, P-enhet, DataCloud, Google Drive, Allas, Databank — med kapacitet och roller.',
      },
      network_drives: {
        label: 'L-enhet och P-enhet',
        description: 'UH-nätverksenheter: känslig klinisk data (L) och aktiv projektlagring (P).',
      },
      datacloud: {
        label: 'DataCloud och Databank',
        description:
          'Universitetstjänster: DataCloud WebDAV /farkkila/ (~10 TB) och UH Databank för långtidsarkiv.',
      },
      cloud_archive: {
        label: 'CSC Allas',
        description: 'CSC-objektlagring (~30 TB aktiv) för dataset innan HPC-analys.',
      },
      google_drive: {
        label: 'Google Drive',
        description:
          'Projektloggar, introduktionsdokument och samarbete — arkivera inaktiva projekt regelbundet.',
      },
      local_storage: {
        label: 'Lokal och extern lagring',
        description:
          'Arbetsstationer, cpu1-data, kallagringsdiskar och HUH klinisk databasåtkomst.',
      },
      guidelines: {
        label: 'Riktlinjer och arbetsflöde',
        description:
          'Aktiv → CSC Allas, inaktiv/publicerad → UH Databank, känslighetsregler och källdokument.',
      },
      tools: {
        label: 'Överföringsverktyg',
        description:
          'rclone, Lumi-O, allas-conf, Cyberduck, rsync — när varje används och vanliga överföringsmönster.',
      },
      documents: {
        label: 'Labb dokument',
        description:
          'All lagringsrelaterad introduktion, städning, IT och inventeringsdokument på ett ställe.',
      },
    },
    projects_data: {
      portfolio: {
        label: 'Projektportfölj',
        description: 'Bläddra bland projekt och öppna arbetsytans grunddata.',
      },
      notebook: {
        label: 'Levande anteckningsbok',
        description: 'Labbanteckningsloggar och protokollwiki.',
      },
      decisions: {
        label: 'Forskningsbeslut',
        description: 'Formellt beslutsregister över projekt.',
      },
      features: {
        label: 'Funktionslager',
        description: 'Klinisk funktionsmatris och likhetssökning.',
      },
    },
    wet_lab: {
      files: {
        label: 'Labb databasfiler',
        description: 'Protokoll, inventarier och våtlabb dokument på disk.',
      },
      protocols: {
        label: 'Våtlabbprotokoll',
        description: 'SOP:er för provförberedelse, färgningsförberedelse och QC.',
      },
      tasks: {
        label: 'Våtlabbuppgifter',
        description: 'Uppgifter taggade för våtlabbarbete.',
      },
      inventory: {
        label: 'Reagens och paneler',
        description: 'Antikroppspaneler och reagensreferenser.',
      },
    },
    cycif: {
      pipeline: {
        label: 'Bildpipeline',
        description: 'Stitching, segmentering och QC-utlösare.',
      },
      install: {
        label: 'Verktygsinstallation',
        description: 'Installation av Napari, Cylinter och visningsprogram.',
      },
      structure: {
        label: 'Projektstruktur',
        description: 'Validering av t-CycIF-mappstruktur.',
      },
      cycif_projects: {
        label: 'Enskilda projekt',
        description: 'Projektspecifika färgningsplaner, anteckningar och körningskalkylblad.',
      },
      cycif_instructions: {
        label: 'Instruktioner och SOP:er',
        description: 't-CycIF-arbetsflödesinstruktioner, mallar och planeringsfiler.',
      },
      cycif_sectioning: {
        label: 'Sektionering och H&E',
        description: 'Sektioneringsorder och H&E-färgning efter t-CycIF.',
      },
      cycif_inventory: {
        label: 'Antikroppsinventarie',
        description: 'CyCIF-antikroppspaneler och inventeringskalkylblad.',
      },
      cycif_protocols: {
        label: 'Protokoll och resurser',
        description: 'Spatiala CycIF-protokoll och GeoMx/CycIF-resurser.',
      },
    },
    computational: {
      onboarding: { label: 'Introduktion och inloggningar' },
      lumi: {
        label: 'LUMI HPC',
        description: 'Slurm-jobb, spatiala verktygsinstallationer, pipelines och Lumi-O-överföringar.',
      },
      pouta: {
        label: 'cPouta VM:er',
        description: 'Labbmolnets virtuella maskiner, etableringsguider och conda på VM.',
      },
      roihu: {
        label: 'Roihu',
        description: 'CSC Roihu-superdator — innehåll kommer snart.',
      },
      troubleshoot: {
        label: 'Felsökning',
        description: 'Miljödiagnostik och logganalys.',
      },
      utilities: {
        label: 'Verktyg',
        description: 'Filoperationer och hantering av conda-miljöer.',
      },
      tools: {
        label: 'Labbets beräkningsverktyg',
        description: 'Publicerad labbprogramvara — Tribus, CEFIIRA, SPACEstat och relaterade spatiala analysverktyg.',
      },
    },
    ai_assistant: {
      copilot: {
        label: 'Chattassistent',
        description: 'RAG-frågor över protokoll och projektdokument.',
      },
      prompts: { label: 'Promptmallar' },
      ingest: { label: 'Importera dokument' },
      models: { label: 'Modellregister' },
    },
    administration: {
      admin: {
        label: 'Användare och jobb',
        description: 'Hälsa, kopplingar, tillåtelselista, importjobb, autentisering.',
      },
      connectors: {
        label: 'Kopplingar och hälsa',
        description: 'GET /health och /api/platform/connectors-beredskap.',
      },
    },
  },

  taskpad: {
    title: 'Taskpad',
    quickCapture: 'Snabbanteckning',
    projectLog: 'Projektlogg',
    collapse: 'Minimera',
    close: 'Minimera taskpad',
    targetArea: 'Målområde',
    noteLabel: 'Anteckning / uppgift / status',
    notePlaceholder: 'Skriv här…',
    save: 'Spara',
    savedAlert: 'Sparat i Taskpad!',
    projectLogHint: 'Projektlogg',
    binaryFileHint:
      'Denna projektlogg är en {ext}-fil. Konvertera den till .md för full Taskpad-redigering, eller öppna originalet från Logg-flikens filbläddrare.',
  },

  workspace: {
    overview: 'Översikt',
    plan: 'Plan',
    data: 'Data',
    methods: 'Metoder',
    writing: 'Skrivande',
    archive: 'Arkiv',
    log: 'Logg',
  },

  docs: {
    files: 'filer',
    searchFiles: 'Sök filer',
    searchPlaceholder: 'Sök filer…',
    noFilesCategory: 'Inga filer i denna kategori.',
    noFilesSearch: 'Inga filer matchar din sökning.',
    groupTabsAria: 'Dokumentgrupper',
    groupEyebrow: 'Sektioner',
    categoryTabsAria: 'Dokumentkategorier',
    subcategoryEyebrow: 'Kategorier',
    subfolderTabsAria: 'Dokumentundermappar',
    albumsEyebrow: 'Välj ett album',
    albumFileOne: '1 fil',
    albumFileMany: '{count} filer',
    selectFile: 'Välj en fil för att förhandsgranska extraherat innehåll eller öppna originalet.',
    openOriginal: 'Öppna original',
    revealSensitive: 'Visa känsligt',
    hideSensitive: 'Dölj känsligt',
    sensitiveMasked: 'Känsligt innehåll — förhandsgranskning maskerad som standard.',
    loading: 'Laddar dokument…',
    loadError: 'Kunde inte ladda dokument.',
    teamDirectory: 'Teamkatalog',
    filesInSection: '{count} filer',
    loadingProject: 'Laddar projektfiler…',
    noProjectFiles:
      'Inga filer i denna arbetsytsektion ännu. Skanna projektmappen eller lägg till filer under motsvarande numrerad mapp (t.ex. 2_Methods & Experiments).',
    selectFileEdit: 'Välj en fil att förhandsgranska eller redigera.',
    editInTaskpad: 'Redigera i Taskpad',
    taskpadEditorHint:
      'Använd Redigera i Taskpad för full Monaco-redigering med spara, korrekturläsning och rubrikverktyg.',
    spreadsheetOpen: 'Kalkylblad — öppna originalfilen för att visa tabeller.',
    spreadsheetLoading: 'Laddar kalkylblad…',
    spreadsheetRepaired: 'Återställt från en skadad eller icke-standardfil:',
    spreadsheetTruncated: 'Visar en delmängd av rader och kolumner för prestanda.',
    spreadsheetEmpty: 'Detta kalkylblad har inga synliga celler.',
    spreadsheetFailed: 'Kunde inte öppna detta kalkylblad i webbläsaren.',
    codeLoading: 'Laddar källfil…',
    codeFailed: 'Kunde inte ladda källfil.',
    noTextPreview: 'Ingen textförhandsgranskning. Öppna originalfilen eller expandera PDF-miniatyren.',
    mediaLoading: 'Laddar bild…',
    mediaFailed: 'Kunde inte ladda bild.',
    videoLoading: 'Laddar video…',
    videoFailed: 'Kunde inte spela upp denna video i webbläsaren.',
    modelLoading: 'Laddar 3D-visare…',
    mediaZoomIn: 'Zooma in',
    mediaZoomOut: 'Zooma ut',
    mediaFit: 'Anpassa till vy',
    mediaActualSize: 'Faktisk storlek',
    mediaRotate: 'Rotera 90°',
    mediaFullscreen: 'Helskärm',
    mediaPrevious: 'Föregående',
    mediaNext: 'Nästa',
    modelHint: 'Dra för att rotera · Scrolla för att zooma · Högerklicka och dra för att panorera',
    modelPlay: 'Spela upp animation',
    modelPause: 'Pausa animation',
    modelAutoRotate: 'Autorotera',
    modelReset: 'Återställ vy',
  },
});
