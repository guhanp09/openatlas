# Decision record

## 1. Use language choice rather than guesswork

Query language and preferred reading language can differ. The prototype gives the reader control and
does not silently translate. This makes scope explicit, although code-switching and transliterated input
remain unresolved. A wrong-language query can still return irrelevant lexical matches; lack of overlap
is not a complete out-of-domain detector.

## 2. Separate policy selection from final evidence

Select a word/character weight on 450 questions from the official training split after article/query
overlap removal. Use the official development queries only for final reporting. The chosen character
weight is 0.75. All policy trials are retained in reports/selection.json.

The corpus necessarily includes the relevant passages for held-out queries. IDF is fitted on searchable
passages, not on hidden query text or answer labels. This measures fixed-corpus search, not retrieval
over unseen documents. No tuning followed the held-out result.

## 3. Read the language gap before recommending rollout

Top-five retrieval is 92.5% for English, 92.0% for Bengali and 75.5% for Telugu. Improvement over each
baseline passes the predeclared comparison gate; it does not establish a satisfactory experience for
every group. The next priority is Telugu failures and native-reader comprehension, with broader rollout
held until those are understood. The Bengali sample is small, so its apparent parity should be treated
cautiously. The datasets also differ in questions and corpus difficulty; these are not matched-language
comparisons of identical questions.

## 4. Reduce preview transfer, retain an expansion path

Short previews reduce measured response bytes, but a snippet can omit the useful part of a passage.
Keep expansion available and test comprehension before making a bandwidth benefit claim. The current
preview uses a leading excerpt, not a query-focused summary. Combining-mark handling protects common
Indic boundaries but is not a complete grapheme-cluster implementation for every script/emoji.

## 5. Keep privacy proportional to the prototype

Bind the server to localhost. Do not persist queries, attach user identities or send analytics. Browser
requests use the local server; source links navigate only when opened. This is a research server, not a
hardened public hosting setup. A hosted pilot would need an explicit privacy and operational design.
