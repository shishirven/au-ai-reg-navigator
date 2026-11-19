"""DRAFT gold questions targeting statement-level authority (D-044): guidance that restates law,
not-yet-in-force law, carve-outs in binding standards, and the Privacy Act small business exemption.
Gold ids refer to the STAGING index (chroma_staging/); validated here. For the user's review."""

import json
from pathlib import Path

B, E, V = "binding", "expectation", "voluntary"
Q = [
    (
        "A01",
        "Do we have to explain our automated decisions in our privacy policy?",
        "bank",
        "split",
        ["privacy_act_app1_7_9:s002", "privacy_act_app1_7_9:s003", "oaic_app1_adm_2026:s005"],
        "Mandatory (binding from 10 Dec 2026): APP 1.7-1.8 require the APP privacy policy to state the kinds of personal "
        "information used and the kinds of decisions made by computer programs. Regulator expects: OAIC guidance on how much "
        "technical detail to include.",
        [B, E],
        "APP 1.7 must appear under Mandatory with 'from 10 Dec 2026', not as guidance.",
    ),
    (
        "A02",
        "When does the APP 1.7-1.9 automated decision-making transparency obligation commence?",
        "any_business",
        "factual",
        ["privacy_act_app1_7_9:s006", "privacy_act_app1_7_9:s001", "oaic_app1_adm_2026:s001"],
        "10 December 2026 (POLA Act 2024, s 2 table item 7). Binding law once in force.",
        [B, E],
        "The original failure case: must be labelled binding (from 10 Dec 2026), citing the Act.",
    ),
    (
        "A03",
        "Can staff put customer personal information into a public generative AI chatbot?",
        "any_business",
        "split",
        ["privacy_act_apps:s007.1", "oaic_ai_products_2025:s021.3"],
        "Mandatory: APP 6 limits use/disclosure to the primary purpose unless an exception applies. Regulator expects: OAIC "
        "recommends as best practice not entering personal (especially sensitive) information into public AI tools.",
        [B, E],
        "Best-practice advice must not be presented as law; APP 6 must be cited as the binding basis.",
    ),
    (
        "A04",
        "If our AI model infers new personal information about customers, is that a collection under the Privacy Act?",
        "insurer",
        "factual",
        ["privacy_act_apps:s004.1", "oaic_ai_products_2025:s003.3"],
        "Yes per OAIC guidance: generating/inferring personal information is a collection that must comply with APP 3 (APP 3 "
        "is binding; that inference counts as collection is the OAIC's interpretation).",
        [B, E],
        "Separates APP 3 (law) from the OAIC's interpretation of it.",
    ),
    (
        "A05",
        "We are a small business with $2 million annual turnover using an AI chatbot. Do the APPs apply to us?",
        "any_business",
        "factual",
        [
            "privacy_act_app_entity_sb:s003",
            "privacy_act_app_entity_sb:s005",
            "privacy_act_app_entity_sb:s002",
        ],
        "Generally no: a business with annual turnover of $3m or less is a small business operator (s 6D) and not an "
        "'organisation' bound by the APPs (s 6C), unless an exception in s 6D(4)/(9) applies or it opts in (s 6EA).",
        [B],
        "Must state the exemption AND its exceptions; must not say the APPs bind all businesses.",
    ),
    (
        "A06",
        "Our turnover is under $3 million but we sell customer data to marketing firms. Are we covered by the Privacy Act?",
        "any_business",
        "factual",
        ["privacy_act_app_entity_sb:s006"],
        "Yes: an entity that discloses personal information for a benefit, service or advantage is not a small business "
        "operator (s 6D(4)(c)), so the APPs apply.",
        [B],
        "Exception to the exemption must be applied.",
    ),
    (
        "A07",
        "Is notifying APRA about a new AI service provider for a critical operation a legal requirement or just guidance?",
        "bank",
        "split",
        ["apra_cps230_2026:p60", "apra_cpg230_2026:s004"],
        "Legal requirement: CPS 230 para 60(a) (within 20 business days). CPG 230's notification table restates it and "
        "explains the form - guidance pointing to the binding paragraph.",
        [B, E],
        "CPG restatement must resolve to CPS 230 para 60 and be labelled binding.",
    ),
    (
        "A08",
        "Is the APRA letter on AI legally binding?",
        "bank",
        "cross_doc",
        ["apra_ai_letter_2026:s002.2", "apra_cps230_2026:p11"],
        "No - the letter sets supervisory expectations. It states that APRA's technology-neutral prudential standards "
        "(e.g. CPS 230) apply to AI risk; those standards are binding.",
        [B, E],
        "Must not call the letter binding; must point to the binding standards it relies on.",
    ),
    (
        "A09",
        "Do the CPS 230 contract requirements in paragraph 53 apply to every material arrangement?",
        "bank",
        "factual",
        ["apra_cps230_2026:p53", "apra_cps230_2026:p57"],
        "Generally yes, but paragraph 57 provides that an entity need not comply with paras 53, 54, 55(d), 59(a) and 59(c) "
        "for certain arrangements (carve-out).",
        [B],
        "Binding carve-out ('need not comply') must be reported, not ignored.",
    ),
    (
        "A10",
        "Must our privacy policy name the specific AI models we use for decisions?",
        "bank",
        "split",
        ["privacy_act_app1_7_9:s003", "oaic_app1_adm_2026:s005"],
        "Not required by the text: APP 1.8 requires the kinds of personal information and kinds of decisions, not model "
        "names. OAIC guidance: avoid unnecessary technical detail.",
        [B, E],
        "Must not invent an obligation; distinguishes what the law requires from guidance on detail.",
    ),
]


def main() -> int:
    rows_path = sorted(Path("chroma_staging").glob("chunks_*.jsonl"))
    ids = (
        {json.loads(line)["chunk_id"] for line in rows_path[0].read_text().splitlines()}
        if rows_path
        else set()
    )
    missing = [g for q in Q for g in q[4] if ids and g not in ids]
    if missing:
        print("unknown gold ids (rebuild staging?):", missing)
        return 1
    out = Path("data/eval/questions_draft_authority.jsonl")
    out.write_text(
        "".join(
            json.dumps(
                {
                    "id": qid,
                    "status": "DRAFT",
                    "question": q,
                    "sector": sector,
                    "type": t,
                    "gold_chunk_ids": gold,
                    "reference_answer": ref,
                    "expected_tiers": tiers,
                    "authority_check": check,
                    "index": "staging",
                }
            )
            + "\n"
            for qid, q, sector, t, gold, ref, tiers, check in Q
        )
    )
    print(f"wrote {len(Q)} DRAFT authority questions to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
