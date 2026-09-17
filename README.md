# CeyNews - A Sri Lankan Trilingual News Corpus

**CeyNews** is the largest trilingual news corpus for Sri Lanka, covering **Sinhala, Tamil, and English**. It contains over **1.02 million articles** (~136 million words) published between **2013 and 2026** by three major Sri Lankan outlets — *Ada Derana*, *Hiru News*, and *ITN News* — with full article text and rich metadata.

Using CeyNews, we define and evaluate three downstream tasks: **(1) News Source Identification**, **(2) News Category Classification**, and **(3) Headline Generation**. Two fine-tuned models from these experiments are released on Hugging Face.

This repository contains the **CeyNews corpus, crawling, and preprocessing code** used to build CeyNews. The corpus is also hosted on Zenodo.

📦 **Corpus:** https://zenodo.org/records/20579021 (DOI: `10.5281/zenodo.20579021`)

🤗 **Models:**
- [`ltguoj/CeyNews-category-infoxlm-large`](https://huggingface.co/ltguoj/CeyNews-category-infoxlm-large) — news category classification
- [`ltguoj/CeyNews-headline-mt5-large`](https://huggingface.co/ltguoj/CeyNews-headline-mt5-large) — headline generation

---

## 📊 Corpus Statistics

| Source | Tamil (Articles) | Sinhala (Articles) | English (Articles) |
| ------ | ---------------: | -----------------: | -----------------: |
| Ada Derana | 158,289 | 193,190 | 78,745 |
| Hiru News | 154,013 | 272,275 | 150,693 |
| ITN News | 48,671 | 60,145 | — |
| **Total** | **360,973** | **525,610** | **229,438** |

Token counts: 38.7M (Tamil), 67.0M (Sinhala), 43.9M (English). Ada Derana Sinhala counts include NSINA articles published before 2017, and ITN Sinhala counts include NSINA articles published before 2023 ([NSINA](https://github.com/Sinhala-NLP/NSINA)). ITN News is not included for English as it has no English-language news section.

---

## 📂 Data Format

Each article is stored as a JSON record:

```json
{
  "Source": "hirunews",
  "Timestamp": "2024-03-12 09:41",
  "Headline": "...",
  "News Content": "...",
  "URL": "https://www.hirunews.lk/...",
  "Category": "Sports"
}
```

Categories are unavailable for Ada Derana articles, as this field is not exposed on individual article pages.

---
<!--
## 🧹 Collection & Preprocessing

A separate crawling strategy was implemented per outlet:

- **Ada Derana** — sequential identifier-based crawling, with a Selenium-initialised browser session passed to a persistent `requests.Session` to clear JavaScript-based validation.
- **Hiru News** — paginated JSON API endpoints for Sinhala and English; identifier-based page crawling for Tamil.
- **ITN News** — date-based archive traversal across all daily pagination pages.

Preprocessing applies Unicode NFC normalisation, rule-based removal of WordPress shortcodes, embedded-media markup, residual HTML, URLs, duplicated timestamp headers, source attributions, reporter bylines and navigation remnants, followed by quotation/dash standardisation and whitespace collapsing. Records with empty headlines or content are dropped, and exact duplicates are removed on the normalised headline–content pair.

---

## 🎯 Downstream Tasks

| Task | Input | Target | Metric | Size |
| ---- | ----- | ------ | ------ | ---- |
| News Source Identification | Article content | Outlet | Macro-F1 | 317,440 articles |
| News Category Classification | Article content | Local / International / Sports / Business | Macro-F1 | 81,309 articles |
| Headline Generation | Article content | Headline | BLEU, TER | 951,252 pairs |

Each task was constructed from CEYNEWS using fixed 80/10/10 train/validation/test splits (stratified by source or category where applicable) and evaluated under supervised fine-tuning, few-shot prompting (Llama 3.1-8B-Instruct), and cross-lingual transfer. The split files are not distributed; the sampling and splitting procedures are documented in the paper and can be reproduced from the released corpus.

**Best fine-tuned results**

| Task | Sinhala | Tamil | English |
| ---- | ------- | ----- | ------- |
| Source identification (Macro-F1) | 0.967 (XLM-R Large) | 0.812 (XLM-R Large) | 0.949 (mmBERT) |
| Category classification (Macro-F1) | 0.900 (InfoXLM Large) | 0.934 (InfoXLM Large) | 0.933 (mmBERT) |
| Headline generation (BLEU) | 0.167 (mBART-50) | 0.234 (mBART-50) | 0.205 (mT5-large) |

---
-->

## ⚖️ Ethical Considerations

The `robots.txt` files of all three sources were examined before crawling, and collection followed the available directives. To reduce the risk of author profiling, the released dataset is randomised and does not preserve the original chronological or author-based ordering.

---

## 📜 License

CeyNews is released under the **Creative Commons Attribution 4.0 International (CC BY 4.0)** license.

You are free to share and adapt the material, including for commercial purposes, provided you give appropriate credit, link to the license, and indicate if changes were made.

---

## 📖 Citation

If you use CEYNEWS, please cite:

> Ajintha, S., Sarveswaran, K., & Ranasinghe, T. (2026). *CeyNews: A Sri Lankan Trilingual News Corpus* [Dataset]. In Proceedings of the 13th Web as Corpus Workshop (Version v1.0). Zenodo. https://doi.org/10.5281/zenodo.20579021

```bibtex
@dataset{ceynews2026,
  title     = {{CeyNews: A Sri Lankan Trilingual News Corpus}},
  author    = {Ajintha, Sivakulasingam and Sarveswaran, Kengatharaiyer and Ranasinghe, Tharindu},
  booktitle = {Proceedings of the 13th Web as Corpus Workshop},
  year      = {2026},
  version   = {v1.0},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.20579021},
  url       = {https://doi.org/10.5281/zenodo.20579021}
}
```

---

## 🙏 Acknowledgement

Ajintha Sivakulasingam and Kengatharaiyer Sarveswaran acknowledge the support received from Google through the Research Scholar Program and from the University of Jaffna through its research grant.
