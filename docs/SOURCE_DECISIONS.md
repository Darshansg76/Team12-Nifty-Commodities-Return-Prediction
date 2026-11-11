# Source decisions

The specific supplied brief, `Project Id 12- Nifty Commodities Benchmark return prediction/Nifty Commodities Benchmark return prediction.docx`, defines this project. The generic `Project List-new.xlsx` and the project list on the first page of the team PDF instead label Project ID 12 as investor risk tolerance. The user explicitly requested the Nifty Commodities project, so that specific brief controls the implementation. The discrepancy is retained for discussion with the instructor.

The team PDF identifies Team 12 as Dhanraj Rathod (PES1UG24AM359), Shridhar Umesh Golipalle (PES1UG25AM814), and Darshan Govekar (PES1UG24AM355). Names and SRNs are paired by their order in that row. The generic spreadsheet lists project topics and does not contain a team roster.

The user clarified that the old brief's prohibition on AI assistance does not apply this year. AI assistance was used for implementation, analysis and document preparation. There is no assertion that this was unaided work. Suggested rehearsal roles in the viva guide do not assert past individual contributions.

Course sources occasionally contain errors. We preserve signed held-out R2 instead of taking its absolute value. The original SHAP paper is arXiv 1705.07874. The arXiv 1602.04938 link in the provided interpretability lecture identifies LIME. The blending extension is our implemented validation procedure, rather than a claim that the supplied lectures explicitly teach this blend.

Nifty Commodities is an equity price index of commodity-related companies. The dataset is neither a total return index nor spot commodity prices. Earlier back-calculated history is retained in the raw download but excluded from modeling because the first 538 rows lack official open, high and low. All retained OHLC sessions are after the index launch.

No numeric experiment results are fabricated. Synthetic deterministic data appear only in isolated software tests. All report, presentation and notebook results derive from the official frozen historical snapshot.
