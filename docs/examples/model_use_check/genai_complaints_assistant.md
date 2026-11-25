# Model-use check: Complaints summarisation assistant (LLM API)

*Summarises customer complaint emails and suggests a category and next step for staff, using a third-party LLM API. Staff make the decision; the model does not.*

| | |
|---|---|
| Sector / team / stage | bank · data science · build |
| Personal information · sensitive | yes · unsure |
| Decisions about individuals | no |
| Third party · offshore | yes · yes |
| Critical operation · generative AI | no · yes |

**13 mandatory · 29 regulator-expects · 5 recommended items** across 18 stages.

> General information from public regulatory documents, not legal advice and not a compliance verdict. Confirm each item against the cited source with your risk, compliance and privacy teams.

## Key points for this use case

- Prudential standards (CPS 230, CPS 234, CPS 220) bind APRA-regulated entities. This check assumes your organisation is an APRA-regulated bank.
- Notify APRA before entering into a material offshoring arrangement, including where data or personnel for the service will be located offshore (CPS 230 para 60(b)).
- Sensitive information (e.g. health) generally needs consent to collect under the Privacy Act (APP 3). The Act's text is not yet live in this library: confirm with your privacy officer.
- 'Unsure' treated as 'yes' for: sensitive_information.

## Risk appetite, ownership and inventory
*Model development, validation and monitoring*

**Evidence typically produced:** Entry in the AI / model inventory; named owner; risk rating within appetite  
**Usually involves:** Data / AI lead, Risk partner

*No binding paragraph in this library matched this stage.*

- [ ] **🟠 Regulator expects** · [APRA AI letter AI adoption is moving fast, but governance maturity is lagging](https://www.apra.gov.au/news-and-publications/apra-letter-industry-artificial-intelligence-ai#:~:text=APRA%20observed%20AI%20adoption%20is%20accelerating) · also: Monitoring, drift and change control  
  APRA observed AI adoption is accelerating across all regulated industries. Entities are moving beyond experimentation from internal productivity use cases to customer facing applications. Many entities are already trialling or introducing AI capabilities in areas such as software engineering, claims triage, loan application processing, fraud and scam disruption, customer interaction and insight generation. …
- [ ] **🟠 Regulator expects** · [APRA AI letter Summary of common weaknesses and expectations for regulated entities - April 2026](https://www.apra.gov.au/news-and-publications/apra-letter-industry-artificial-intelligence-ai#:~:text=To%3A%20All%20APRA-regulated%20entities%20%E2%80%A2%20oversee)  
  To: All APRA-regulated entities • oversee an AI strategy which is consistent with the entity’s risk appetite and tolerance settings, supported by effective monitoring and reporting (including for third party dependencies), with clearly defined triggers aligned to resilience objectives to enable timely action when not operating as expected. …
- [ ] **🟢 Recommended** · [AI6 Foundations 3.Measure and manage risks](https://www.ai.gov.au/sites/default/files/2026-05/Guidance-for-AI-adoption-foundations_2.pdf) · also: Board oversight and AI literacy  
  AI risks fundamentally change depending on the type and complexity of your AI systems. Risks often emerge from how the AI system behaves in different situations and use-cases, rather than only from software updates. They can rapidly amplify smaller issues into significant problems. …

## Data quality and data risk
*Model development, validation and monitoring*

**Evidence typically produced:** Data quality checks; data lineage; known limitations  
**Usually involves:** Data / AI lead

- [ ] **🔴 Mandatory** · [CPS 220 para 25](https://www.legislation.gov.au/F2019L00669/asmade/2019-05-07/text/original/pdf#page=10)  
  25. The MIS must provide the Board of the APRA-regulated institution, board committees of the APRA-regulated institution and senior management of the institution with regular, accurate and timely information concerning the institution’s risk profile. …
- [ ] **🟠 Regulator expects** · [CPG 235 para 51](https://www.apra.gov.au/system/files/CPG-235-Managing-Data-Risk.pdf#page=14) · ⚖️ explains binding law  
  51. Data validation is the assessment of the data against business rules to determine its fitness for use prior to further processing. It constitutes a key set of controls for ensuring that data meets quality requirements.
- [ ] **🟠 Regulator expects** · [CPG 235 para 54](https://www.apra.gov.au/system/files/CPG-235-Managing-Data-Risk.pdf#page=14) · ⚖️ explains binding law  
  54. Common forms of data validation include verification of format, type, value range, currency, presence, consistency and completeness. Data validation can also be usefully conducted at a data-set level such as the use of: (a) control totalling: aggregation techniques including hash totalling , amount totalling and record counts; (b) reconciliation: comparing two sets of data and explaining variances; …

## Testing and validation before use
*Model development, validation and monitoring*

**Evidence typically produced:** Validation report; test results against acceptance criteria  
**Usually involves:** Model risk / independent validation

- [ ] **🔴 Mandatory** · [CPS 234 para 27](https://www.legislation.gov.au/F2018L01745/asmade/2018-12-12/text/original/pdf#page=9)  
  27. An APRA-regulated entity must test the effectiveness of its information security controls through a systematic testing program. The nature and frequency of the systematic testing must be commensurate with: (a) the rate at which the vulnerabilities and threats change; (b) the criticality and sensitivity of the information asset; (c) the consequences of an information security incident; …
- [ ] **🔴 Mandatory** · [CPS 230 para 29](https://www.legislation.gov.au/F2026L00475/asmade/2026-04-29/text/original/pdf#page=10) · ❔ weaker match, check relevance  
  29. An APRA-regulated entity must regularly monitor, review and test controls for design and operating effectiveness, the frequency of which must be commensurate with the materiality of the risks being controlled. The results of testing must be reported to senior management and any gaps or deficiencies in the control environment must be rectified in a timely manner.
- [ ] **🟠 Regulator expects** · [APRA AI letter Traditional change management and assurance is in place but is not sufficient for dynamic AI solutions](https://www.apra.gov.au/news-and-publications/apra-letter-industry-artificial-intelligence-ai#:~:text=AI%20risks%20can%20cut%20across%20multiple) · also: Monitoring, drift and change control; Vendor information security; AI supply chain, change and exit  
  AI risks can cut across multiple domains at regulated entities. This includes operational risk, cyber and information security, data governance, model risk, change control and release management, legal and regulatory compliance, privacy and conduct risk, procurement and third party dependency. …
- [ ] **🟠 Regulator expects** · [OAIC AI products guidance Is the product appropriate for its intended uses?](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-the-use-of-commercially-available-ai-products#:~:text=When%20selecting%20an%20AI%20product%2C%20your) · ⚖️ explains binding law · ❔ weaker match, check relevance  
  When selecting an AI product, your organisation should clearly identify the ways it intends to use AI and evaluate whether the particular product is appropriate. This includes considering whether the product has been tested and proven for such uses. You should consider whether the intended uses are likely to constitute high privacy risk activities. …
- [ ] **🟢 Recommended** · [AI6 Foundations 5.Test and monitor](https://www.ai.gov.au/sites/default/files/2026-05/Guidance-for-AI-adoption-foundations_2.pdf) · also: Monitoring, drift and change control; AI-specific security threats; Vendor information security  
  AI systems can change their behaviour over time or act in ways that are less predictable than conventional software. For example, an AI system that worked well last month might start giving different answers today if it is trained on additional data. To use AI safely, organisations should test and monitor their AI systems. Getting started 5.1 Ask for proof. …

## Monitoring, drift and change control
*Model development, validation and monitoring*

**Evidence typically produced:** Monitoring dashboard and thresholds; change-control record for retraining and version changes  
**Usually involves:** Data / AI lead, Model risk

*No binding paragraph in this library matched this stage.*

- Covered by items listed above: APRA AI letter Traditional change management and assurance is in place but is not sufficient for dynamic AI solutions; APRA AI letter AI adoption is moving fast, but governance maturity is lagging; AI6 Foundations 5.Test and monitor

## Collection, use and disclosure
*Personal information in data, prompts or outputs*

**Evidence typically produced:** Data inventory for the model (fields, sources, purpose); privacy impact assessment  
**Usually involves:** Privacy officer

*No binding paragraph in this library matched this stage. Privacy Act obligations apply, but the Act's text is not yet live in this library: see the ⚖️ notes and *Not covered* below.*

- [ ] **🟠 Regulator expects** · [OAIC AI products guidance Top five takeaways](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-the-use-of-commercially-available-ai-products#:~:text=If%20personal%20information%20is%20being%20input) · ⚖️ explains binding law · also: What goes into prompts and the model  
  4. If personal information is being input into an AI system, APP 6 requires entities to only use or disclose the information for the primary purpose for which it was collected, unless they have consent or can establish the secondary use would be reasonably expected by the individual, and is related (or directly related, for sensitive information) to the primary purpose. …
- [ ] **🟠 Regulator expects** · [OAIC AI products guidance Quick reference guide](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-the-use-of-commercially-available-ai-products#:~:text=The%20Privacy%20Act%20applies%20to%20all) · ⚖️ explains binding law  
  • The Privacy Act applies to all uses of AI involving personal information. • If personal information is being input into an AI system, APP 6 requires entities to only use or disclose the information for the primary purpose for which it was collected, unless they have consent or can establish the secondary use would be reasonably expected by the individual, and is related (or directly related, for sensitive …
- [ ] **🟢 Recommended** · [AI6 Foundations 4.Share essential information](https://www.ai.gov.au/sites/default/files/2026-05/Guidance-for-AI-adoption-foundations_2.pdf) · also: What goes into prompts and the model; Telling people they are dealing with AI  
  To use AI responsibly, organisations need to tell users and stakeholders when and how they’re interacting with AI. People should know when they’re interacting with AI and understand when AI decisions affect them. For example, when a customer is receiving services and information from a chatbot, they should know this is not a human specialist. Getting started 4.1 Create and maintain an AI register. …

## Overseas hosting and disclosure
*Personal information in data, prompts or outputs*

**Evidence typically produced:** Where data and models are hosted; overseas disclosure assessment  
**Usually involves:** Privacy officer, Legal

*No binding paragraph in this library matched this stage. Privacy Act obligations apply, but the Act's text is not yet live in this library: see the ⚖️ notes and *Not covered* below.*

- [ ] **🟠 Regulator expects** · [OAIC AI products guidance What are the potential security risks?](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-the-use-of-commercially-available-ai-products#:~:text=When%20assessing%20a%20new%20product%2C%20you) · ⚖️ explains binding law · also: Security, retention and deletion  
  When assessing a new product, you should consider your organisation’s obligations under APP 11 to take reasonable steps to protect the personal information you hold from misuse, interference and loss, as well as unauthorised access, modification or disclosure. …
- [ ] **🟠 Regulator expects** · [OAIC AI products guidance What are the requirements of APP 6?](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-the-use-of-commercially-available-ai-products#:~:text=When%20personal%20information%20is%20input%20into) · ⚖️ explains binding law  
  When personal information is input into an AI system, it may be considered either a use of personal information (if the data stays within your organisation’s control) or a disclosure of personal information (if the data is made accessible to others outside the organisation and has been released from your organisation’s effective control) under the Privacy Act. …

## Security, retention and deletion
*Personal information in data, prompts or outputs*

**Evidence typically produced:** Access controls; retention and deletion plan for training data, prompts and logs  
**Usually involves:** Privacy officer, CISO / Information security

*No binding paragraph in this library matched this stage. Privacy Act obligations apply, but the Act's text is not yet live in this library: see the ⚖️ notes and *Not covered* below.*

- Also relevant (listed above): OAIC AI products guidance What are the potential security risks?
- [ ] **🟠 Regulator expects** · [OAIC AI products guidance What are the requirements of APP 10?](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-the-use-of-commercially-available-ai-products#:~:text=Organisations%20looking%20to%20use%20AI%20must) · ⚖️ explains binding law  
  Organisations looking to use AI must be aware of these accuracy risks and how they may impact on the organisation’s ability to comply with their privacy obligations. As discussed above, APP 10 requires an entity to take reasonable steps to ensure that: • the personal information it collects is accurate, up-to-date and complete; …

## Accuracy of inputs and outputs
*Personal information in data, prompts or outputs*

**Evidence typically produced:** Output accuracy testing; process to correct inaccurate outputs about individuals  
**Usually involves:** Data / AI lead, Privacy officer

*No binding paragraph in this library matched this stage. Privacy Act obligations apply, but the Act's text is not yet live in this library: see the ⚖️ notes and *Not covered* below.*

- [ ] **🟠 Regulator expects** · [OAIC AI products guidance Quick reference guide](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-the-use-of-commercially-available-ai-products#:~:text=The%20Privacy%20Act%20applies%20to%20all) · ⚖️ explains binding law  
  • The Privacy Act applies to all uses of AI involving personal information. • Organisations must take particular care with sensitive information, which generally requires consent to be handled. Many photographs or recordings of individuals (including artificially generated ones) contain sensitive information and therefore may not be able to be generated by, or used as input data for, AI systems without the …
- [ ] **🟠 Regulator expects** · [OAIC AI products guidance What obligations do we have to ensure the accuracy of AI systems?](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-the-use-of-commercially-available-ai-products#:~:text=Organisations%20subject%20to%20the%20Privacy%20Act) · ⚖️ explains binding law  
  Organisations subject to the Privacy Act must comply with their accuracy obligations under APP 10 when using AI systems. APP 10 requires entities to take reasonable steps to ensure that: • the personal information they collect is accurate, up-to-date and complete; …
- [ ] **🟢 Recommended** · [AI6 Foundations 2.Understand impacts and plan accordingly](https://www.ai.gov.au/sites/default/files/2026-05/Guidance-for-AI-adoption-foundations_2.pdf) · also: Accuracy of generated outputs  
  Because AI systems can operate at speed and scale, their potential impacts are often magnified. Without careful planning, a single AI system can lead to widespread negative outcomes, such as unfair decisions or the provision of inaccurate information. For example, AI systems can learn from and amplify existing issues such as unwanted bias in data. …

## What goes into prompts and the model
*Generative AI and LLMs*

**Evidence typically produced:** Rules for what staff and systems may put in prompts; data-use terms of the model provider (training on your data, retention)  
**Usually involves:** Privacy officer, Data / AI lead

*No binding paragraph in this library matched this stage.*

- Also relevant (listed above): OAIC AI products guidance Top five takeaways; AI6 Foundations 4.Share essential information
- [ ] **🟠 Regulator expects** · [OAIC AI products guidance Privacy risks and harms](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-the-use-of-commercially-available-ai-products#:~:text=The%20use%20of%20both%20traditional%20and) · ⚖️ explains binding law  
  The use of both traditional and generative AI technologies carries a number of significant privacy risks. Specific risks are discussed throughout this guidance, but can include: • Bias and discrimination: As AI systems learn from source data which may contain inherent bias, this bias may be replicated in their outputs through inferences made based on gender, race or age and have discriminatory effects. …

## Accuracy of generated outputs
*Generative AI and LLMs*

**Evidence typically produced:** Output evaluation set and error rates; human-review step for outputs that reach customers or decisions  
**Usually involves:** Data / AI lead, Business owner

*No binding paragraph in this library matched this stage.*

- Also relevant (listed above): AI6 Foundations 2.Understand impacts and plan accordingly
- [ ] **🟠 Regulator expects** · [OAIC AI products guidance What are the specific accuracy risks of generative AI?](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-the-use-of-commercially-available-ai-products#:~:text=Accuracy%20risks%20are%20particularly%20relevant%20in) · ⚖️ explains binding law  
  Accuracy risks are particularly relevant in the context of generative AI. There are a number of factors which contribute to this: • Generative AI models such as large language models (LLMs) are trained on huge amounts of data sourced from across the internet, which is highly likely to include inaccuracies and built-in biases. …
- [ ] **🟠 Regulator expects** · [OAIC AI products guidance Privacy risks and harms](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-the-use-of-commercially-available-ai-products#:~:text=The%20use%20of%20both%20traditional%20and) · ⚖️ explains binding law  
  The use of both traditional and generative AI technologies carries a number of significant privacy risks. Specific risks are discussed throughout this guidance, but can include: • Misuse of generative AI systems: …

## Telling people they are dealing with AI
*Generative AI and LLMs*

**Evidence typically produced:** Disclosure wording in the interface; staff guidance on AI-assisted communications  
**Usually involves:** Business owner, Compliance

*No binding paragraph in this library matched this stage.*

- Also relevant (listed above): AI6 Foundations 4.Share essential information
- [ ] **🟠 Regulator expects** · [OAIC AI products guidance Can we collect personal information through an AI chatbot?](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-the-use-of-commercially-available-ai-products#:~:text=If%20your%20organisation%20collects%20personal%20information) · ⚖️ explains binding law  
  If your organisation collects personal information through public facing AI systems, such as through the use of AI chatbots, this collection must comply with APP 3 and APP 5 requirements. For example, if you have a customer facing AI chatbot on your website and you collect the information your customers send to the chatbot, you will need to ensure this collection complies with APP 3. …
- [ ] **🟠 Regulator expects** · [OAIC AI products guidance What are the requirements of APP 6?](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-the-use-of-commercially-available-ai-products#:~:text=When%20personal%20information%20is%20input%20into) · ⚖️ explains binding law  
  When personal information is input into an AI system, it may be considered either a use of personal information (if the data stays within your organisation’s control) or a disclosure of personal information (if the data is made accessible to others outside the organisation and has been released from your organisation’s effective control) under the Privacy Act. …

## AI-specific security threats
*Generative AI and LLMs*

**Evidence typically produced:** Threat model for the AI use (prompt injection, data leakage, agent permissions); security testing results  
**Usually involves:** CISO / Information security

- Also relevant (listed above): AI6 Foundations 5.Test and monitor
- [ ] **🔴 Mandatory** · [CPS 234 para 21](https://www.legislation.gov.au/F2018L01745/asmade/2018-12-12/text/original/pdf#page=8)  
  21. An APRA-regulated entity must have information security controls to protect its information assets, including those managed by related parties and third parties, that are implemented in a timely manner and that are commensurate with: (a) vulnerabilities and threats to the information assets; (b) the criticality and sensitivity of the information assets; …
- [ ] **🔴 Mandatory** · [CPS 234 Objectives and key requirements of this Prudential Standard](https://www.legislation.gov.au/F2018L01745/asmade/2018-12-12/text/original/pdf#page=3)  
  This Prudential Standard aims to ensure that an APRA-regulated entity takes measures to be resilient against information security incidents (including cyber-attacks) by maintaining an information security capability commensurate with information security vulnerabilities and threats. …
- [ ] **🟠 Regulator expects** · [APRA AI letter AI threats are increasing, but information security practices are struggling to keep pace](https://www.apra.gov.au/news-and-publications/apra-letter-industry-artificial-intelligence-ai#:~:text=APRA%20observes%20that%20AI%20adoption%20is)  
  APRA observes that AI adoption is materially changing the cyber threat landscape for regulated entities. The use of AI increases the pathways that cyber attackers can use and lead to more frequent cyber attacks. Common attack pathways observed include prompt injection, data leakage, insecure integrations, exploit injection and the manipulation or misuse of autonomous AI agents. …
- [ ] **🟠 Regulator expects** · [APRA AI letter AI threats are increasing, but information security practices are struggling to keep pace](https://www.apra.gov.au/news-and-publications/apra-letter-industry-artificial-intelligence-ai#:~:text=APRA%20observes%20that%20AI%20adoption%20is)  
  APRA observes that AI adoption is materially changing the cyber threat landscape for regulated entities. The use of AI increases the pathways that cyber attackers can use and lead to more frequent cyber attacks. Common attack pathways observed include prompt injection, data leakage, insecure integrations, exploit injection and the manipulation or misuse of autonomous AI agents. …

## Due diligence before signing
*Third-party AI vendor, model API or platform*

**Evidence typically produced:** Vendor due-diligence record; materiality assessment; risk assessment of reliance on the provider  
**Usually involves:** Operational risk, Procurement

- [ ] **🔴 Mandatory** · [CPS 230 para 52](https://www.legislation.gov.au/F2026L00475/asmade/2026-04-29/text/original/pdf#page=14) · also: Contract terms; Notifying APRA and offshoring  
  52. Before entering into or materially modifying a material arrangement, an APRA-regulated entity must: (a) undertake appropriate due diligence, including an appropriate selection process and an assessment of the ability of the service provider to provide the service on an ongoing basis; …
- [ ] **🔴 Mandatory** · [CPS 230 para 55](https://www.legislation.gov.au/F2026L00475/asmade/2026-04-29/text/original/pdf#page=15)  
  55. For each material arrangement an APRA-regulated entity must: (a) identify and manage risks that could affect the ability of the service provider to provide the service on an ongoing basis; (b) identify and manage risks to the APRA-regulated entity that could result from the arrangement, such as step-in risk or contagion risk; (c) ensure it can execute its BCP if needed; …
- [ ] **🟠 Regulator expects** · [CPG 230 Table 5: Expectations for material non-traditional service provider arrangements](https://www.apra.gov.au/system/files/2026-05/Prudential%20Practice%20Guide%20CPG%20230%20-%20Operational%20Risk%20Management%20-%20clean.pdf#page=23) · ⚖️ explains binding law · also: Contract terms  
  Requirement: Materiality assessment; Activities to be undertaken by regulated entity: Perform materiality assessment of arrangements with NTSPs. Requirement: Selection and initial due diligence; Activities to be undertaken by regulated entity: Perform initial due diligence and appropriate selection process for material arrangements with non-traditional service providers. …
- [ ] **🟠 Regulator expects** · [CPG 230 para 55](https://www.apra.gov.au/system/files/2026-05/Prudential%20Practice%20Guide%20CPG%20230%20-%20Operational%20Risk%20Management%20-%20clean.pdf#page=22) · ⚖️ explains binding law  
  55. A prudent entity would assess the risks of engaging a service provider in another jurisdiction to determine if it is within appetite. This would include consideration of: a) the ability to continue operations and meet core obligations following a loss of service; b) maintenance of information security; c) the ability to own and manage controls on its behalf; …

## Contract terms
*Third-party AI vendor, model API or platform*

**Evidence typically produced:** Contract clause checklist (audit and APRA access, termination and exit, sub-contracting, incident notice, model change notice, data use)  
**Usually involves:** Legal, Procurement

- Also relevant (listed above): CPS 230 para 52; CPG 230 Table 5: Expectations for material non-traditional service provider arrangements
- [ ] **🔴 Mandatory** · [CPS 230 para 53](https://www.legislation.gov.au/F2026L00475/asmade/2026-04-29/text/original/pdf#page=14)  
  53. For all material arrangements, an APRA-regulated entity must maintain a formal legally binding agreement (formal agreement). The formal agreement must, at a minimum: (a) specify the services covered by the agreement and associated service levels; …
- [ ] **🟠 Regulator expects** · [CPG 230 para 52](https://www.apra.gov.au/system/files/2026-05/Prudential%20Practice%20Guide%20CPG%20230%20-%20Operational%20Risk%20Management%20-%20clean.pdf#page=22) · ⚖️ explains binding law  
  52. CPS 230 requires entities to maintain formal agreements for material arrangements with material service providers. Not all arrangements with a material service provider will be material to support delivery of the critical operation or expose the entity to material operational risk.

## Notifying APRA and offshoring
*Third-party AI vendor, model API or platform*

**Evidence typically produced:** Notification decision and date; offshoring assessment (where data and models are hosted)  
**Usually involves:** Operational risk, Compliance

- Also relevant (listed above): CPS 230 para 52
- [ ] **🔴 Mandatory** · [CPS 230 para 60](https://www.legislation.gov.au/F2026L00475/asmade/2026-04-29/text/original/pdf#page=16)  
  60. An APRA-regulated entity must notify APRA: (a) as soon as possible and not more than 20 business days after entering into or materially changing an agreement for the provision of a service on which the entity relies to undertake a critical operation; …
- [ ] **🟠 Regulator expects** · [CPG 230 Table 1. Notifications to APRA](https://www.apra.gov.au/system/files/2026-05/Prudential%20Practice%20Guide%20CPG%20230%20-%20Operational%20Risk%20Management%20-%20clean.pdf#page=9) · ⚖️ explains binding law  
  Notifications to APRA 2 Operational risk incidents | As soon as possible and not later than 72 hours after becoming aware of an operational risk incident that it determines to be likely to have a material financial impact or a material impact on the ability of the entity to maintain its critical operations (paragraph 32 of CPS 230) Disruption | As soon as possible and not later than 24 hours after a disruption to a …
- [ ] **🟠 Regulator expects** · [CPG 230 para 59](https://www.apra.gov.au/system/files/2026-05/Prudential%20Practice%20Guide%20CPG%20230%20-%20Operational%20Risk%20Management%20-%20clean.pdf#page=23) · ⚖️ explains binding law  
  59. For a material arrangement with a service provider that does not meet either of the above conditions, regulated entities may apply to APRA for a specific exemption under paragraph 58.

## Vendor information security
*Third-party AI vendor, model API or platform*

**Evidence typically produced:** Security assessment of the vendor; control testing evidence or assurance reports  
**Usually involves:** CISO / Information security

- Also relevant (listed above): APRA AI letter Traditional change management and assurance is in place but is not sufficient for dynamic AI solutions; AI6 Foundations 5.Test and monitor
- [ ] **🔴 Mandatory** · [CPS 234 para 16](https://www.legislation.gov.au/F2018L01745/asmade/2018-12-12/text/original/pdf#page=7)  
  16. Where information assets are managed by a related party or third party, the APRA-regulated entity must assess the information security capability of that party, commensurate with the potential consequences of an information security incident affecting those assets.
- [ ] **🔴 Mandatory** · [CPS 234 para 22](https://www.legislation.gov.au/F2018L01745/asmade/2018-12-12/text/original/pdf#page=8)  
  22. Where an APRA-regulated entity’s information assets are managed by a related party or third party, the APRA-regulated entity must evaluate the design of that party’s information security controls that protects the information assets of the APRA-regulated entity.
- [ ] **🟠 Regulator expects** · [CPG 230 para 53](https://www.apra.gov.au/system/files/2026-05/Prudential%20Practice%20Guide%20CPG%20230%20-%20Operational%20Risk%20Management%20-%20clean.pdf#page=22) · ⚖️ explains binding law · ❔ weaker match, check relevance  
  53. An entity would normally conduct periodic reviews of material arrangements with a service provider. This could include assessment of operational issues (including information security incidents and service disruptions); control effectiveness; information security capabilities and business continuity capabilities; strategic changes; and comparisons to other offerings in the market.

## AI supply chain, change and exit
*Third-party AI vendor, model API or platform*

**Evidence typically produced:** Supply-chain map (vendor, foundation model, hosting); exit or substitution plan; model-change monitoring  
**Usually involves:** Data / AI lead, Operational risk

*No binding paragraph in this library matched this stage.*

- Also relevant (listed above): APRA AI letter Traditional change management and assurance is in place but is not sufficient for dynamic AI solutions
- [ ] **🟠 Regulator expects** · [APRA AI letter Supplier risk management is in place, but supplier concentration and opacity present challenges](https://www.apra.gov.au/news-and-publications/apra-letter-industry-artificial-intelligence-ai#:~:text=APRA%20observed%20some%20entities%20heavily%20dependent)  
  APRA observed some entities heavily dependent on a single provider for multiple AI use cases. Few entities had demonstrated robust contingency planning or tested exit and substitution strategies for critical AI providers. …
- [ ] **🟢 Recommended** · [AI6 Foundations 1. Decide who is accountable](https://www.ai.gov.au/sites/default/files/2026-05/Guidance-for-AI-adoption-foundations_2.pdf) · ❔ weaker match, check relevance  
  AI systems can make automated decisions that significantly impact people, communities and businesses. Overall, your organisation is ultimately accountable for how and where AI is used, AI complexity can create gaps where no one takes clear responsibility for outcomes. Accountability is the first step to using AI responsibly. Getting started 1.1 Assign a senior leader as the overall AI governance owner. …

## Board oversight and AI literacy
*Board and executive oversight*

**Evidence typically produced:** Board or committee paper; approval within the risk management framework  
**Usually involves:** Executive sponsor, Risk partner

- Also relevant (listed above): AI6 Foundations 3.Measure and manage risks
- [ ] **🔴 Mandatory** · [CPS 230 para 21](https://www.legislation.gov.au/F2026L00475/asmade/2026-04-29/text/original/pdf#page=8)  
  21. The Board must: (a) oversee operational risk management and the effectiveness of key internal controls in maintaining the entity’s operational risk profile within risk appetite. The Board must be provided with regular updates on the APRA-regulated entity’s operational risk profile and ensure senior management takes action as required to address any areas of concern; …
- [ ] **🔴 Mandatory** · [CPS 230 para 19](https://www.legislation.gov.au/F2026L00475/asmade/2026-04-29/text/original/pdf#page=8)  
  19. The Board of an APRA-regulated entity is ultimately accountable for oversight of an entity’s operational risk management. This includes business continuity and the management of service provider arrangements.
- [ ] **🟠 Regulator expects** · [APRA AI letter Summary of common weaknesses and expectations for regulated entities - April 2026](https://www.apra.gov.au/news-and-publications/apra-letter-industry-artificial-intelligence-ai#:~:text=To%3A%20All%20APRA-regulated%20entities%20Artificial%20Intelligence)  
  To: All APRA-regulated entities Artificial Intelligence (AI) is being rapidly adopted across APRA-regulated industries as entities seek to realise benefits to their businesses and customers. AI presents great opportunity for productivity and efficiency, and failing to embrace AI may put businesses at a strategic disadvantage. AI also has the potential to create new risks and escalate existing challenges. …
- [ ] **🟠 Regulator expects** · [CPG 230 para 9](https://www.apra.gov.au/system/files/2026-05/Prudential%20Practice%20Guide%20CPG%20230%20-%20Operational%20Risk%20Management%20-%20clean.pdf#page=8) · ⚖️ explains binding law · ❔ weaker match, check relevance  
  9. The Board would typically: a) oversee updates to an entity’s operational risk profile and ensure risks outside of its appetite are addressed promptly; b) oversee the effectiveness of key internal controls; c) be kept informed of areas of any material weaknesses and major remediation efforts; d) understand the material operational risks that arise from new ventures; …

## Not covered by this library: check separately

- **Privacy Act 1988 and the Australian Privacy Principles (the Act itself).** Privacy obligations are covered through OAIC guidance, which explains the APPs. The Act's text is staged but not yet live (it switches on with statement-level legal authority, D-044), so APP obligations appear under "Regulator expects" with an "explains binding law" note rather than under "Mandatory".
- **Financial Accountability Regime (FAR).** Named accountable executives and their accountability maps.
- **CPS 510 Governance.** Board and governance requirements beyond risk management.
- **CPG 234 Information Security (guidance).** APRA's practice guide to CPS 234, including third-party security assurance.
- **ASIC guidance and Corporations Act licensee obligations.** Conduct obligations for AFS and credit licensees, including s912A general obligations.

---
Generated 2026-11-25 · config `hybrid_stratified_capped` · index `idx-1174b9fc0ac3` · no language model used: every item quotes its cited source.
