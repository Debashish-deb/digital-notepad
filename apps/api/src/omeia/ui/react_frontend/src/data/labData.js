import asset_hero_png from "../assets/hero.png";
import { newsData, newsFallbackImage } from "./newsData.js";
import { coverImages } from "./coverImages.js";
import { labMembers } from "./labMembers.js";
import { researchTopics } from "./researchTopics.js";

export { coverImages } from "./coverImages.js";
export { newsData, newsFallbackImage } from "./newsData.js";
export { labMembers } from "./labMembers.js";
export { researchTopics } from "./researchTopics.js";

// Use existing hero image as valid build fallbacks
export const eventCoverImage = asset_hero_png;
export const asset_research_cefiira_png = asset_hero_png;
export const asset_research_tribus_cover_png = asset_hero_png;
export const asset_research_tribus_png = asset_hero_png;
export const asset_research_optimized_gt_png = asset_hero_png;

export const alumniData = [
  {
    "title": "Postdoctoral Researchers",
    "members": [
      {
        "name": "Ashwini Nagaraj, PhD",
        "focus": "Ashwini Nagaraj's research focused on establishing high-grade serous ovarian cancer patient-derived immunocompetent models for functional testing of immunotherapeutic agents."
      },
      {
        "name": "Elina Pietilä, PhD",
        "focus": "Elina Pietilä worked on precision medicine in high-grade serous ovarian cancer using immunocompetent patient-derived ex-vivo cultures."
      },
      {
        "name": "Julia Casado, PhD",
        "focus": "Julia Casado's research focused on the tumor microenvironment analysis from highly-multiplexed images, developing algorithms for cell type and state identification."
      }
    ]
  },
  {
    "title": "Doctoral Researchers",
    "members": [
      {
        "name": "Fernando Perez, PhD",
        "focus": "Fernando Perez's research focused on identifying genomic and tumor microenvironment biomarkers that predict chemotherapy response in ovarian cancer."
      }
    ]
  },
  {
    "title": "Staff",
    "members": [
      {
        "name": "Aino Elomaa, BSc",
        "focus": "Aino Elomaa coordinated the ONCOSYS-Ova sample collection as Laboratory and Clinical Sample Coordinator."
      },
      {
        "name": "Angéla Szabó, MSc",
        "focus": "Angéla Szabó's work focused on cell-type calling and image analysis."
      }
    ]
  },
  {
    "title": "Other Students",
    "members": [
      {
        "name": "Abhilash VA, MSc",
        "focus": "Abhilash VA performed evaluations of immune cell-specific functional responses in patient-derived immunocompetent cultures."
      },
      {
        "name": "Aditi Sirsikar, BSc",
        "focus": "Aditi Sirsikar's responsibilities included analyzing multi-dimensional drug response data from patient-derived immunocompetent cultures."
      },
      {
        "name": "Alva Grönholm, BSc",
        "focus": "Alva Grönholm focused on performing bioinformatic analyses for the cell cycle project on highly multiplexed imaging data."
      },
      {
        "name": "Arttu Peltola, BSc",
        "focus": "Arttu Peltola contributed to improving the image processing pipeline by developing a metric and framework to evaluate and optimize segmentation performance."
      },
      {
        "name": "Assel Kalmenova, MSc",
        "focus": "Assel Kalmenova worked on the expansion of high-grade serous ovarian cancer organoids and analysis of the tumor microenvironment."
      },
      {
        "name": "Eveliina Holappa, BSc",
        "focus": "Eveliina Holappa's tasks focused on patient sample processing, 3D cell culture, and flow cytometry experiments."
      },
      {
        "name": "Foteini Chamchougia, MSc",
        "focus": "Foteini Chamchougia was involved in multiple projects analyzing patient-derived samples using spatial techniques like tCycIF."
      },
      {
        "name": "Gayani Anandagoda, BSc",
        "focus": "Gayani Anandagoda applied bioinformatics and machine learning tools to spatial transcriptomic data to analyze the tumor microenvironment."
      },
      {
        "name": "Lina Maltrovsky, BSc",
        "focus": "Lina Maltrovsky focused on combining highly multiplexed imaging with proteomics analysis."
      },
      {
        "name": "Matías Aiskovich, MSc",
        "focus": "Matías Aiskovich applied bioinformatics and machine learning to tumor omics data, focusing on computer vision models for multiplexed imaging."
      },
      {
        "name": "Olavi Goussev, MSc (Tech)",
        "focus": "Olavi Goussev focused on the development of machine learning processes and feature engineering for analyzing tumor microenvironments."
      },
      {
        "name": "Panagiotis Lilis, BSc",
        "focus": "Panagiotis Lilis specialized in cell culture and establishing long-term 3D ovarian tumor organoid cultures."
      },
      {
        "name": "Sarah Wolf, BSc",
        "focus": "Sarah Wolf supported patient sample processing and biobanking, and assisted with drug testing in complex in vitro models of the tumor microenvironment."
      },
      {
        "name": "Teodóra Faragó, MSc",
        "focus": "Teodóra Faragó's tasks consisted of automatic cell-type calling and computational analysis."
      },
      {
        "name": "Venla Kaislo, BSc",
        "focus": "Venla Kaislo's research focused on omics data analysis and multimodal clinical modeling for ovarian cancer."
      }
    ]
  }
];

export const publicationsData = [
  {
    "id": 0,
    "type": "Review",
    "authors": "Junquera A, Färkkilä A.",
    "title": "Tracing cancer progression through interpretable spatial multi-omics.",
    "journal": "Trends in Cancer",
    "details": "Available online 19 Nov 2025. In Press, Corrected Proof. doi: 10.1016/j.trecan.2025.11.002.",
    "year": 2025,
    "doi": "10.1016/j.trecan.2025.11.002"
  },
  {
    "id": 1,
    "type": "Commentary",
    "authors": "Bhatt S, Chhabra Y, Cohen M, Färkkilä A, Goel S, Li G, Romero-Córdoba S.",
    "title": "Navigating life as an early career researcher.",
    "journal": "Trends Cancer",
    "details": "2025 Apr;11(4):261-266. doi: 10.1016/j.trecan.2025.03.006. PMID: 40157857.",
    "year": 2025,
    "doi": "10.1016/j.trecan.2025.03.006"
  },
  {
    "id": 2,
    "type": "Commentary",
    "authors": "Chan EM, Chhabra Y, Dixon KO, Durbin AD, Färkkilä A, Jeyasekharan AD, Keckesova Z, Prensner JR, Wagenblast E, Xie SZ, Zhao D.",
    "title": "Insights on Future Directions in Cancer Research from the 2025 AACR NextGen Stars.",
    "journal": "Cancer Discov",
    "details": "2025 Apr 2;15(4):678-684. doi: 10.1158/2159-8290.CD-25-0239. PMID: 40170536.",
    "year": 2025,
    "doi": "10.1158/2159-8290.CD-25-0239"
  },
  {
    "id": 3,
    "type": "Original Article",
    "authors": "Kang Z, Szabo A, Farago T, Perez F, Junquera A, Shah S, Launonen IM, Anttila E, Casado J, Elias K, Virtanen A, Haltia UM, Färkkilä A.",
    "title": "Tribus: semi-automated discovery of cell identities and phenotypes from multiplexed imaging and proteomic data.",
    "journal": "Bioinformatics",
    "details": "2025 Mar 4;41(3):btaf082. doi: 10.1093/bioinformatics/btaf082. PMID: 39982403; PMCID: PMC11932726.",
    "year": 2025,
    "doi": "10.1093/bioinformatics/btaf082"
  },
  {
    "id": 4,
    "type": "Original Article",
    "authors": "Launonen IM, Pekcan Erkan E, Niemiec I, Junquera A, Hincapie-Otero M, Afenteva D, Liang Z, Salko M, Szabo A, Perez F, Falco MM, Li Y, Micoli G, Nagaraj A, Haltia UM, Kahelin E, Oikkonen J, Hynninen J, Virtanen A, Nirmal AJ, Vallius T, Hautaniemi S, Sorger P, Vähärautio A, Färkkilä A.",
    "title": "Chemotherapy induces myeloid-driven spatially confined T cell exhaustion in ovarian cancer.",
    "journal": "Cancer Cell",
    "details": "2024;42(12):2045–2063.e10.",
    "year": 2024,
    "doi": "10.1016/j.ccell.2024.11.005"
  },
  {
    "id": 5,
    "type": "Original Article",
    "authors": "Kozłowska E, Haltia UM, Puszynski K, Färkkilä A.",
    "title": "Mathematical modeling framework enhances clinical trial design for maintenance treatment in oncology.",
    "journal": "Sci Rep",
    "details": "2024 Nov;14(1):29721. doi: 10.1038/s41598-024-80768-6. PMID: 39613825.",
    "year": 2024,
    "doi": "10.1038/s41598-024-80768-6"
  },
  {
    "id": 6,
    "type": "Original Article",
    "authors": "Konstantinopoulos PA, Cheng SC, Lee EK, da Costa AABA, Gulhan D, Wahner Hendrickson AE, Kochupurakkal B, Kolin DL, Kohn EC, Liu JF, Penson RT, Stover EH, Curtis J, Sawyer H, Polak M, Chowdhury D, D'Andrea AD, Färkkilä A, Shapiro GI, Matulonis UA.",
    "title": "Randomized Phase II Study of Gemcitabine With or Without ATR Inhibitor Berzosertib in Platinum-Resistant Ovarian Cancer.",
    "journal": "JCO Precis Oncol",
    "details": "2024 Apr;8:e2300635. doi: 10.1200/PO.23.00635.",
    "year": 2024,
    "doi": "10.1200/PO.23.00635"
  },
  {
    "id": 7,
    "type": "Original Article",
    "authors": "Dai J, Zheng S, Falco MM, Bao J, Eriksson J, Pikkusaari S, Forsten S, Jiang J, Wang W, Gao L, Perez F, Dufva O, Saeed K, Wang Y, Amiryousefi A, Färkkilä A, Mustjoki S, Kauppi L, Tang J, Vaharautio A.",
    "title": "Tracing back primed resistance in cancer via sister cells.",
    "journal": "Nat Commun",
    "details": "2024 Feb;15(1):1158. doi: 10.1038/s41467-024-45478-7.",
    "year": 2024,
    "doi": "10.1038/s41467-024-45478-7"
  },
  {
    "id": 8,
    "type": "Original Article",
    "authors": "Hetemaki I, Sarkkinen J, Heikkila N, Drechsel K, Mayranpaa MI, Färkkilä A, Laakso S, Makitie O, Arstila TP, Kekalainen E.",
    "title": "Dysregulated germinal center reaction with expanded T follicular helper cells in autoimmune polyendocrinopathy-candidiasis-ectodermal dystrophy lymph nodes.",
    "journal": "J Allergy Clin Immunol",
    "details": "2023 Dec;151(6):1564–1577. doi: 10.1016/j.jaci.2023.12.004.",
    "year": 2023,
    "doi": "10.1016/j.jaci.2023.12.004"
  },
  {
    "id": 9,
    "type": "Review",
    "authors": "Launonen IM, Vähärautio A, Färkkilä A.",
    "title": "The Emerging Role of the Single-Cell and Spatial Tumor Microenvironment in High-Grade Serous Ovarian Cancer.",
    "journal": "Cold Spring Harb Perspect Med",
    "details": "2023 Oct;13(10):a041314. doi: 10.1101/cshperspect.a041314.",
    "year": 2023,
    "doi": "10.1101/cshperspect.a041314"
  },
  {
    "id": 10,
    "type": "Original Article",
    "authors": "Andersson N, Haltia UM, Färkkilä A, Wong SC, Eloranta K, Wilson DB, Unkila-Kallio L, Pihlajoki M, Kyrönlahti A, Heikinheimo M.",
    "title": "Analysis of Non-Relapsed and Relapsed Adult Type Granulosa Cell Tumors Suggests Stable Transcriptomes during Tumor Progression.",
    "journal": "Curr Issues Mol Biol",
    "details": "2022 Jan;44(2):686–698. doi: 10.3390/cimb44020048.",
    "year": 2022,
    "doi": "10.3390/cimb44020048"
  },
  {
    "id": 11,
    "type": "Original Article",
    "authors": "Chae CS, Sandoval TA, Hwang SM, Park ES, Giovanelli P, Awasthi D, Salvagno C, Emmanuelli A, Tan C, Chaudhary V, Casado J, Kossenkov AV, Song M, Barrat FJ, Holcomb K, Romero-Sandoval EA, Zamarin D, Pépin D, D'Andrea AD, Färkkilä A, Cubillos-Ruiz JR.",
    "title": "Tumor-Derived Lysophosphatidic Acid Blunts Protective Type I Interferon Responses in Ovarian Cancer.",
    "journal": "Cancer Discov",
    "details": "2022 Aug;12(8):1904–1921. doi: 10.1158/2159-8290.CD-21-1181.",
    "year": 2022,
    "doi": "10.1158/2159-8290.CD-21-1181"
  },
  {
    "id": 12,
    "type": "Original Article",
    "authors": "Launonen IM, Lyytikainen N, Casado J, Anttila EA, Szabo A, Haltia UM, Jacobson CA, Lin JR, Maliga Z, Howitt BE, Strickland KC, Santagata S, Elias K, D'Andrea AD, Konstantinopoulos PA, Sorger PK, Färkkilä A.",
    "title": "Single-cell tumor-immune microenvironment of BRCA1/2 mutated high-grade serous ovarian cancer.",
    "journal": "Nat Commun",
    "details": "2022 Feb;13(1):835. doi: 10.1038/s41467-022-28389-3.",
    "year": 2022,
    "doi": "10.1038/s41467-022-28389-3"
  },
  {
    "id": 13,
    "type": "Original Article",
    "authors": "Duraiswamy J, Turrini R, Minasyan A, Barras D, Crespo I, Grimm AJ, Casado J, Genolet R, Benedetti F, Wicky A, Ioannidou K, Castro W, Neal C, Moriot A, Renaud-Tissot S, Anstett V, Fahr N, Tanyi JL, Eiva MA, Jacobson CA, Montone KT, Westergaard MCW, Svane IM, Kandalaft LE, Delorenzi M, Sorger PK, Färkkilä A, Michielin O, Zoete V, Carmona SJ, Foukas PG, Powell DJ Jr, Rusakiewicz S, Doucey MA, Dangaj Laniti D, Coukos G.",
    "title": "Myeloid antigen-presenting cell niches sustain antitumor T cells and license PD-1 blockade via CD28 costimulation.",
    "journal": "Cancer Cell",
    "details": "2021 Dec;39(12):1623–1642.e20. doi: 10.1016/j.ccell.2021.10.008.",
    "year": 2021,
    "doi": "10.1016/j.ccell.2021.10.008"
  },
  {
    "id": 14,
    "type": "Original Article",
    "authors": "Zhou J, Gelot C, Pantelidou C, Li A, Yücel H, Davis RE, Färkkilä A, Kochupurakkal B, Syed A, Shapiro GI, Tainer JA, Blagg BSJ, Ceccaldi R, D'Andrea AD.",
    "title": "A first-in-class Polymerase Theta Inhibitor selectively targets Homologous-Recombination-Deficient Tumors.",
    "journal": "Nat Cancer",
    "details": "2021 Jun;2(6):598–610. doi: 10.1038/s43018-021-00203-x.",
    "year": 2021,
    "doi": "10.1038/s43018-021-00203-x"
  },
  {
    "id": 15,
    "type": "Original Article",
    "authors": "Färkkilä A, Rodríguez A, Oikkonen J, Gulhan DC, Nguyen H, Domínguez J, Ramos S, Mills CE, Pérez-Villatoro F, Lazaro JB, Zhou J, Clairmont CS, Moreau LA, Park PJ, Sorger PK, Hautaniemi S, Frias S, D'Andrea AD.",
    "title": "Heterogeneity and Clonal Evolution of Acquired PARP Inhibitor Resistance in TP53- and BRCA1-Deficient Cells.",
    "journal": "Cancer Res",
    "details": "2021 May;81(10):2774–2787. doi: 10.1158/0008-5472.CAN-20-2912.",
    "year": 2021,
    "doi": "10.1158/0008-5472.CAN-20-2912"
  },
  {
    "id": 16,
    "type": "Original Article",
    "authors": "Iyer S, Zhang S, Yucel S, Horn H, Smith SG, Reinhardt F, Hoefsmit E, Assatova B, Casado J, Meinsohn MC, Barrasa MI, Bell GW, Pérez-Villatoro F, Huhtinen K, Hynninen J, Oikkonen J, Galhenage PM, Pathania S, Hammond PT, Neel BG, Färkkilä A, Pépin D, Weinberg RA.",
    "title": "Genetically Defined Syngeneic Mouse Models of Ovarian Cancer as Tools for the Discovery of Combination Immunotherapy.",
    "journal": "Cancer Discov",
    "details": "2021 Feb;11(2):384–407. doi: 10.1158/2159-8290.CD-20-0818.",
    "year": 2021,
    "doi": "10.1158/2159-8290.CD-20-0818"
  },
  {
    "id": 17,
    "type": "Original Article",
    "authors": "Casado J, Lehtonen O, Rantanen V, Kaipio K, Pasquini L, Häkkinen A, Petrucci E, Hynninen J, Hietanen S, Carpén O, Biffoni M, Färkkilä A, Hautaniemi S.",
    "title": "Agile workflow for interactive analysis of mass cytometry data.",
    "journal": "Bioinformatics",
    "details": "2021 Jun;37(9):1263–1268. doi: 10.1093/bioinformatics/btaa946.",
    "year": 2021,
    "doi": "10.1093/bioinformatics/btaa946"
  },
  {
    "id": 18,
    "type": "Original Article",
    "authors": "Rodríguez A, Zhang K, Färkkilä A, Filiatrault J, Yang C, Velázquez M, Furutani E, Goldman DC, García de Teresa B, Garza-Mayén G, McQueen K, Sambel LA, Molina B, Torres L, González M, Vadillo E, Pelayo R, Fleming WH, Grompe M, Shimamura A, Hautaniemi S, Greenberger J, Frías S, Parmar K, D'Andrea AD.",
    "title": "MYC Promotes Bone Marrow Stem Cell Dysfunction in Fanconi Anemia.",
    "journal": "Cell Stem Cell",
    "details": "2021 Jan;28(1):33–47.e8. doi: 10.1016/j.stem.2020.09.004.",
    "year": 2021,
    "doi": "10.1016/j.stem.2020.09.004"
  },
  {
    "id": 19,
    "type": "Original Article",
    "authors": "Konstantinopoulos PA, Cheng SC, Wahner Hendrickson AE, Penson RT, Schumer ST, Doyle LA, Lee EK, Duska LR, Crispens MA, Olawaiye AB, Winer IS, Barroilhet LM, Fu S, McHale MT, Schilder RJ, Färkkilä A, Chowdhury D, Curtis J, Quinn RS, Bowes B, D'Andrea AD, Shapiro GI, Matulonis UA.",
    "title": "Berzosertib plus gemcitabine versus gemcitabine alone in platinum-resistant high-grade serous ovarian cancer: a multicentre, open-label, randomised, phase 2 trial.",
    "journal": "Lancet Oncol",
    "details": "2020 Jul;21(7):957–968. doi: 10.1016/S1470-2045(20)30180-7.",
    "year": 2020,
    "doi": "10.1016/S1470-2045(20)30180-7"
  },
  {
    "id": 20,
    "type": "Original Article",
    "authors": "Färkkilä A, Gulhan DC, Casado J, Jacobson CA, Nguyen H, Kochupurakkal B, Maliga Z, Yapp C, Chen YA, Schapiro D, Zhou Y, Graham JR, Dezube BJ, Munster P, Santagata S, Garcia E, Rodig S, Lako A, Chowdhury D, Shapiro GI, Matulonis UA, Park PJ, Hautaniemi S, Sorger PK, Swisher EM, D'Andrea AD, Konstantinopoulos PA.",
    "title": "Immunogenomic profiling determines responses to combined PARP and PD-1 inhibition in ovarian cancer.",
    "journal": "Nat Commun",
    "details": "2020 Mar;11(1):1459. doi: 10.1038/s41467-020-15315-8.",
    "year": 2020,
    "doi": "10.1038/s41467-020-15315-8"
  },
  {
    "id": 21,
    "type": "Original Article",
    "authors": "Parmar K, Kochupurakkal BS, Lazaro JB, Wang ZC, Palakurthi S, Kirschmeier PT, Yang C, Sambel LA, Färkkilä A, Reznichenko E, Reavis HD, Dunn CE, Zou L, Do KT, Konstantinopoulos PA, Matulonis UA, Liu JF, D'Andrea AD, Shapiro GI.",
    "title": "The CHK1 Inhibitor Prexasertib Exhibits Monotherapy Activity in High-Grade Serous Ovarian Cancer Models and Sensitizes to PARP Inhibition.",
    "journal": "Clin Cancer Res",
    "details": "2019 Oct;25(20):6127–6140. doi: 10.1158/1078-0432.CCR-19-0448.",
    "year": 2019,
    "doi": "10.1158/1078-0432.CCR-19-0448"
  },
  {
    "id": 22,
    "type": "Original Article",
    "authors": "Konstantinopoulos PA, Waggoner S, Vidal GA, Mita M, Moroney JW, Holloway R, Van Le L, Sachdev JC, Chapman-Davis E, Colon-Otero G, Penson RT, Matulonis UA, Kim YB, Moore KN, Swisher EM, Färkkilä A, D'Andrea A, Stringer-Reasor E, Wang J, Buerstatte N, Arora S, Graham JR, Bobilev D, Dezube BJ, Munster P.",
    "title": "Single-Arm Phases 1 and 2 Trial of Niraparib in Combination With Pembrolizumab in Patients With Recurrent Platinum-Resistant Ovarian Carcinoma.",
    "journal": "JAMA Oncol",
    "details": "2019 Aug;5(8):1141–1149. doi: 10.1001/jamaoncol.2019.1048.",
    "year": 2019,
    "doi": "10.1001/jamaoncol.2019.1048"
  }
];

export const computationalToolsData = {
  "key": "Computational tools",
  "title": "Computational Tools & Innovations",
  "name": "Computational Tools & Innovations",
  "intro": "At the Färkkilä Lab, our primary focus is on understanding tumor biology. As part of this, we develop and apply computational approaches that help us make sense of complex spatial and multi-omics data. These tools are not an end in themselves, but a way to better explore biological questions and translate findings toward clinical relevance.",
  "tools": [
    {
      "id": "cefiira",
      "name": "CEFIIRA",
      "fullName": "CEll Feature Importance Identification by RAndom-forest",
      "description": "We developed CEFIIRA as a machine learning–based approach to help interpret single-cell spatial atlases of high-grade serous ovarian cancer. This method allows us to identify features that are most relevant within complex datasets, particularly in the context of highly multiplexed imaging. Using this approach, we were able to highlight biologically meaningful signals, such as the potential prognostic role of MHC class II expression in cancer cells. By leveraging random-forest importance scores, CEFIIRA provides a robust framework for identifying critical biomarkers within the tumor-immune microenvironment, facilitating deeper biological insights from spatial multi-omics data.",
      "image": asset_research_cefiira_png,
      "link": "https://aacrjournals.org/cancerdiscovery/article-abstract/doi/10.1158/2159-8290.CD-25-1492/774230/Single-cell-spatial-atlas-of-high-grade-serous?redirectedFrom=fulltext"
    },
    {
      "id": "tribus",
      "name": "Tribus",
      "fullName": "A semi-automated pipeline for cell phenotyping",
      "description": "Tribus is a semi-automated pipeline we developed to support the identification of cell types and phenotypes from multiplexed imaging and spatial proteomics data. It helps streamline the phenotyping process and enables more consistent analysis of cellular organization within the tumor microenvironment. This tool is particularly useful in exploring how different cell populations interact in space, allowing researchers to accurately map the complex architecture of cancer tissues. By automating repetitive aspects of the identification process, Tribus reduces manual effort while maintaining the high precision required for detailed spatial analysis, ultimately helping to reveal the intricate spatial relationships that drive disease progression.",
      "image": asset_research_tribus_png,
      "link": "https://academic.oup.com/bioinformatics/article/41/3/btaf082/8029662"
    },
    {
      "id": "optimized-gt",
      "name": "Optimized Genetic Testing",
      "fullName": "Precision diagnostics for ovarian cancer",
      "description": "In addition to computational tool development, our work has contributed to improving genetic testing strategies for ovarian cancer. These efforts aim to better identify clinically relevant mutations and support treatment decisions through the integration of genomic and clinical data. By optimizing these testing protocols, we help ensure that patients are accurately diagnosed and that their therapy is tailored to their specific molecular profile. This work is essential for the implementation of precision medicine, helping to bridge the gap between scientific discovery and clinical care, and consistently contributing to more personalized and effective approaches to patient outcomes.",
      "image": asset_research_optimized_gt_png,
      "link": "https://www.helsinki.fi/en/news/cancer/new-genetic-test-improves-ovarian-cancer-treatment"
    }
  ],
  "conclusion": "Overall, these approaches reflect our broader goal: to combine biological insight with computational methods in a way that helps us better understand disease and, over time, improve patient outcomes.",
  "images": [
    asset_research_tribus_cover_png
  ]
};

export const thesisData = [
  {
    "id": 1,
    "name": "Aino Elomaa",
    "title": "Incorporating stromal cells into a 3D patient-derived model for immuno-oncology drug testing in ovarian cancer",
    "program": "Master's Programme in Drug Discovery and Development",
    "university": "University of Turku",
    "year": 2025
  },
  {
    "id": 2,
    "name": "Fernando Perez",
    "title": "Tumor microenvironment and genomic biomarkers for precision oncology in high-grade serous ovarian cancer",
    "program": "Doctoral researcher",
    "university": "University of Helsinki",
    "year": 2025
  },
  {
    "id": 3,
    "name": "Alva Grönholm",
    "title": "Profiling of Spatial Tumor Microenvironment Architecture in Highly Multiplexed Images of High-Grade Serous Ovarian Carcinoma",
    "program": "TRANSMED Master's Programme",
    "university": "University of Helsinki",
    "year": 2025
  },
  {
    "id": 4,
    "name": "Lina Maltrovsky",
    "title": "ProteoPicking: bridging tCycIF with precision tissue microdissection for TME proteomic exploration",
    "program": "Biological Chemistry Master's Programme",
    "university": "University of Vienna",
    "year": 2025
  },
  {
    "id": 5,
    "name": "Matias Aiskovich",
    "title": "Mapping Regions of Interest in Ovarian Cancer: A Deep Learning Approach with Multiplexed Imaging",
    "program": "Master's Programme in Life Science Informatics",
    "university": "University of Helsinki",
    "year": 2025
  },
  {
    "id": 6,
    "name": "Angéla Szabó",
    "title": "Accurate Detection of Immune Landscapes in High-Grade Serous Ovarian Cancer: Developing a Pipeline with Integrated Visual Aid for Single-Cell Phenotyping",
    "program": "Master's Programme in Life Science Informatics",
    "university": "University of Helsinki",
    "year": 2024
  },
  {
    "id": 7,
    "name": "Matilda Salko",
    "title": "Patient-derived functional immuno-oncology platform identifies responders to ATR inhibitor and immunotherapy in ovarian cancer",
    "program": "Doctoral researcher",
    "university": "University of Helsinki",
    "year": 2024
  },
  {
    "id": 8,
    "name": "Aleksandra Shabanova",
    "title": "Uncovering Tumor Microenvironment features linked to Clinico-molecular types of Ovarian Cancer using Machine Learning",
    "program": "Master's Programme in Genetics and Molecular Biosciences",
    "university": "University of Helsinki",
    "year": 2024
  },
  {
    "id": 9,
    "name": "Aleksandra Shabanova",
    "title": "Tissue-based Biomarker Investigation Guided by Functional Immuno-oncology Platform in Ovarian Cancer",
    "program": "Master's Programme in Translational Medicine (TRANSMED)",
    "university": "University of Helsinki",
    "year": 2024
  },
  {
    "id": 10,
    "name": "Ella Anttila",
    "title": "HPV ja syövän mikroyhteisön (TME) vaikutus kohdunkaulasyövän syntyyn ja kohdunkaulasyövässä käytetyt immunologiset hoidot",
    "program": "Licentiate of Medicine",
    "university": "University of Oulu",
    "year": 2024
  },
  {
    "id": 11,
    "name": "Abhilash Venganellur Anandakumar",
    "title": "Evaluation of immune cell-specific functional response following single or combinatorial treatment with DNA damaging and immunotherapy agents using patient-derived immunocompetent cultures of High Grade Serous Ovarian Cancer",
    "program": "BS-MS Dual Degree Programme",
    "university": "Indian Institute of Science Education and Research",
    "year": 2024
  },
  {
    "id": 12,
    "name": "Zhihan Liang",
    "title": "Nano-Pick: A Novel Method Enables Spatially Resolved Gene Expression Profiling of Tertiary Lymphoid Structures in Ovarian Cancer",
    "program": "Master's Programme in Translational Medicine (TRANSMED)",
    "university": "University of Helsinki",
    "year": 2024
  },
  {
    "id": 13,
    "name": "Ada Junquera",
    "title": "Integrative methods for investigating spatial biology of the tumor microenvironment",
    "program": "Master's Programme in Translational Medicine (TRANSMED)",
    "university": "University of Helsinki",
    "year": 2023
  },
  {
    "id": 14,
    "name": "Inga-Maria Launonen",
    "title": "Single-cell tumor-immune microenvironment of BRCA1/2 mutated high-grade serous ovarian cancer",
    "program": "Licentiate of Medicine",
    "university": "University of Helsinki",
    "year": 2023
  },
  {
    "id": 15,
    "name": "Ulla-Maija Haltia",
    "title": "Biomarkers and targeted therapies for ovarian granulosa cell tumors",
    "program": "Doctoral Programme in Clinical Research",
    "university": "University of Helsinki",
    "year": 2023
  }
];

// Friendly aliases used by some source components
export const publications = publicationsData;
export const theses = thesisData;
export const highlightedNews = newsData.slice(0, 3);
export const featuredNews = newsData.filter((item) => item.type === 'featured');

// Legacy compatibility aliases used by src/live page modules
export const a = eventCoverImage;
export const b = alumniData;
export const c = coverImages;
export const f = newsFallbackImage;
export const l = labMembers;
export const n = newsData;
export const p = publicationsData;
export const r = researchTopics;
export const s = thesisData;

export default {
  eventCoverImage,
  alumniData,
  coverImages,
  newsFallbackImage,
  labMembers,
  newsData,
  publicationsData,
  researchTopics,
  computationalToolsData,
  thesisData,
};
