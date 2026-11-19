"""Writes data/eval/questions_draft.jsonl - DRAFT candidates for the user's review.

NEVER scored as the gold set. To promote: review/edit each item, delete `status`, and copy
approved items into data/eval/questions.jsonl. Gold ids are validated against the index.
"""

import json
import sys
from pathlib import Path

B, E, V = "binding", "expectation", "voluntary"
Q = [
    # ---------------- split: binding obligation hidden behind tech-neutral wording ----------------
    (
        "What do we need to do before engaging a third-party AI vendor?",
        "bank",
        "split",
        [
            "apra_cps230_2026:p52",
            "apra_cps230_2026:p55",
            "apra_ai_letter_2026:s006",
            "naic_ai6_foundations:s010",
        ],
        "Mandatory: an AI vendor is a service provider; before entering a material arrangement CPS 230 para 52 requires due diligence and an assessment of financial and non-financial risks. Regulator expects: APRA's AI letter expects mapping of the AI supply chain, transparency/auditability in contracts and concentration-risk management. Recommended: AI6 suggests asking suppliers for proof of testing.",
        [B, E, V],
    ),
    (
        "What must the contract with a provider of an AI model include if we rely on it for a critical operation?",
        "insurer",
        "split",
        ["apra_cps230_2026:p53", "apra_cps230_2026:p54", "apra_ai_letter_2026:s006"],
        "Mandatory: CPS 230 paras 53-54 require a formal legally binding agreement specifying services and service levels, rights and responsibilities (incl. data ownership, audit access), and provisions allowing APRA access. Regulator expects: contractual arrangements giving transparency, auditability and assurance over AI services (APRA AI letter).",
        [B, E],
    ),
    (
        "Do we have to tell APRA when we start using an AI provider for a critical operation?",
        "bank",
        "split",
        ["apra_cps230_2026:p60"],
        "Mandatory: CPS 230 para 60(a) - notify APRA as soon as possible and not more than 20 business days after entering into or materially changing an agreement for a service relied on for a critical operation; para 60(b) prior notice for material offshoring.",
        [B],
    ),
    (
        "Who in the organisation is accountable for risks from AI systems?",
        "bank",
        "split",
        [
            "apra_cps230_2026:p19",
            "apra_cps230_2026:p21",
            "apra_ai_letter_2026:s005",
            "naic_ai6_foundations:s006",
        ],
        "Mandatory: the Board is ultimately accountable for oversight of operational risk management (CPS 230 paras 19-21). Regulator expects: ownership and accountability across the AI lifecycle (APRA AI letter). Recommended: AI6 practice 1 - assign a senior AI governance owner and an accountable person per AI system.",
        [B, E, V],
    ),
    (
        "What are our obligations to secure an AI system that processes customer data?",
        "super",
        "split",
        [
            "apra_cps234:p15",
            "apra_cps234:p21",
            "apra_cps230_2026:p24",
            "apra_ai_letter_2026:s004.1",
            "naic_ai6_foundations:s010",
        ],
        "Mandatory: an AI system is an information asset - CPS 234 requires an information security capability and controls commensurate with threats (paras 15, 21); CPS 230 para 24 requires sound IT capability and compliance with CPS 234. Regulator expects: uplift of security practices for AI threats (APRA AI letter). Recommended: extend data governance and cyber practices to AI (AI6 5.4).",
        [B, E, V],
    ),
    (
        "If our AI vendor manages our information assets, what must we check about their security?",
        "bank",
        "split",
        ["apra_cps234:p16", "apra_cps234:p22", "apra_cps234:p28"],
        "Mandatory: CPS 234 requires assessing the third party's information security capability (para 16), evaluating the design of its controls (para 22) and, where relying on its control testing, assessing that testing (para 28).",
        [B],
    ),
    (
        "We had a serious outage of our AI-driven claims triage system. What are our notification obligations?",
        "insurer",
        "split",
        ["apra_cps230_2026:p41", "apra_cps230_2026:p32", "apra_cps230_2026:p35"],
        "Mandatory: claims processing is a minimum critical operation for insurers (CPS 230 para 35); a disruption outside tolerance must be notified to APRA within 24 hours (para 41); an operational risk incident likely to have material impact within 72 hours (para 32).",
        [B],
    ),
    (
        "We plan to use an AI model to approve loans. What controls and monitoring are required?",
        "bank",
        "split",
        [
            "apra_cps230_2026:p28",
            "apra_cps230_2026:p29",
            "apra_ai_letter_2026:s007",
            "naic_ai6_foundations:s011",
        ],
        "Mandatory: design, implement and embed internal controls and regularly monitor, review and test them (CPS 230 paras 28-29). Regulator expects: continuous validation/monitoring for drift and bias and integrated assurance (APRA AI letter). Recommended: meaningful human oversight and override points (AI6 practice 6).",
        [B, E, V],
    ),
    (
        "Does our risk appetite statement need to cover AI?",
        "bank",
        "split",
        ["apra_cps220:p27", "apra_cps220:p28", "apra_ai_letter_2026:s002.2"],
        "Mandatory: CPS 220 requires a Board-approved risk appetite statement addressing material risks with tolerances (paras 27-28) - it does not mention AI but applies where AI is a material risk. Regulator expects: an AI strategy consistent with risk appetite and tolerance settings (APRA AI letter).",
        [B, E],
    ),
    (
        "Do we need an inventory of our AI systems?",
        "super",
        "split",
        ["apra_ai_letter_2026:s005", "naic_ai6_foundations:s009", "apra_cps234:p20"],
        "Regulator expects: an inventory of AI tooling and AI use cases (APRA AI letter). Recommended: create and maintain an AI register (AI6 4.1). Mandatory (tech-neutral): CPS 234 para 20 requires classifying information assets, which includes AI systems.",
        [B, E, V],
    ),
    (
        "How should internal audit cover our use of AI?",
        "insurer",
        "split",
        ["apra_cps230_2026:p61", "apra_cps234:p32", "apra_ai_letter_2026:s007"],
        "Mandatory: internal audit must review proposed material outsourcing of critical operations (CPS 230 para 61) and review information security controls (CPS 234 para 32). Regulator expects: second line and internal audit to have technical capability and tooling to assess AI systems (APRA AI letter).",
        [B, E],
    ),
    (
        "What should we do about concentration risk from relying on a single AI provider?",
        "bank",
        "split",
        ["apra_ai_letter_2026:s006", "apra_cpg230_2026:p54", "apra_cps230_2026:p52"],
        "Regulator expects: active management of concentration risk incl. credible substitution/exit for critical AI providers (APRA AI letter); consider concentration risk when selecting providers (CPG 230 para 54). Mandatory: assess risks incl. concentration of the service provider before entering a material arrangement (CPS 230 para 52(b)).",
        [B, E],
    ),
    (
        "Must we keep a business continuity plan for critical operations that depend on AI?",
        "super",
        "split",
        ["apra_cps230_2026:p33", "apra_cps230_2026:p39", "apra_cps230_2026:p42"],
        "Mandatory: maintain a register of critical operations and a credible BCP (CPS 230 para 33) with prescribed contents (para 39) and a systematic testing program (para 42) - applies whether or not the operation uses AI.",
        [B],
    ),
    (
        "Our staff are using public generative AI chatbots. What rules apply?",
        "any_business",
        "split",
        ["oaic_ai_products_2025:s021.3", "apra_ai_letter_2026:s004.1", "naic_ai6_foundations:s006"],
        "Regulator expects: as best practice do not enter personal (especially sensitive) information into publicly available AI tools (OAIC); APRA is concerned about enterprise AI tools used outside approved control frameworks (APRA AI letter). Recommended: an AI policy advising staff on AI risks (AI6 1.2).",
        [E, V],
    ),
    # ---------------- factual: single document ----------------
    (
        "When does the APP 1.7-1.9 automated decision-making transparency obligation commence?",
        "any_business",
        "factual",
        ["oaic_app1_adm_2026:s001"],
        "From 10 December 2026 (not yet in force as of November 2026).",
        [E],
    ),
    (
        "When is an organisation in scope of the APP 1.7-1.9 transparency obligation?",
        "any_business",
        "factual",
        ["oaic_app1_adm_2026:s002", "oaic_app1_adm_2026:s004.1"],
        "Where it has arranged for a computer program to make, or do a thing substantially and directly related to making, a decision that could reasonably be expected to significantly affect an individual's rights or interests, using their personal information.",
        [E],
    ),
    (
        "How much technical detail must a privacy policy include about automated decisions?",
        "any_business",
        "factual",
        ["oaic_app1_adm_2026:s005"],
        "OAIC guidance: enough for individuals to understand how their information is handled, without overwhelming technical detail; structured so further information can be requested; tailored to the entity; decisions may be grouped by category.",
        [E],
    ),
    (
        "What are examples of decisions in scope of the ADM transparency obligation?",
        "any_business",
        "factual",
        ["oaic_app1_adm_2026:s006"],
        "OAIC Note 1 lists e.g. facial recognition for watchlist matching, recruitment software sorting candidates, personalised pricing for significant goods, among others.",
        [E],
    ),
    (
        "Within what time must APRA be notified of a material information security incident?",
        "bank",
        "factual",
        ["apra_cps234:p35"],
        "As soon as possible and no later than 72 hours after becoming aware (CPS 234 para 35).",
        [B],
    ),
    (
        "When must APRA be told about an information security control weakness we cannot fix in time?",
        "insurer",
        "factual",
        ["apra_cps234:p36"],
        "As soon as possible and no later than 10 business days after becoming aware (CPS 234 para 36).",
        [B],
    ),
    (
        "What business operations must an RSE licensee classify as critical operations at a minimum?",
        "super",
        "factual",
        ["apra_cps230_2026:p35"],
        "Investment management and fund administration, plus customer enquiries and supporting systems and infrastructure (CPS 230 para 35(c),(d)).",
        [B],
    ),
    (
        "What tolerance levels must be set for each critical operation?",
        "bank",
        "factual",
        ["apra_cps230_2026:p37"],
        "Maximum period of disruption, maximum extent of data loss, and minimum service levels under alternative arrangements (CPS 230 para 37).",
        [B],
    ),
    (
        "Which service providers must a bank classify as material service providers at a minimum?",
        "bank",
        "factual",
        ["apra_cps230_2026:p49"],
        "For an ADI: credit assessment, funding and liquidity management and mortgage brokerage; for all entities: risk management, core technology services and internal audit (CPS 230 para 49).",
        [B],
    ),
    (
        "When does CPS 230 (July 2026 version) commence?",
        "bank",
        "factual",
        ["apra_cps230_2026:p6"],
        "1 July 2026 (CPS 230 para 6).",
        [B],
    ),
    (
        "What governance arrangements does APRA expect for AI at a minimum?",
        "bank",
        "factual",
        ["apra_ai_letter_2026:s005"],
        "Frameworks and reporting lines; ownership and accountability across the AI lifecycle; an inventory of AI tooling and use cases; human involvement for high-risk decisions; staff training (APRA AI letter).",
        [E],
    ),
    (
        "What are the six essential practices in the Guidance for AI Adoption?",
        "any_business",
        "factual",
        [
            "naic_ai6_foundations:s006",
            "naic_ai6_foundations:s007",
            "naic_ai6_foundations:s008",
            "naic_ai6_foundations:s009",
            "naic_ai6_foundations:s010",
            "naic_ai6_foundations:s011",
        ],
        "Decide who is accountable; understand impacts and plan accordingly; measure and manage risks; share essential information; test and monitor; maintain human control.",
        [V],
    ),
    (
        "What dimensions of data quality does APRA suggest assessing?",
        "bank",
        "factual",
        ["apra_cpg235:p16"],
        "Accuracy, completeness, consistency, timeliness, availability and fitness for use, among others (CPG 235 para 16).",
        [E],
    ),
    # ---------------- cross_doc: several documents / tiers ----------------
    (
        "Compare what is mandatory versus only expected when managing AI suppliers.",
        "bank",
        "cross_doc",
        [
            "apra_cps230_2026:p52",
            "apra_cps230_2026:p53",
            "apra_ai_letter_2026:s006",
            "apra_cpg230_2026:p50",
        ],
        "Mandatory (CPS 230): due diligence and risk assessment before material arrangements; formal agreements with minimum terms. Expected (APRA AI letter, CPG 230): AI supply-chain mapping, auditability, concentration-risk management, proactive management of key risks.",
        [B, E],
    ),
    (
        "What privacy obligations apply if our AI generates or infers personal information about customers?",
        "any_business",
        "cross_doc",
        ["oaic_ai_products_2025:s003.3", "oaic_ai_products_2025:s022", "oaic_app1_adm_2026:s002"],
        "OAIC guidance: generating or inferring personal information is a collection that must comply with APP 3 (and APP 5 notice); if used in significant automated decisions the APP 1.7-1.9 transparency obligation applies from 10 Dec 2026.",
        [E],
    ),
    (
        "What due diligence should we do when buying a commercially available AI product?",
        "any_business",
        "cross_doc",
        ["oaic_ai_products_2025:s013", "oaic_ai_products_2025:s016.1", "naic_ai6_foundations:s010"],
        "Regulator expects (OAIC): ensure enough information to understand how the product works and its privacy risks; review terms on developer access to data (APP 6). Recommended (AI6): ask for proof of testing.",
        [E, V],
    ),
    (
        "How should model drift in AI systems be monitored?",
        "insurer",
        "cross_doc",
        ["apra_ai_letter_2026:s007", "naic_ai6_foundations:s010", "apra_cps230_2026:p29"],
        "Regulator expects continuous validation/monitoring to detect drift, bias and failures (APRA AI letter); recommended: monitor after deployment matched to risk (AI6 5.3); mandatory tech-neutral basis: regularly monitor and test controls (CPS 230 para 29).",
        [B, E, V],
    ),
    (
        "What human oversight is expected for high-risk AI decisions?",
        "bank",
        "cross_doc",
        ["apra_ai_letter_2026:s005", "naic_ai6_foundations:s011", "oaic_app1_adm_2026:s004.1"],
        "Regulator expects human involvement for high-risk decisions (APRA AI letter); recommended: meaningful oversight and override points (AI6 practice 6); OAIC notes ML outputs are generally in scope of ADM transparency unless subject to extensive human oversight.",
        [E, V],
    ),
    (
        "What does APRA expect for assurance over AI systems, and is any of it mandatory?",
        "super",
        "cross_doc",
        ["apra_ai_letter_2026:s007", "apra_cps234:p27", "apra_cps234:p32"],
        "Expected: recognised control frameworks, integrated assurance, capable second and third lines (APRA AI letter). Mandatory tech-neutral: systematic testing of information security controls (CPS 234 para 27) and internal audit review of those controls (para 32).",
        [B, E],
    ),
    (
        "Is following the Guidance for AI Adoption mandatory for an insurer?",
        "insurer",
        "cross_doc",
        ["naic_ai6_foundations:s001.1", "apra_ai_letter_2026:s002.2"],
        "No - AI6 is voluntary guidance (an update to the Voluntary AI Safety Standard). Binding obligations for insurers come from prudential standards (e.g. CPS 230, CPS 234), which are technology-neutral; APRA's AI letter sets expectations, not new requirements.",
        [E, V],
    ),
    (
        "What should a service provider management policy cover when we use AI providers?",
        "super",
        "cross_doc",
        ["apra_cps230_2026:p46", "apra_cps230_2026:p47", "apra_cpg230_2026:p45"],
        "Mandatory: a comprehensive service provider management policy covering identification, engagement, monitoring and exit of material providers (CPS 230 paras 46-47). Guidance on additional content in CPG 230 para 45.",
        [B, E],
    ),
    # ---------------- unanswerable: out of corpus -> must abstain ----------------
    (
        "What penalties apply under the EU AI Act for prohibited AI practices?",
        "bank",
        "unanswerable",
        [],
        "Out of scope - the corpus covers Australian documents only. Abstain.",
        [],
    ),
    (
        "What capital charge does APRA apply to AI model risk under APS 115?",
        "bank",
        "unanswerable",
        [],
        "Not covered by the corpus (no capital standards). Abstain.",
        [],
    ),
    (
        "What are ASIC's requirements for AI used in financial advice under RG 255?",
        "any_business",
        "unanswerable",
        [],
        "ASIC documents are not in the corpus. Abstain.",
        [],
    ),
    (
        "What will the proposed mandatory guardrails for high-risk AI in Australia require?",
        "any_business",
        "unanswerable",
        [],
        "Proposals for mandatory guardrails are not in the corpus. Abstain (do not answer from superseded voluntary standard).",
        [],
    ),
    (
        "How much does a Claude API call cost per million tokens?",
        "any_business",
        "unanswerable",
        [],
        "Unrelated to regulation; abstain.",
        [],
    ),
]


def main() -> int:
    chunk_files = sorted(Path("chroma").glob("chunks_*.jsonl"))
    ids = (
        {json.loads(line)["chunk_id"] for line in chunk_files[0].read_text().splitlines()}
        if chunk_files
        else set()
    )
    out, missing = [], []
    for i, (q, sector, qtype, gold, ref, tiers) in enumerate(Q, start=1):
        missing += [g for g in gold if ids and g not in ids]
        out.append(
            {
                "id": f"D{i:02d}",
                "status": "DRAFT",
                "question": q,
                "sector": sector,
                "type": qtype,
                "gold_chunk_ids": gold,
                "reference_answer": ref,
                "expected_tiers": tiers,
            }
        )
    if missing:
        print("unknown gold ids:", missing)
        return 1
    path = Path("data/eval/questions_draft.jsonl")
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out))
    from collections import Counter

    print(f"wrote {len(out)} DRAFT questions to {path}: {dict(Counter(r['type'] for r in out))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
