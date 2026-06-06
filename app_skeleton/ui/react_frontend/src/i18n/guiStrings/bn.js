/** Bengali GUI strings. */
import en from './en.js';
import { mergeLocale } from '../mergeLocale.js';

export default mergeLocale(en, {
  common: {
    appTitle: 'Farkki ডিজিটাল রিসার্চ নোটপ্যাড',
    searchRegistry: 'রেজিস্ট্রি অনুসন্ধান করুন...',
    mainNavAria: 'ল্যাবের প্রধান বিভাগসমূহ',
    user: 'ব্যবহারকারী:',
    api: 'API:',
    apiConnected: 'সংযুক্ত',
    apiUnreachable: 'অপ্রাপ্য',
    apiChecking: 'পরীক্ষা হচ্ছে…',
    dbOffline: 'ডাটাবেস অফলাইন',
    themeTitle: 'থিম: {theme}। পরিবর্তন করতে ক্লিক করুন।',
    skipToWorkspace: 'ওয়ার্কস্পেসে যান',
    platformEyebrow: 'Farkki গবেষণা প্ল্যাটফর্ম',
    refresh: 'রিফ্রেশ',
    refreshAria: 'প্রকল্প, দল এবং অডিট ডেটা রিফ্রেশ করুন',
    syncing: 'সিঙ্ক হচ্ছে…',
    ready: 'প্রস্তুত',
    projectsSynced: 'প্রকল্পসমূহ সিঙ্ক হয়েছে',
    syncWarning: 'API অনুপলব্ধ থাকায় ক্যাশ করা প্রকল্প তালিকা ব্যবহার করা হচ্ছে।',
    langLabel: 'ভাষা',
    documentTitleSuffix: 'Farkki Lab Assistant',
  },
  navMain: {
    overview: 'সংক্ষিপ্তসার',
    orders: 'অর্ডার ও সম্পর্কিত তথ্য',
    social: 'সামাজিক ও অন্যান্য',
    data_storage: 'ডেটা ও স্টোরেজ',
    projects_data: 'প্রকল্প ও ডেটা',
    wet_lab: 'ওয়েট-ল্যাব',
    cycif: 'CyCif',
    computational: 'কম্পিউটেশনাল হাব',
    ai_assistant: 'AI ল্যাব সহকারী',
    administration: 'প্রশাসন',
  },
  navSub: {
    overview: {
      get_started: {
        label: 'ল্যাবের সাধারণ তথ্য',
        description:
          'Färkkilä Lab এবং ONCOSYS পরিচিতি — orientation এবং onboarding ফাইল Onboarding & Outboarding অংশে আছে।',
      },
      onboarding: {
        label: 'অনবোর্ডিং ও আউটবোর্ডিং',
        description: 'অরিয়েন্টেশন এবং অনবোর্ডিং/আউটবোর্ডিং চেকলিস্ট।',
      },
      guidelines: {
        label: 'নির্দেশিকা',
        description: 'গবেষণা ও কাজ-সম্পর্কিত ল্যাব নির্দেশিকা।',
      },
      documents_permits: {
        label: 'ডকুমেন্টস ও পারমিটস',
        description: 'পারমিট, ফর্ম, ডেটাশিট এবং হ্যান্ডবুক।',
      },
      personnel: {
        label: 'জনবল',
        description: 'কর্মী রেকর্ড ও সহায়ক ডকুমেন্ট।',
      },
      cleaning: {
        label: 'ল্যাব পরিষ্কার',
        description: 'পরিষ্কার-পরিচ্ছন্নতার সময়সূচি ও রক্ষণাবেক্ষণ নথি।',
      },
      dashboard: {
        label: 'ল্যাব ড্যাশবোর্ড',
        description: 'মেট্রিক্স, টিম, অডিট ট্রেইল এবং প্ল্যাটফর্ম প্রস্তুতি।',
      },
      research: {
        label: 'গবেষণা সামগ্রী',
        description: 'কনফারেন্স উপকরণ, পোস্টার এবং ডিস্কে থাকা প্রকাশনা।',
      },
    },
    orders: {
      billing: {
        label: 'বিলিং ও অর্ডার নির্দেশনা',
        description: 'বিলিং, ভেন্ডর, শিপমেন্ট এবং HUS অর্ডার।',
      },
      archive: {
        label: 'আর্কাইভ',
        description: 'পুরনো অর্ডার, কোট এবং প্রোকিউরমেন্ট আর্কাইভ।',
      },
      orders: {
        label: 'অর্ডার রেজিস্টার',
        description: 'রিএজেন্ট, সিকোয়েন্সিং ও সার্ভিস অর্ডার।',
      },
      related: {
        label: 'সম্পর্কিত রেকর্ড',
        description: 'সংযুক্ত নমুনা, শিপমেন্ট এবং মেটাডেটা।',
      },
    },
    social: {
      lab_parties: {
        label: 'ল্যাব পার্টি',
        description: 'হ্যালোইন, গ্রিলিং পার্টি ও ইভেন্ট পরিকল্পনার ডকুমেন্ট।',
      },
      winter_events: {
        label: 'উইন্টার ডে ও মৌসুমি অনুষ্ঠান',
        description: 'ল্যাবের উইন্টার ডে ছবি ও মৌসুমি সমাবেশ।',
      },
      lab_retreats: {
        label: 'ল্যাব রিট্রিট',
        description: 'রিট্রিট পরিকল্পনা ও Nuuksio রিট্রিট উপকরণ।',
      },
      lab_photos: {
        label: 'ল্যাব ছবি',
        description: 'গ্রুপ ছবি, রিট্রিট অ্যালবাম ও ল্যাব জীবনের ছবি।',
      },
      researcher_visits: {
        label: 'গবেষক ভিজিট',
        description: 'ভিজিটর রেকর্ড এবং হোস্টিং উপকরণ।',
      },
      outreach: {
        label: 'আউটরিচ ও সোশ্যাল মিডিয়া',
        description: 'আউটরিচ ক্যাম্পেইন এবং সোশ্যাল মিডিয়া অ্যাসেট।',
      },
    },
    data_storage: {
      landscape: {
        label: 'স্টোরেজ ল্যান্ডস্কেপ',
        description:
          'ল্যাবের সব স্টোরেজ সিস্টেম — L-drive, P-drive, DataCloud, Google Drive, Allas, Databank — সক্ষমতা ও ভূমিকা সহ।',
      },
      network_drives: {
        label: 'L-drive ও P-drive',
        description: 'UH নেটওয়ার্ক ড্রাইভ: সংবেদনশীল ক্লিনিক্যাল (L) এবং সক্রিয় প্রকল্প স্টোরেজ (P)।',
      },
      datacloud: {
        label: 'DataCloud ও Databank',
        description:
          'বিশ্ববিদ্যালয় সেবা: DataCloud WebDAV /farkkila/ (~10 TB) এবং দীর্ঘমেয়াদি আর্কাইভের জন্য UH Databank।',
      },
      cloud_archive: {
        label: 'CSC Allas',
        description: 'HPC বিশ্লেষণের আগে ডেটাসেট স্টেজিংয়ের জন্য CSC অবজেক্ট স্টোরেজ (~30 TB সক্রিয়)।',
      },
      google_drive: {
        label: 'Google Drive',
        description: 'প্রকল্প লগ, অনবোর্ডিং ডকস এবং সহযোগিতা — নিষ্ক্রিয় প্রকল্প নিয়মিত আর্কাইভ করুন।',
      },
      local_storage: {
        label: 'লোকাল ও এক্সটার্নাল ডিস্ক',
        description: 'ওয়ার্কস্টেশন, cpu1-data, কোল্ড-স্টোরেজ ডিস্ক এবং HUH ক্লিনিক্যাল ডেটাবেস অ্যাক্সেস।',
      },
      guidelines: {
        label: 'নির্দেশিকা ও কর্মপ্রবাহ',
        description:
          'Active → CSC Allas, inactive/published → UH Databank, সংবেদনশীলতা নীতি এবং সোর্স ডকুমেন্ট।',
      },
      tools: {
        label: 'ট্রান্সফার টুলস',
        description:
          'rclone, Lumi-O, allas-conf, Cyberduck, rsync — কখন কোনটি ব্যবহার করবেন এবং সাধারণ ট্রান্সফার প্যাটার্ন।',
      },
      documents: {
        label: 'ল্যাব ডকুমেন্টস',
        description: 'স্টোরেজ-সংক্রান্ত অনবোর্ডিং, পরিষ্কার, IT এবং ইনভেন্টরি ডকুমেন্ট এক জায়গায়।',
      },
    },
    projects_data: {
      portfolio: {
        label: 'প্রকল্প পোর্টফোলিও',
        description: 'প্রকল্প ব্রাউজ করুন এবং ওয়ার্কস্পেস ভিটালস খুলুন।',
      },
      notebook: {
        label: 'জীবন্ত নোটবুক',
        description: 'ল্যাব নোটবুক লগ এবং প্রোটোকল উইকি।',
      },
      decisions: {
        label: 'গবেষণা সিদ্ধান্ত',
        description: 'প্রকল্প জুড়ে আনুষ্ঠানিক সিদ্ধান্ত রেজিস্টার।',
      },
      features: {
        label: 'ফিচার ওয়্যারহাউস',
        description: 'ক্লিনিক্যাল ফিচার ম্যাট্রিক্স ও সাদৃশ্য অনুসন্ধান।',
      },
    },
    wet_lab: {
      files: {
        label: 'ল্যাব ডেটাবেস ফাইল',
        description: 'ডিস্কে থাকা প্রোটোকল, ইনভেন্টরি এবং ওয়েট-ল্যাব ডকুমেন্ট।',
      },
      protocols: {
        label: 'ওয়েট-ল্যাব প্রোটোকল',
        description: 'স্যাম্পল প্রস্তুতি, স্টেইনিং প্রস্তুতি ও QC-এর SOP।',
      },
      tasks: {
        label: 'ওয়েট-ল্যাব টাস্ক',
        description: 'ওয়েট-ল্যাব কাজের জন্য ট্যাগ করা টাস্ক।',
      },
      inventory: {
        label: 'রিএজেন্ট ও প্যানেল',
        description: 'অ্যান্টিবডি প্যানেল ও রিএজেন্ট রেফারেন্স।',
      },
    },
    cycif: {
      pipeline: {
        label: 'ইমেজিং পাইপলাইন',
        description: 'স্টিচিং, সেগমেন্টেশন ও QC ট্রিগার।',
      },
      install: {
        label: 'টুল সেটআপ',
        description: 'Napari, Cylinter এবং ভিউয়ার ইনস্টল।',
      },
      structure: {
        label: 'প্রকল্প কাঠামো',
        description: 't-CycIF ফোল্ডার লেআউট ভ্যালিডেশন।',
      },
      cycif_projects: {
        label: 'স্বতন্ত্র প্রকল্প',
        description: 'প্রকল্পভিত্তিক স্টেইনিং পরিকল্পনা, নোট এবং রান স্প্রেডশিট।',
      },
      cycif_instructions: {
        label: 'নির্দেশনা ও SOPs',
        description: 't-CycIF ওয়ার্কফ্লো নির্দেশনা, টেমপ্লেট এবং পরিকল্পনা ফাইল।',
      },
      cycif_sectioning: {
        label: 'সেকশনিং ও H&E',
        description: 't-CycIF-এর পর সেকশনিং অর্ডার ও H&E স্টেইনিং।',
      },
      cycif_inventory: {
        label: 'অ্যান্টিবডি ইনভেন্টরি',
        description: 'CyCIF অ্যান্টিবডি প্যানেল ও ইনভেন্টরি স্প্রেডশিট।',
      },
      cycif_protocols: {
        label: 'প্রোটোকল ও রিসোর্স',
        description: 'Spatial CycIF প্রোটোকল এবং GeoMx/CycIF রিসোর্স।',
      },
    },
    computational: {
      onboarding: { label: 'অনবোর্ডিং ও ক্রেডেনশিয়াল' },
      lumi: {
        label: 'LUMI HPC',
        description: 'Slurm জব, স্পেশিয়াল টুল ইনস্টল, পাইপলাইন এবং Lumi-O ট্রান্সফার।',
      },
      pouta: {
        label: 'cPouta VMs',
        description: 'ল্যাব ক্লাউড VM, প্রভিশনিং গাইড এবং VM-সাইড conda সেটআপ।',
      },
      roihu: {
        label: 'Roihu',
        description: 'CSC Roihu সুপারকম্পিউটার — কনটেন্ট শীঘ্রই আসছে।',
      },
      troubleshoot: {
        label: 'সমস্যা সমাধান',
        description: 'এনভায়রনমেন্ট ডায়াগনস্টিক ও লগ বিশ্লেষণ।',
      },
      utilities: {
        label: 'ইউটিলিটিজ',
        description: 'ফাইল অপারেশন এবং conda এনভায়রনমেন্ট ম্যানেজমেন্ট।',
      },
      tools: {
        label: 'ল্যাব কম্পিউটেশনাল টুলস',
        description: 'প্রকাশিত ল্যাব সফটওয়্যার — Tribus, CEFIIRA, SPACEstat এবং সংশ্লিষ্ট টুল।',
      },
    },
    ai_assistant: {
      copilot: {
        label: 'চ্যাট কোপাইলট',
        description: 'প্রোটোকল ও প্রকল্প ডকসের উপর RAG প্রশ্নোত্তর।',
      },
      prompts: { label: 'প্রম্পট টেমপ্লেট' },
      ingest: { label: 'ডকুমেন্ট ইনজেস্ট' },
      models: { label: 'মডেল রেজিস্ট্রি' },
    },
    administration: {
      admin: {
        label: 'ব্যবহারকারী ও জব',
        description: 'হেলথ, কানেক্টর, অ্যালাউলিস্ট, ইনজেস্ট জব এবং অথ।',
      },
      connectors: {
        label: 'কানেক্টর ও হেলথ',
        description: 'GET /health এবং /api/platform/connectors readiness।',
      },
    },
  },
  docs: {
    files: 'ফাইল',
    searchFiles: 'ফাইল অনুসন্ধান',
    searchPlaceholder: 'ফাইল অনুসন্ধান করুন…',
    noFilesCategory: 'এই ক্যাটাগরিতে কোনো ফাইল নেই।',
    noFilesSearch: 'আপনার অনুসন্ধানের সাথে কোনো ফাইল মেলেনি।',
    groupTabsAria: 'ডকুমেন্ট গ্রুপ',
    groupEyebrow: 'সেকশন',
    categoryTabsAria: 'ডকুমেন্ট ক্যাটাগরি',
    subcategoryEyebrow: 'ক্যাটাগরি',
    subfolderTabsAria: 'ডকুমেন্ট সাবফোল্ডার',
    albumsEyebrow: 'একটি অ্যালবাম নির্বাচন করুন',
    albumFileOne: '১টি ফাইল',
    albumFileMany: '{count}টি ফাইল',
    selectFile: 'এক্সট্র্যাক্টেড কনটেন্ট প্রিভিউ করতে বা মূল ফাইল খুলতে একটি ফাইল নির্বাচন করুন।',
    openOriginal: 'মূল ফাইল খুলুন',
    revealSensitive: 'সংবেদনশীল দেখান',
    hideSensitive: 'সংবেদনশীল লুকান',
    sensitiveMasked: 'সংবেদনশীল কনটেন্ট — প্রিভিউ ডিফল্টভাবে মাস্ক করা।',
    loading: 'ডকুমেন্ট লোড হচ্ছে…',
    loadError: 'ডকুমেন্ট লোড করতে ব্যর্থ হয়েছে।',
    teamDirectory: 'টিম ডিরেক্টরি',
    filesInSection: '{count}টি ফাইল',
    loadingProject: 'প্রকল্প ফাইল লোড হচ্ছে…',
    noProjectFiles:
      'এই ওয়ার্কস্পেস সেকশনে এখনো কোনো ফাইল নেই। প্রকল্প ফোল্ডার স্ক্যান করুন বা মিল থাকা নম্বরযুক্ত ফোল্ডারে ফাইল যোগ করুন।',
    selectFileEdit: 'প্রিভিউ বা এডিট করতে একটি ফাইল নির্বাচন করুন।',
    editInTaskpad: 'Taskpad-এ এডিট করুন',
    taskpadEditorHint: 'পূর্ণ Monaco এডিটিং, সেভ, প্রুফরিড ও হেডিং টুলের জন্য Taskpad ব্যবহার করুন।',
    spreadsheetOpen: 'স্প্রেডশিট — টেবিল দেখতে মূল ফাইল খুলুন।',
    spreadsheetLoading: 'স্প্রেডশিট লোড হচ্ছে…',
    spreadsheetRepaired: 'ক্ষতিগ্রস্ত বা অ-স্ট্যান্ডার্ড ফাইল থেকে পুনরুদ্ধার করা হয়েছে:',
    spreadsheetTruncated: 'পারফরম্যান্সের জন্য সারি ও কলামের একটি অংশ দেখানো হচ্ছে।',
    spreadsheetEmpty: 'এই স্প্রেডশিটে দৃশ্যমান কোনো সেল নেই।',
    spreadsheetFailed: 'ব্রাউজারে এই স্প্রেডশিট খোলা যায়নি।',
    codeLoading: 'সোর্স ফাইল লোড হচ্ছে…',
    codeFailed: 'সোর্স ফাইল লোড করা যায়নি।',
    noTextPreview: 'টেক্সট প্রিভিউ নেই। মূল ফাইল খুলুন বা PDF থাম্বনেইল বড় করুন।',
    mediaLoading: 'ছবি লোড হচ্ছে…',
    mediaFailed: 'ছবি লোড করা যায়নি।',
    videoLoading: 'ভিডিও লোড হচ্ছে…',
    videoFailed: 'ব্রাউজারে এই ভিডিও চালানো যায়নি।',
    modelLoading: '3D ভিউয়ার লোড হচ্ছে…',
    mediaZoomIn: 'জুম ইন',
    mediaZoomOut: 'জুম আউট',
    mediaFit: 'ভিউতে ফিট করুন',
    mediaActualSize: 'আসল আকার',
    mediaRotate: '৯০° ঘোরান',
    mediaFullscreen: 'ফুলস্ক্রিন',
    mediaPrevious: 'পূর্ববর্তী',
    mediaNext: 'পরবর্তী',
    modelHint: 'টেনে ঘোরান · স্ক্রল করে জুম · ডান-ক্লিক টেনে প্যান',
    modelPlay: 'অ্যানিমেশন চালান',
    modelPause: 'অ্যানিমেশন থামান',
    modelAutoRotate: 'অটো-রোটেট',
    modelReset: 'ভিউ রিসেট',
  },
  taskpad: {
    title: 'Taskpad',
    quickCapture: 'দ্রুত ক্যাপচার',
    projectLog: 'প্রকল্প লগ',
    collapse: 'সংকুচিত',
    close: 'Taskpad সংকুচিত করুন',
    targetArea: 'লক্ষ্য এলাকা',
    noteLabel: 'নোট / টাস্ক / স্ট্যাটাস',
    notePlaceholder: 'এখানে লিখুন…',
    save: 'সংরক্ষণ করুন',
    savedAlert: 'Taskpad-এ সংরক্ষিত হয়েছে!',
    projectLogHint: 'প্রকল্প লগ',
    binaryFileHint:
      'এই প্রকল্প লগটি একটি {ext} ফাইল। পূর্ণ Taskpad এডিটিংয়ের জন্য এটিকে .md-এ রূপান্তর করুন অথবা Log ট্যাব থেকে মূল ফাইল খুলুন।',
  },
  workspace: {
    overview: 'সংক্ষিপ্তসার',
    plan: 'পরিকল্পনা',
    data: 'ডেটা',
    methods: 'পদ্ধতি',
    writing: 'লিখন',
    archive: 'আর্কাইভ',
    log: 'লগ',
  },
  catGroup: {
    billing: 'বিলিং ও অর্থনীতি',
    logistics: 'লজিস্টিকস ও শিপিং',
    other: 'অন্যান্য',
    guidelines: 'ল্যাব নির্দেশিকা',
    onboarding: 'অনবোর্ডিং ও আউটবোর্ডিং',
    cleaning: 'ল্যাব পরিষ্কার',
    personnel: 'জনবল',
    research: 'গবেষণা সামগ্রী',
    permits: 'পারমিট ও কমপ্লায়েন্স',
    reference: 'রেফারেন্স ও যন্ত্রপাতি',
  },
});
