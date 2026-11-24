# Model-use check: Motor insurance pricing model (GBM)

*Gradient-boosted model that sets motor premiums from policyholder, vehicle and claims-history data. Built in-house; trained on a cloud ML platform hosted by an external provider.*

| | |
|---|---|
| Sector / team / stage | insurer · actuarial · validate |
| Personal information · sensitive | yes · no |
| Decisions about individuals | yes |
| Third party · offshore | yes · unsure |
| Critical operation · generative AI | yes · no |

**16 mandatory · 31 regulator-expects · 6 recommended items** across 19 stages.

> General information from public regulatory documents, not legal advice and not a compliance verdict. Confirm each item against the cited source with your risk, compliance and privacy teams.

## Key points for this use case

- Prudential standards (CPS 230, CPS 234, CPS 220) bind APRA-regulated entities. This check assumes your organisation is an APRA-regulated insurer.
- If the vendor's service supports a critical operation, notify APRA as soon as possible and not more than 20 business days after entering into or materially changing the agreement (CPS 230 para 60(a)).
- Notify APRA before entering into a material offshoring arrangement, including where data or personnel for the service will be located offshore (CPS 230 para 60(b)). You answered 'unsure' on offshore: find out where the vendor hosts data and models.
- Automated decision-making transparency (APP 1.7-1.9) commences on 10 December 2026 (16 days from today): privacy policies must describe decisions a computer program makes, or substantially and directly informs, that could significantly affect individuals. Applies to decisions made after commencement, even if the computer program was arranged, or the personal information was used, acquired or created, before then. Banks and insurers are assumed to be APP entities. (Sources: OAIC APP 1.7-1.9 fact sheet; Privacy and Other Legislation Amendment Act 2024, s 2 commencement table, item 7.)
- 'Unsure' treated as 'yes' for: offshore.

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
- [ ] **🟢 Recommended** · [AI6 Foundations 5.Test and monitor](https://www.ai.gov.au/sites/default/files/2026-05/Guidance-for-AI-adoption-foundations_2.pdf) · also: Monitoring, drift and change control; Vendor information security  
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

- [ ] **🟠 Regulator expects** · [OAIC AI products guidance Top five takeaways](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-the-use-of-commercially-available-ai-products#:~:text=If%20personal%20information%20is%20being%20input) · ⚖️ explains binding law  
  4. If personal information is being input into an AI system, APP 6 requires entities to only use or disclose the information for the primary purpose for which it was collected, unless they have consent or can establish the secondary use would be reasonably expected by the individual, and is related (or directly related, for sensitive information) to the primary purpose. …
- [ ] **🟠 Regulator expects** · [OAIC AI products guidance Quick reference guide](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-the-use-of-commercially-available-ai-products#:~:text=The%20Privacy%20Act%20applies%20to%20all) · ⚖️ explains binding law  
  • The Privacy Act applies to all uses of AI involving personal information. • If personal information is being input into an AI system, APP 6 requires entities to only use or disclose the information for the primary purpose for which it was collected, unless they have consent or can establish the secondary use would be reasonably expected by the individual, and is related (or directly related, for sensitive …
- [ ] **🟢 Recommended** · [AI6 Foundations 4.Share essential information](https://www.ai.gov.au/sites/default/files/2026-05/Guidance-for-AI-adoption-foundations_2.pdf)  
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
- [ ] **🟢 Recommended** · [AI6 Foundations 2.Understand impacts and plan accordingly](https://www.ai.gov.au/sites/default/files/2026-05/Guidance-for-AI-adoption-foundations_2.pdf) · also: Fairness, bias and testing  
  Because AI systems can operate at speed and scale, their potential impacts are often magnified. Without careful planning, a single AI system can lead to widespread negative outcomes, such as unfair decisions or the provision of inaccurate information. For example, AI systems can learn from and amplify existing issues such as unwanted bias in data. …

## Privacy policy disclosure of automated decisions
*Decisions about individuals (pricing, underwriting, credit, claims, eligibility)*

**Evidence typically produced:** List of decisions the model makes or informs; privacy-policy wording; commencement readiness (from 10 Dec 2026)  
**Usually involves:** Privacy officer, Legal

*No binding paragraph in this library matched this stage. Privacy Act obligations apply, but the Act's text is not yet live in this library: see the ⚖️ notes and *Not covered* below.*

- [ ] **🟠 Regulator expects** · [OAIC APP 1.7-1.9 fact sheet Is the computer program substantially and directly related to making a decision?](https://www.oaic.gov.au/__data/assets/pdf_file/0021/269013/APP-1.7-1.9-Transparency-Obligation-Fact-Sheet.PDF) · ⏳ APP 1.7-1.9 commences 2026-12-10 · ⚖️ explains binding law  
  Substantially means where it is a key factor in facilitating the human’s decision making; and Directly means where the thing has a direct connection with making the decision. A computer program may be substantially and directly related to a decision if it: • advises of an appropriate outcome of a process • determines the outcome of a process • in any other way influences the outcome of a process. …
- [ ] **🟠 Regulator expects** · [OAIC APP 1.7-1.9 fact sheet When does the transparency obligation apply?](https://www.oaic.gov.au/__data/assets/pdf_file/0021/269013/APP-1.7-1.9-Transparency-Obligation-Fact-Sheet.PDF) · ⏳ APP 1.7-1.9 commences 2026-12-10 · ⚖️ explains binding law  
  An APP entity is in scope of the transparency obligation where: • it has arranged for a computer program to make, or do a thing that is substantially and directly related to making a decision; and • the decision could reasonably be expected to significantly affect the rights or interests of an individual; …
- [ ] **🟢 Recommended** · [AI6 Foundations 1. Decide who is accountable](https://www.ai.gov.au/sites/default/files/2026-05/Guidance-for-AI-adoption-foundations_2.pdf) · ❔ weaker match, check relevance · also: AI supply chain, change and exit  
  AI systems can make automated decisions that significantly impact people, communities and businesses. Overall, your organisation is ultimately accountable for how and where AI is used, AI complexity can create gaps where no one takes clear responsibility for outcomes. Accountability is the first step to using AI responsibly. Getting started 1.1 Assign a senior leader as the overall AI governance owner. …

## Fairness, bias and testing
*Decisions about individuals (pricing, underwriting, credit, claims, eligibility)*

**Evidence typically produced:** Fairness and bias testing results; impact assessment on affected customer groups  
**Usually involves:** Data / AI lead, Model risk

*No binding paragraph in this library matched this stage. Privacy Act obligations apply, but the Act's text is not yet live in this library: see the ⚖️ notes and *Not covered* below.*

- Also relevant (listed above): AI6 Foundations 2.Understand impacts and plan accordingly
- [ ] **🟠 Regulator expects** · [OAIC AI products guidance Privacy risks and harms](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-the-use-of-commercially-available-ai-products#:~:text=The%20use%20of%20both%20traditional%20and) · ⚖️ explains binding law  
  The use of both traditional and generative AI technologies carries a number of significant privacy risks. Specific risks are discussed throughout this guidance, but can include: This example highlights the risks of AI systems regurgitating personal information from their training data even when prompted for fictional examples, creating a range of potential privacy compliance and ethical risks. …
- [ ] **🟠 Regulator expects** · [OAIC AI products guidance Privacy risks and harms](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-the-use-of-commercially-available-ai-products#:~:text=The%20use%20of%20both%20traditional%20and) · ⚖️ explains binding law  
  The use of both traditional and generative AI technologies carries a number of significant privacy risks. Specific risks are discussed throughout this guidance, but can include: • Bias and discrimination: As AI systems learn from source data which may contain inherent bias, this bias may be replicated in their outputs through inferences made based on gender, race or age and have discriminatory effects. …

## Human oversight and contestability
*Decisions about individuals (pricing, underwriting, credit, claims, eligibility)*

**Evidence typically produced:** Human-review design; complaint and contest process; explanation approach  
**Usually involves:** Business owner, Compliance

- [ ] **🔴 Mandatory** · [CPS 230 para 12](https://www.legislation.gov.au/F2026L00475/asmade/2026-04-29/text/original/pdf#page=7) · ❔ weaker match, check relevance  
  12. An APRA-regulated entity must identify, assess and manage operational risks that may result from inadequate or failed internal processes or systems, the actions or inactions of people or external drivers and events. Operational risk is inherent in all products, activities, processes and systems.
- [ ] **🔴 Mandatory** · [CPS 230 para 24](https://www.legislation.gov.au/F2026L00475/asmade/2026-04-29/text/original/pdf#page=9) · ❔ weaker match, check relevance  
  24. An APRA-regulated entity must maintain appropriate and sound information and information technology (IT) capability to meet its current and projected business requirements and to support its critical operations and risk management. …
- [ ] **🟠 Regulator expects** · [OAIC AI products guidance What are the requirements of APP 10?](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-the-use-of-commercially-available-ai-products#:~:text=Organisations%20looking%20to%20use%20AI%20must) · ⚖️ explains binding law  
  Organisations looking to use AI must be aware of these accuracy risks and how they may impact on the organisation’s ability to comply with their privacy obligations. As discussed above, APP 10 requires an entity to take reasonable steps to ensure that: • Establishing processes to ensure there is appropriate human oversight of AI outputs, which treat the outputs as statistically informed guesses. …
- [ ] **🟠 Regulator expects** · [OAIC AI products guidance What ongoing assurance processes are needed?](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-the-use-of-commercially-available-ai-products#:~:text=Throughout%20the%20lifecycle%20of%20the%20AI) · ⚖️ explains binding law · ❔ weaker match, check relevance  
  Throughout the lifecycle of the AI product, your organisation should have in place processes for ensuring that the product continues to be reliable and appropriate for its intended uses. This will assist your organisation to comply with the requirement under APP 1 to take reasonable steps to implement practices, procedures and systems that will ensure it complies with the APPs and is able to deal with related …
- [ ] **🟢 Recommended** · [AI6 Foundations 6.Maintain human control](https://www.ai.gov.au/sites/default/files/2026-05/Guidance-for-AI-adoption-foundations_2.pdf)  
  Unlike traditional software that follows explicit instructions, AI systems learn patterns from data and make their own opaque decision logic. This means they need human oversight to make sure they operate safely. For example, while regular software does exactly what you program it to do, AI might interpret your instructions differently than you intended. …

## Due diligence before signing
*Third-party AI vendor, model API or platform*

**Evidence typically produced:** Vendor due-diligence record; materiality assessment; risk assessment of reliance on the provider  
**Usually involves:** Operational risk, Procurement

- [ ] **🔴 Mandatory** · [CPS 230 para 52](https://www.legislation.gov.au/F2026L00475/asmade/2026-04-29/text/original/pdf#page=14) · also: Contract terms; Notifying APRA and offshoring  
  52. Before entering into or materially modifying a material arrangement, an APRA-regulated entity must: (a) undertake appropriate due diligence, including an appropriate selection process and an assessment of the ability of the service provider to provide the service on an ongoing basis; …
- [ ] **🔴 Mandatory** · [CPS 230 para 55](https://www.legislation.gov.au/F2026L00475/asmade/2026-04-29/text/original/pdf#page=15)  
  55. For each material arrangement an APRA-regulated entity must: (a) identify and manage risks that could affect the ability of the service provider to provide the service on an ongoing basis; (b) identify and manage risks to the APRA-regulated entity that could result from the arrangement, such as step-in risk or contagion risk; (c) ensure it can execute its BCP if needed; …
- [ ] **🟠 Regulator expects** · [CPG 230 Requirement Activities to be undertaken by regulated entity](https://www.apra.gov.au/system/files/2026-05/Prudential%20Practice%20Guide%20CPG%20230%20-%20Operational%20Risk%20Management%20-%20clean.pdf#page=23) · ⚖️ explains binding law  
  Materiality assessment Perform materiality assessment of arrangements with NTSPs. Selection and initial due diligence Perform initial due diligence and appropriate selection process for material arrangements with non-traditional service providers. Where there is no optionality, there can be no selection process. Ongoing due diligence, monitoring, risk management, and
- [ ] **🟠 Regulator expects** · [CPG 230 para 55](https://www.apra.gov.au/system/files/2026-05/Prudential%20Practice%20Guide%20CPG%20230%20-%20Operational%20Risk%20Management%20-%20clean.pdf#page=22) · ⚖️ explains binding law  
  55. A prudent entity would assess the risks of engaging a service provider in another jurisdiction to determine if it is within appetite. This would include consideration of: a) the ability to continue operations and meet core obligations following a loss of service; b) maintenance of information security; c) the ability to own and manage controls on its behalf; …

## Contract terms
*Third-party AI vendor, model API or platform*

**Evidence typically produced:** Contract clause checklist (audit and APRA access, termination and exit, sub-contracting, incident notice, model change notice, data use)  
**Usually involves:** Legal, Procurement

- Also relevant (listed above): CPS 230 para 52
- [ ] **🔴 Mandatory** · [CPS 230 para 53](https://www.legislation.gov.au/F2026L00475/asmade/2026-04-29/text/original/pdf#page=14)  
  53. For all material arrangements, an APRA-regulated entity must maintain a formal legally binding agreement (formal agreement). The formal agreement must, at a minimum: (a) specify the services covered by the agreement and associated service levels; …
- [ ] **🟠 Regulator expects** · [CPG 230 para 52](https://www.apra.gov.au/system/files/2026-05/Prudential%20Practice%20Guide%20CPG%20230%20-%20Operational%20Risk%20Management%20-%20clean.pdf#page=22) · ⚖️ explains binding law  
  52. CPS 230 requires entities to maintain formal agreements for material arrangements with material service providers. Not all arrangements with a material service provider will be material to support delivery of the critical operation or expose the entity to material operational risk.
- [ ] **🟠 Regulator expects** · [CPG 230 para 58](https://www.apra.gov.au/system/files/2026-05/Prudential%20Practice%20Guide%20CPG%20230%20-%20Operational%20Risk%20Management%20-%20clean.pdf#page=23) · ⚖️ explains binding law  
  58. APRA recognises that regulated entities cannot meet certain contractual obligations in CPS 230 when engaging with NTSPs. Paragraph 57 of CPS 230 outlines exemptions available for such arrangements. Regulated entities may only utilise the relief for material arrangements with service providers where: …

## Notifying APRA and offshoring
*Third-party AI vendor, model API or platform*

**Evidence typically produced:** Notification decision and date; offshoring assessment (where data and models are hosted)  
**Usually involves:** Operational risk, Compliance

- Also relevant (listed above): CPS 230 para 52
- [ ] **🔴 Mandatory** · [CPS 230 para 60](https://www.legislation.gov.au/F2026L00475/asmade/2026-04-29/text/original/pdf#page=16)  
  60. An APRA-regulated entity must notify APRA: (a) as soon as possible and not more than 20 business days after entering into or materially changing an agreement for the provision of a service on which the entity relies to undertake a critical operation; …
- [ ] **🟠 Regulator expects** · [CPG 230 Notifications to APRA](https://www.apra.gov.au/system/files/2026-05/Prudential%20Practice%20Guide%20CPG%20230%20-%20Operational%20Risk%20Management%20-%20clean.pdf#page=9) · ⚖️ explains binding law · also: Critical operations and tolerance levels; Incident management and notification  
  Operational risk incidents As soon as possible and not later than 72 hours after becoming aware of an operational risk incident that it determines to be likely to have a material financial impact or a material impact on the ability of the entity to maintain its critical operations (paragraph 32 of CPS 230) Disruption As soon as possible and not later than 24 hours after a disruption to a critical operation outside …
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

- Also relevant (listed above): APRA AI letter Traditional change management and assurance is in place but is not sufficient for dynamic AI solutions; AI6 Foundations 1. Decide who is accountable
- [ ] **🟠 Regulator expects** · [APRA AI letter Supplier risk management is in place, but supplier concentration and opacity present challenges](https://www.apra.gov.au/news-and-publications/apra-letter-industry-artificial-intelligence-ai#:~:text=APRA%20observed%20some%20entities%20heavily%20dependent)  
  APRA observed some entities heavily dependent on a single provider for multiple AI use cases. Few entities had demonstrated robust contingency planning or tested exit and substitution strategies for critical AI providers. …

## Critical operations and tolerance levels
*Critical operations, incidents and resilience*

**Evidence typically produced:** Whether the model supports a critical operation; tolerance levels; fallback if the model fails  
**Usually involves:** Operational risk, Business owner

- Also relevant (listed above): CPG 230 Notifications to APRA
- [ ] **🔴 Mandatory** · [CPS 230 para 39](https://www.legislation.gov.au/F2026L00475/asmade/2026-04-29/text/original/pdf#page=12)  
  39. An APRA-regulated entity’s BCP must include: (a) the register of critical operations and associated tolerance levels; (b) triggers to identify a disruption and prompt activation of the plan, and arrangements to direct resources in the event of activation; (c) actions it would take to maintain its critical operations within tolerance levels through disruptions; …
- [ ] **🔴 Mandatory** · [CPS 230 para 41](https://www.legislation.gov.au/F2026L00475/asmade/2026-04-29/text/original/pdf#page=12) · also: Incident management and notification  
  41. An APRA-regulated entity must notify APRA as soon as possible, and not later than 24 hours after, if it has suffered a disruption to a critical operation outside tolerance. The notification must cover the nature of the disruption, the action taken, the likely impact on the entity’s business operations and the timeframe for returning to normal operations.
- [ ] **🟠 Regulator expects** · [CPG 230 para 16](https://www.apra.gov.au/system/files/2026-05/Prudential%20Practice%20Guide%20CPG%20230%20-%20Operational%20Risk%20Management%20-%20clean.pdf#page=11) · ⚖️ explains binding law  
  16. In identifying critical operations, in addition to APRA’s minimum list (see CPS 230 paragraph 35), a prudent entity would consider business operations that, if disrupted beyond tolerance levels: a) would have a direct material adverse impact on depositors, policyholders, beneficiaries or other customers; …

## Incident management and notification
*Critical operations, incidents and resilience*

**Evidence typically produced:** Incident playbook covering model failures; notification thresholds and timings  
**Usually involves:** Operational risk, CISO / Information security

- Also relevant (listed above): CPS 230 para 41; CPG 230 Notifications to APRA
- [ ] **🔴 Mandatory** · [CPS 230 para 32](https://www.legislation.gov.au/F2026L00475/asmade/2026-04-29/text/original/pdf#page=10)  
  32. An APRA-regulated entity must notify APRA as soon as possible, and not later than 72 hours, after becoming aware of an operational risk incident that it determines to be likely to have a material financial impact or a material impact on the ability of the entity to maintain its critical operations.
- [ ] **🟠 Regulator expects** · [CPG 230 para 29](https://www.apra.gov.au/system/files/2026-05/Prudential%20Practice%20Guide%20CPG%20230%20-%20Operational%20Risk%20Management%20-%20clean.pdf#page=13) · ⚖️ explains binding law  
  29. APRA expects that an entity would avoid extended delays or unwarranted extensions to targeted closure dates in addressing operational risk incidents. Incidents and near misses would be recorded in the entity’s operational risk information system and linked to controls to ensure that the risk profile accurately reflects any control weaknesses or gaps.

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
- **Insurance Contracts Act and insurance codes of practice.** Duties in claims handling and underwriting, including utmost good faith.
- **Anti-discrimination law.** Relevant where a model's decisions could treat people differently by a protected attribute.
- **ASIC guidance and Corporations Act licensee obligations.** Conduct obligations for AFS and credit licensees, including s912A general obligations.
- **Actuaries Institute professional standards and guidance.** Professional obligations for actuaries relying on models and AI outputs.

---
Generated 2026-11-24 · config `hybrid_stratified_rerank` · index `idx-2185d086e9c4` · no language model used: every item quotes its cited source.
