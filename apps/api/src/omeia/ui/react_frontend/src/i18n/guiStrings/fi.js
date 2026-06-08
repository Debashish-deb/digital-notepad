/** Finnish GUI strings. */
export default {
  common: {
    appTitle: 'Farkki Digital Research NotePad',
    searchRegistry: 'Hae rekisteristä...',
    mainNavAria: 'Laboratorion pääosiot',
    user: 'Käyttäjä:',
    api: 'API:',
    apiConnected: 'Yhdistetty',
    apiUnreachable: 'Ei tavoitettavissa',
    apiChecking: 'Tarkistetaan…',
    dbOffline: 'Tietokanta offline',
    themeTitle: 'Teema: {theme}. Napsauta vaihtaaksesi.',
    skipToWorkspace: 'Siirry työtilaan',
    platformEyebrow: 'Farkki-tutkimusalusta',
    refresh: 'Päivitä',
    refreshAria: 'Päivitä projekti-, tiimi- ja auditointitiedot',
    syncing: 'Synkronoidaan…',
    ready: 'Valmis',
    projectsSynced: 'Projektit synkronoitu',
    syncWarning: 'Käytetään välimuistissa olevaa projektilistaa, koska API ei ollut käytettävissä.',
    langLabel: 'Kieli',
    documentTitleSuffix: 'Farkki Lab Assistant',
  },

  navMain: {
    overview: 'Yleiskatsaus',
    orders: 'Tilaukset ja niihin liittyvät tiedot',
    social: 'Sosiaalinen ja muu',
    data_storage: 'Data ja tallennus',
    projects_data: 'Projektit ja data',
    wet_lab: 'Märkälaboratorio',
    cycif: 'CyCif',
    computational: 'Laskennallinen keskus',
    ai_assistant: 'AI-laboratorioavustaja',
    administration: 'Hallinta',
  },

  navSub: {
    overview: {
      get_started: {
        label: 'Yleiset laboratoriotiedot',
        description:
          'Johdatus Färkkilä-laboratorioon ja ONCOSYSiin — perehdytys- ja onboarding-tiedostot löytyvät osiosta Perehdytys ja poistuminen.',
      },
      onboarding: {
        label: 'Perehdytys ja poistuminen',
        description: 'Perehdytys- ja poistumistarkistuslistat.',
      },
      guidelines: {
        label: 'Ohjeet',
        description: 'Tutkimus- ja työhön liittyvät laboratorio-ohjeet.',
      },
      documents_permits: {
        label: 'Asiakirjat ja luvat',
        description: 'Luvat, lomakkeet, datalehdet ja käsikirjat.',
      },
      personnel: {
        label: 'Henkilöstö',
        description: 'Henkilöstötiedot ja tukidokumentit.',
      },
      cleaning: {
        label: 'Laboratorion siivous',
        description: 'Siivousaikataulut ja laboratorion ylläpitodokumentit.',
      },
      dashboard: {
        label: 'Laboratorion hallintapaneeli',
        description: 'Mittarit, tiimi, auditointiloki ja alustan valmius.',
      },
      research: {
        label: 'Tutkimusmateriaalit',
        description: 'Konferenssimateriaalit, posterit ja julkaisut levyltä.',
      },
    },
    orders: {
      billing: {
        label: 'Laskutus- ja tilausohjeet',
        description: 'Laskutus, toimittajat, lähetykset ja HUS-tilaukset.',
      },
      archive: {
        label: 'Arkisto',
        description: 'Historialliset tilaukset, tarjoukset ja hankinta-arkistot.',
      },
      orders: {
        label: 'Tilausrekisteri',
        description: 'Reagenssit, sekvensointi- ja palvelutilaukset.',
      },
      related: {
        label: 'Liittyvät tiedot',
        description: 'Linkitetyt näytteet, lähetykset ja metatiedot.',
      },
    },
    social: {
      lab_parties: {
        label: 'Laboratoriojuhlat',
        description: 'Halloween-, grilli- ja muiden juhlien suunnitteludokumentit.',
      },
      winter_events: {
        label: 'Talvipäivä ja kausitapahtumat',
        description: 'Laboratorion talvipäivän kuvat ja kausittaiset tapahtumat.',
      },
      lab_retreats: {
        label: 'Laboratorioretriitit',
        description: 'Retriittien suunnittelu ja Nuuksion retriittimateriaalit.',
      },
      lab_photos: {
        label: 'Laboratoriokuvat',
        description: 'Ryhmäkuvat, retriittialbumit ja arjen kuvat.',
      },
      researcher_visits: {
        label: 'Tutkijavierailut',
        description: 'Vierailijatiedot ja isännöintimateriaalit.',
      },
      outreach: {
        label: 'Tiedotus ja sosiaalinen media',
        description: 'Tiedotuskampanjat ja some-materiaalit.',
      },
    },
    data_storage: {
      landscape: {
        label: 'Tallennusympäristö',
        description:
          'Kaikki labran tallennuspalvelut — L-asema, P-asema, DataCloud, Google Drive, Allas, Databank.',
      },
      network_drives: {
        label: 'L-asema ja P-asema',
        description: 'HY-verkkoasemat: arkaluonteinen kliininen (L) ja aktiiviset projektit (P).',
      },
      datacloud: {
        label: 'DataCloud ja Databank',
        description:
          'Yliopiston palvelut: DataCloud WebDAV /farkkila/ (~10 TB) ja HY Databank pitkäaikaistallennukseen.',
      },
      cloud_archive: {
        label: 'CSC Allas',
        description: 'CSC:n objektitallennus (~30 TB aktiivinen) ennen HPC-analyysiä.',
      },
      google_drive: {
        label: 'Google Drive',
        description: 'Projektilokit, perehdytys ja yhteistyö — arkistoi passiiviset projektit.',
      },
      local_storage: {
        label: 'Paikallinen ja ulkoinen tallennus',
        description: 'Työasemat, cpu1-data, kylmät levyt ja HUS-kliininen tietokanta.',
      },
      guidelines: {
        label: 'Ohjeet ja työnkulku',
        description: 'Active → CSC Allas, inactive/published → HY Databank, arkaluonteisuus ja lähteet.',
      },
      tools: {
        label: 'Siirtotyökalut',
        description: 'rclone, Lumi-O, allas-conf, Cyberduck, rsync — käyttö ja siirtokuviot.',
      },
      documents: {
        label: 'Labradokumentit',
        description: 'Kaikki tallennukseen liittyvät onboarding-, siivous- ja IT-dokumentit.',
      },
    },
    projects_data: {
      portfolio: {
        label: 'Projektiportfolio',
        description: 'Selaa projekteja ja avaa työtilan perustiedot.',
      },
      notebook: {
        label: 'Elävä muistikirja',
        description: 'Laboratoriomuistikirjan lokit ja protokollawiki.',
      },
      decisions: {
        label: 'Tutkimuspäätökset',
        description: 'Virallinen päätösrekisteri projektien välillä.',
      },
      features: {
        label: 'Ominaisuusvarasto',
        description: 'Kliininen ominaisuusmatriisi ja samankaltaisuushaku.',
      },
    },
    wet_lab: {
      files: {
        label: 'Laboratoriotietokannan tiedostot',
        description: 'Protokollat, inventaariot ja märkälaboratorion dokumentit levyltä.',
      },
      protocols: {
        label: 'Märkälaboratorion protokollat',
        description: 'SOP:t näytteen valmisteluun, värjäysvalmisteluun ja laadunvalvontaan.',
      },
      tasks: {
        label: 'Märkälaboratorion tehtävät',
        description: 'Märkälaboratoriotyöhön merkityt tehtävät.',
      },
      inventory: {
        label: 'Reagenssit ja paneelit',
        description: 'Vasta-ainepaneelit ja reagenssiviitteet.',
      },
    },
    cycif: {
      pipeline: {
        label: 'Kuvantamispipeline',
        description: 'Stitching, segmentointi ja laadunvalvonnan käynnistimet.',
      },
      install: {
        label: 'Työkalujen asennus',
        description: 'Napari, Cylinter ja katseluohjelmien asennukset.',
      },
      structure: {
        label: 'Projektirakenne',
        description: 't-CycIF-kansioiden rakenteen validointi.',
      },
      cycif_projects: {
        label: 'Yksittäiset projektit',
        description: 'Projektikohtaiset värjäyssuunnitelmat ja ajotaulukot.',
      },
      cycif_instructions: {
        label: 'Ohjeet ja SOP:t',
        description: 't-CycIF-työnkulun ohjeet, mallit ja suunnittelutiedostot.',
      },
      cycif_sectioning: {
        label: 'Leikkaukset ja H&E',
        description: 'Leikkausmääräykset ja H&E-värjäys t-CycIF:n jälkeen.',
      },
      cycif_inventory: {
        label: 'Vasta-aineinventaario',
        description: 'CyCIF-vasta-ainepaneelit ja inventaariotaulukot.',
      },
      cycif_protocols: {
        label: 'Protokollat ja resurssit',
        description: 'Spatiaaliset CycIF-protokollat ja GeoMx/CycIF-resurssit.',
      },
    },
    computational: {
      onboarding: { label: 'Perehdytys ja tunnistetiedot' },
      lumi: {
        label: 'LUMI-supertietokone',
        description: 'Slurm-työt, työkaluasennukset, pipeline:t ja Lumi-O-siirrot.',
      },
      pouta: {
        label: 'cPouta-virtuaalikoneet',
        description: 'Labran pilvikoneet, käyttöönotto-ohjeet ja VM-condat.',
      },
      roihu: {
        label: 'Roihu',
        description: 'CSC Roihu -supertietokone — sisältö tulossa.',
      },
      troubleshoot: {
        label: 'Vianmääritys',
        description: 'Ympäristödiagnostiikka ja lokianalyysi.',
      },
      utilities: {
        label: 'Apuohjelmat',
        description: 'Tiedosto-operaatiot ja conda-ympäristöjen hallinta.',
      },
      tools: {
        label: 'Laskennalliset labratyökalut',
        description: 'Julkaistut labraohjelmistot — Tribus, CEFIIRA, SPACEstat ja muut spatiaalianalyysityökalut.',
      },
    },
    ai_assistant: {
      copilot: {
        label: 'Chat-avustaja',
        description: 'RAG-kyselyt protokollien ja projektidokumenttien yli.',
      },
      prompts: { label: 'Kehotemallit' },
      ingest: { label: 'Tuo dokumentteja' },
      models: { label: 'Mallirekisteri' },
    },
    administration: {
      admin: {
        label: 'Käyttäjät ja työt',
        description: 'Terveys, liittimet, sallittujen lista, tuontityöt, autentikointi.',
      },
      connectors: {
        label: 'Liittimet ja tila',
        description: 'GET /health ja /api/platform/connectors -valmius.',
      },
    },
  },

  catGroup: {
    billing: 'Laskutus ja talous',
    logistics: 'Logistiikka ja lähetykset',
    other: 'Muu',
    guidelines: 'Laboratorio-ohjeet',
    onboarding: 'Perehdytys ja poistuminen',
    cleaning: 'Laboratorion siivous',
    personnel: 'Henkilöstö',
    research: 'Tutkimusmateriaalit',
    permits: 'Luvat ja vaatimustenmukaisuus',
    reference: 'Viite ja laitteet',
    pharma: 'GSK-asiakirjat',
    archive_finance: 'Laboratorion talous ja tilit',
    archive_procurement: 'Hankintatiedot',
    archive_it: 'IT ja infrastruktuuri',
  },

  cat: {
    biobank: {
      label: 'Biopankkipyynnöt',
      description: 'Biopankkinäyte- ja -datapyynnöt.',
    },
    bsl_forms: {
      label: 'BSL-2-lomakkeet ja -mallit',
      description: 'GMM-lomakkeet ja riskinarviointimallit BSL-2-juuressa.',
    },
    bsl1_2: {
      label: 'BSL-1- ja BSL-2-käsikirjat',
      description: 'Bioturvallisuuskäsikirjat, hätäsuunnitelmat, vakuutukset ja THL-mallit.',
    },
    bsl_drafts: {
      label: 'BSL-luonnokset muokattavaksi',
      description: 'Bioturvallisuuskäsikirjojen ja solusääntöjen luonnokset.',
    },
    bsl_gmo: {
      label: 'GMO-hakemusluonnokset',
      description: 'GMM-hakemus- ja riskinarviointilomakkeet.',
    },
    ethanol: {
      label: 'Etanolilupa (Valvira 2019)',
      description: 'Valvira-luvat, valitukset ja inventaariotiedot.',
    },
    datasheets: {
      label: 'Datalehdet ja käsikirjat',
      description: 'Tuotedatalehdet ja laboratoriokäsikirjat.',
    },
    qiagen: {
      label: 'Qiagen-käsikirjat',
      description: 'Qiagen-pakkauksien käsikirjat ja protokollat.',
    },
    equipment_barcodes: {
      label: 'Laitteiden viivakoodit',
      description: 'Viivakoodikuvat REVCO:lle, inkubaattoreille jne.',
    },
    root_docs: {
      label: 'Yleinen viite',
      description: 'FFPE-artikkelit, huonenumerot ja muut viite-PDF:t.',
    },
    gsk_nov2021: {
      label: 'GSK marraskuu 2021 (GSK3859856B)',
      description: 'Proformalaskut, tulli- ja tarkoituslomakkeet.',
    },
    gsk_filled: {
      label: 'GSK täytetyt lomakkeet (luonnokset)',
      description: 'Täytetyt RFI-lomakkeet — Ashwini ja Anastasiya.',
    },
    gsk_unfilled: {
      label: 'GSK täyttämättömät lomakkeet',
      description: 'Tyhjät Helsingin yliopiston RFI-mallit.',
    },
    gsk_root: {
      label: 'GSK muu',
      description: 'MSDS ja muut GSK-viitetiedostot.',
    },
    research: {
      label: 'Tutkimukseen liittyvät',
      description: 'Tiivistelmät, esitykset, väitöskirjat, kokoukset, apurahat ja sidonnaisuudet.',
    },
    work: {
      label: 'Työhön liittyvät',
      description: 'Lomat, sairauslomat ja päivittäiset työohjeet.',
    },
    orientation: {
      label: 'Perehdytys ja turvallisuus',
      description: 'Perehdytysmateriaalit, orientointi-PDF:t ja Kauppi-laboratorion turvallisuus.',
    },
    contacts: {
      label: 'Yhteystiedot ja menettelyt',
      description: 'Perehdytys-/poistumistarkistuslistat ja tärkeät yhteystiedot.',
    },
    cleaning_20250528: {
      label: 'Siivouspäivä — 28.5.2025',
      description: 'Datan siivouspäivän tehtävät ja varastoyksiköiden kommentit.',
    },
    cleaning_251205: {
      label: 'Siivouspäivä — 5.12.2025',
      description: 'Märkä-, kuiva- ja ulkoisten levyjen siivousinventaariot.',
    },
    roster: {
      label: 'Nykyinen henkilöstö',
      description: 'Aktiivisten laboratorion jäsenten tiedot.',
    },
    hiring: {
      label: 'Rekrytointi',
      description: 'Työpaikkailmoitukset, haastattelumateriaalit ja arviointimatriisit.',
    },
    lab_management: {
      label: 'Laboratorion johtaminen',
      description: 'Johtamisrakenne, roolikuvaukset ja ohjeet.',
    },
    conference: {
      label: 'Konferenssitiivistelmät ja posterit',
      description: 'ESGO, AACR, European Ovarian Cancer Symposium, EMBL jne.',
    },
    phd_apps: {
      label: 'Väitöskirja ja tohtorikoulu',
      description: 'Tohtorikouluhakemukset ja niihin liittyvät materiaalit.',
    },
    peer_review: {
      label: 'Vertaisarviointi',
      description: 'Vertaisarvioitavana olevat artikkelit.',
    },
    presentations: {
      label: 'Esitysten ja posterien arkisto',
      description: 'Arkistoidut esitykset ja posteritiedostot.',
    },
    general_reference: {
      label: 'Yleinen viite',
      description: 'Keskeiset laskutusosoitteet, toimitustiedot ja yliopiston laskulomakkeet.',
    },
    hus_finance: {
      label: 'HUS-talous ja laskutus',
      description: 'HUS-laskutusohjeet, EVO-budjetit ja HUSLAB-tilauslomakkeet.',
    },
    credentials: {
      label: 'Tunnistetiedot ja käyttöoikeudet',
      description: 'Toimittajien verkkosivujen kirjautumistiedot (arkaluontoista).',
    },
    fedex: {
      label: 'FedEx',
      description: 'FedEx-tilitiedot ja arkistoidut rahtikirjat.',
    },
    ups: {
      label: 'UPS',
      description: 'UPS-kuriiriasetukset, kuvakaappaukset ja rahtikirjat.',
    },
    dna_shipments: {
      label: 'DNA-näytelähetykset',
      description: 'Kansainväliset DNA-lähetykset (Kööpenhamina, Myriad, Tanska).',
    },
    us_customs: {
      label: 'Yhdysvaltain tulli ja proforma',
      description: 'USDA-lausunnot, proformalaskut ja tulliesimerkit.',
    },
    other_admin: {
      label: 'Hallinto ja tilat',
      description: 'Huonevaraukset ja muut hallinnolliset viitteet.',
    },
    hus_purchases: {
      label: 'HUS-laboratorion ostot',
      description: 'HUSLAB-tilin ostot ja laboratorion hankintataulukot.',
    },
    fican_funding: {
      label: 'FiCAN South -rahoitus',
      description: 'FiCAN South -ohjelman rahoitus- ja budjettirekisterit.',
    },
    lab_transfers: {
      label: 'Laboratorioiden väliset siirrot',
      description: 'Rahansiirrot ja velkojen selvitykset laboratorioittain.',
    },
    equipment_orders: {
      label: 'Laitetilausten vahvistukset',
      description: 'Toimittajien tilausvahvistukset (Fisher Scientific, ONCOSYS-laitteet jne.).',
    },
    collaboration_orders: {
      label: 'Yhteistyöhankinnat',
      description: 'Laboratorioiden väliset hankinnat (Kauppi, TERVA).',
    },
    purchase_registers: {
      label: 'Ostorekisterit',
      description: 'Historialliset osto-taulukot ja luokittelemattomat rekisterit.',
    },
    computer_orders: {
      label: 'Tietokone- ja IT-tilaukset',
      description: 'Työasematilaukset, Dustin-laskut ja IT-hankintalomakkeet.',
    },
  },

  taskpad: {
    title: 'Taskpad',
    quickCapture: 'Pikakirjaus',
    projectLog: 'Projektiloki',
    collapse: 'Pienennä',
    close: 'Pienennä taskpad',
    targetArea: 'Kohdealue',
    noteLabel: 'Muistiinpano / tehtävä / tila',
    notePlaceholder: 'Kirjoita tähän…',
    save: 'Tallenna',
    savedAlert: 'Tallennettu Taskpadiin!',
    projectLogHint: 'Projektiloki',
    binaryFileHint:
      'Tämä projektiloki on {ext}-tiedosto. Muunna se .md-muotoon täyttääksesi Taskpad-muokkauksen, tai avaa alkuperäinen Lokin tiedostoselaimesta.',
  },

  workspace: {
    overview: 'Yleiskatsaus',
    plan: 'Suunnitelma',
    data: 'Data',
    methods: 'Menetelmät',
    writing: 'Kirjoittaminen',
    archive: 'Arkisto',
    log: 'Loki',
  },

  docs: {
    files: 'tiedostoa',
    searchFiles: 'Hae tiedostoja',
    searchPlaceholder: 'Hae tiedostoja…',
    noFilesCategory: 'Ei tiedostoja tässä kategoriassa.',
    noFilesSearch: 'Haku ei tuottanut tuloksia.',
    groupTabsAria: 'Dokumenttiryhmät',
    groupEyebrow: 'Osat',
    categoryTabsAria: 'Dokumenttikategoriat',
    subcategoryEyebrow: 'Kategoriat',
    subfolderTabsAria: 'Dokumenttialikansiot',
    albumsEyebrow: 'Valitse albumi',
    albumFileOne: '1 tiedosto',
    albumFileMany: '{count} tiedostoa',
    selectFile: 'Valitse tiedosto esikatsellaksesi poimittua sisältöä tai avataksesi alkuperäisen.',
    openOriginal: 'Avaa alkuperäinen',
    revealSensitive: 'Näytä arkaluontoinen',
    hideSensitive: 'Piilota arkaluontoinen',
    sensitiveMasked: 'Arkaluontoinen sisältö — esikatselu peitetty oletuksena.',
    loading: 'Ladataan dokumentteja…',
    loadError: 'Dokumenttien lataus epäonnistui.',
    teamDirectory: 'Tiimihakemisto',
    filesInSection: '{count} tiedostoa',
  },
};
