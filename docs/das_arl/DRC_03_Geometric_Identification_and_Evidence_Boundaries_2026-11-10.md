---
title: "深度表徵猜想 III：表徵場演化的幾何識別、因果驗證與解釋邊界"
english_title: "Deep Representation Conjecture III: Geometric Identification, Causal Tests, and Evidence Boundaries of Representational Field Dynamics"
series: "Deep Representation Conjecture (DRC)"
series_number: "03/03"
related_research: "DAS-ARL"
version: "0.1.0"
date: "2026-11-10"
author: "Neo.K / EveMissLab"
status: "MEASUREMENT_FRAMEWORK_NOT_EXECUTED"
source_format: "UTF-8 Markdown; canonical math delimiters only"
---

# 深度表徵猜想 III：表徵場演化的幾何識別、因果驗證與解釋邊界

## 摘要

本稿討論當 DRC-02 在同一問題的不同推理預算及第 X 次推理觀察到答案差異後，如何進一步判斷該差異與**模型內部表徵場的動態變化**是否有可驗證的關係。核心不是假設一段外顯思維鏈必然沿著某條高維測地線前進，而是建立可測量的狀態、尺度、距離、路徑、控制與介入程序，區分取樣隨機性、上下文變化、隱狀態變化及真正具有因果影響的表示轉換。

在抽象觀察者層次，整個 AI 可被視為一個對外有效單位；在內部工程層次，此單位由大量分散的狀態、計算路徑及參數構成。本文將「一也是全」理解為**同一系統可以被不同尺度粗粒化**，並以觀察者映射作為幾何比較的前提。若未證明所選度量有意義、未保存足夠的內部狀態或不能進行介入，應停留在現象描述，不能聲稱已識別場的幾何動力。

## 1. 與前兩篇的分工

- [DRC-01](DRC_01_Multiscale_Representation_Field_and_Observer_2026-11-10.md)：什麼是多尺度有效單位、候選表徵場與觀察者相對描述？
- [DRC-02](DRC_02_Temporal_Reasoning_Repeated_Answer_Protocol_2026-11-10.md)：同一問題在直接回答、30／40／50／60 秒與第 X 次推理下，外部回答如何變化？
- **本篇**：哪些內部遙測及因果證據能使「場態演化」成為可檢驗的模型，並防止把任意答案變化、思維鏈文字或相似度圖當成幾何證明？

本系列不是取代原本 DAS-ARL 六篇；DRC 提出研究對象，DAS 是可能的重建控制方式，DAS-L 是候選學習方法，DAS-LL 保持訓練與推論事件可追蹤。

## 2. 證據階梯：外部觀察、內部遙測、因果介入

| 等級 | 有何資料 | 能說什麼 | 不能說什麼 |
|---|---|---|---|
| E0 外部結果 | 同題的最終答案、實際時間、Token、驗證狀態 | 回答是否不同、是否更正確、成本多少 | 不能唯一還原內部表徵場 |
| E1 外顯過程 | 允許取得的中間文字／步驟、工具呼叫 | 外顯推理路徑是否不同 | CoT 是完整或忠實的內部原因 |
| E2 神經遙測 | 有權限取得的隱層活化、模組輸出、路由、注意力張量 | 某個模型、層、位置及觀測尺度上的活動變化 | 活化差異本身就是因果或語義真理 |
| E3 表徵對齊 | 多模型、不同層或不同時刻的探針與表示對齊 | 在固定比較規約下的相似性、分離性或轉換 | 表示距離天然等於理解深度 |
| E4 介入試驗 | 有控制的特徵抑制、活化替換、路由介入、隨機化 | 介入對指定結果的因果影響（條件限定） | 已定位普世唯一的「概念神經元」或物理場 |

白箱模型若不可取得某些資料，應標記 unavailable，而不是用 prompt 敘述補出不存在的隱狀態。封閉 API 可以先做 E0；有明確控制和可審核中間輸出的服務可有限做 E1。

## 3. 觀察者映射、模型版本與有效場態

令模型 $m$ 在計算步 $t$ 的全域有效狀態為 $S_{m,t}$，由觀察者 $o$ 的尺度映射取得：

$$
Z_{m,t}^{(o)}=\mathcal C_o(S_{m,t}).
$$

若研究者使用完整的某層隱狀態，可將 $Z$ 表示為帶 token 位置、層及特徵軸的張量；若研究者使用整個 AI 的黑箱回應，則 $Z$ 僅是外部有效輸出分布的代理。兩者不能聲稱具有同一個完整可觀測的表示空間。

跨模型版本也需要記錄 tokenizer、層結構、embedding 維度、路由設計與上下文限制；不同模型的「第 12 層」或「第 3 個專家」不能自動一一對應。

### 3.1 粗粒化識別性的簡單命題

**DRC-G1（不可逆觀察的識別下界）**：若映射 $\mathcal C_o$ 非單射，則至少存在 $S\ne S'$ 而有相同的 $Z^{(o)}$。因而只看到某觀察者尺度的相同輸出，不足以唯一還原微觀場態。

**證明**：非單射的定義直接給出不同輸入對應相同輸出。此處「場態」仍須由具體模型實作定義，不能將抽象證明視為已發現神經場。

## 4. 候選幾何：距離、對齊、路徑而非先指定測地線

研究者首先需定義某一表示空間與可重現的距離（或差異）函數：

$$
d_o(Z_a,Z_b).
$$

若兩次推理產生不同 $Z$，可比較距離，但不能只根據距離大小宣稱理解深度。不同的特徵基底、層正規化、尺度與上下文長度，均可能改變任意指定的距離。

可選研究工具包括：同層表徵的相似性矩陣、Centered Kernel Alignment（CKA）、Representational Similarity Analysis（RSA）、適當的對齊映射及事先驗證的線性探針。這些工具回答的是特定**表示可區分程度或幾何相似程度**，並不直接回答真理或模型主體性。

### 4.1 需要先定義度量才可談測地線

若表徵狀態真的形成可微流形 $\mathcal M_o$，而度量 $g_o$ 經研究合理定義，才可比較路徑長度：

$$
L_{g_o}(\gamma)=\int_0^1 \sqrt{g_o(\gamma(t))(\dot\gamma(t),\dot\gamma(t))}\,dt.
$$

實際 autoregressive 推論常是離散步次與不連續的路由事件，不保證能以此公式建模。若不適合連續流形，應採有限狀態圖、帶型別路徑或離散動態模型。**沒有幾何度量就沒有可檢驗的測地線主張**；即使度量已定，測地線也不是最正確的答案路徑。

### 4.2 表示基底與度量的敏感性

模型隱狀態可能因基底變換而改變座標數值，但下游整體輸出不變。若直接在原座標使用歐氏距離，任意非正交可逆變換不保證保留距離。因此應測試距離估計、鄰近關係及所宣稱的「表徵轉換」對允許的基底變換是否穩定，或明確聲明只研究特定座標規約。

這能減少把量測表示法的任意選擇誤當 AI 內在幾何的風險。

## 5. 幾何觀察與回答差異的兩層對照

對固定題目與模型版本，DRC-02 的試驗可形成完成態回答 $A_j$ 與可觀測場態快照 $Z_j^{(o)}$。至少檢查四種情形：

1. **外顯答案相同、內部狀態不同**：表示可能有不同路徑收斂到相同答覆，需檢查取樣、輸入與狀態對齊。
2. **外顯答案不同、所選尺度的表示相似**：可能是該尺度不足、輸出頭差異或取樣；不能反推全域場未改變。
3. **場態不同且回答更正確**：仍要排除更多計算、模型外部工具及偶然相關。
4. **場態不同而回答更錯誤**：直接反例，證明「更多表徵變化」本身不保證改善。

再將這些情形分別對照 30／40／50／60 秒及輪次、是否保留前史、是否真正續接隱狀態，檢查是否存在穩定可重現的變化方向。

## 6. 因果介入設計：改動場態是否真的改動輸出？

只看時間序列的表示相關性尚不足以識別機制。若有白箱開放權重模型，可考慮：

- **活化替換（activation patching）**：將特定層、位置或模組在條件 A 的活化替換至條件 B，測試指定回答義務是否改變。
- **特徵抑制或增強**：在受控範圍改動候選特徵方向，測量解答品質及來源忠實的變化。
- **路由介入**：固定認知路由或 MoE 計算路由，區分表徵操作策略與資源選擇的作用。
- **相反控制**：將非關鍵位置、隨機等量特徵或同預算其他路徑作為對照，排除一般擾動造成的退化。

必須保留 model revision、干預位置、樣本家族、比較分布、評估規約與資源成本。介入成功只證明**該設計及所選任務中的因果作用**，不意味場有唯一分割，也不代表跨架構普遍成立。

## 7. 語義尺度與哲學超譯的特殊驗證

對中文哲學文本，先讓模型在以下尺度抽取有來源的關係：字詞、句子、段落、全篇、整套理論、他者詮釋及創造性延伸。每一層必須附來源跨度或明確標為外部類比／新假說。

驗收不問「誰說得比較玄」，而問：

- 新增的限定詞與前提是否真在原文；
- 推理是否保留否定、模態與量詞範圍；
- 他者立場是否被錯認成作者本意；
- 跨域連結是否有適用條件與反例；
- 模型是否承認原文不足以支持某項結論。

單字、句段、全文與整體理論的多尺度切換如果提升來源忠實及有效結構發現，才可以說研究得到**操作層面的支持**；即使如此，尚不能直接等同於流形、曲率或測地線的存在。

## 8. 與既有 CoT 研究的區別

Wei 等人（2022）的 CoT 及 Wang 等人（2023）的 self-consistency 已研究中間推理與多路徑效果。Turpin 等人（2023）指出外顯 CoT 可能是不忠實的說明；Ghosal 等人（2025）和 2026 年相關 test-time compute 研究指出更多思考可能存在效益遞減及退化。因此單純觀察「思考久一點答案變了」不構成全新的神經幾何結論。

DRC 的待驗證新增問題是：**在清楚定義觀察尺度的情況下，答案結構與神經場態的可重現變化，是否能以可比較的多尺度幾何與因果模型更有效地描述或預測？**

若傳統輸出層統計、取樣變異與一般思維鏈模型已足以解釋資料，就不必強迫額外引入高維場的特殊幾何。

## 9. 候選測量指標（DRC-G01–10，未實測）

| ID | 候選指標 | 檢查目的 |
|---|---|---|
| DRC-G01 | 場態遙測可用率 | 有無可訪問且版本明確的內部狀態 |
| DRC-G02 | 尺度對齊完整度 | 不同粒度映射是否可重現 |
| DRC-G03 | 固定題目表徵距離 | 在指定度量下的配對差異 |
| DRC-G04 | 表徵距離對答案變化的解釋度 | 控制隨機性和輸出長度後仍有無貢獻 |
| DRC-G05 | 度量選擇敏感度 | 結論是否依任意距離設計劇變 |
| DRC-G06 | 基底與版本對齊穩健度 | 允許變換下的測量穩定性 |
| DRC-G07 | 動態路徑可重現性 | 控制條件下的路徑相似與差異 |
| DRC-G08 | 有效介入效應 | 特定活化干預對驗證結果的配對因果影響 |
| DRC-G09 | 來源忠實與超譯區別 | 幾何變化是否伴隨有用且有據的新關係 |
| DRC-G10 | 等成本預測增益 | 幾何模型是否超越簡單統計對照 |

這些是研究時可能需要的**新候選量**，不添加到 DAS-ARL 原 72 項未量測指標，也不給出任何虛構數值。

## 10. 判定與可被推翻的條件

**支持某些 DRC 機制的觀測**：同題不同計算條件下，內部狀態在明確度量與尺度選擇下出現可重現的結構變化；且部分變化經受控介入，能預測或影響指定答案義務、來源忠實度或正確性，並在新的題目家族仍可觀察。

**不支持或尚無法識別的觀測**：僅有文字改寫、幾何對距離極端敏感、不同取樣 seed 可重現所有效果、模型無法提供合法內部遙測、所選探針不能跨版本對齊、因果介入無效果或效果完全由更多運算解釋。

任何實驗結果只能在其模型、任務、來源、尺度、工具及驗證器的有限範圍內陳述。單個支持性結果不意味整個 AI 系統的高維表徵場已被完整測量。

## 11. 未來工程接口與資料限制

將 DRC-02 的外部實驗紀錄與白箱遙測另建對照關係，保留：

- source_hash、task_id、model_revision、tokenizer_revision、token_position_map、budget_condition、round_index、history_mode；
- observer_scale、projection_version、layer_or_module_ref、activation_receipt、metric_version、alignment_version；
- candidate_answer_hash、obligation_verification_receipt、intervention_type、control_condition、cost_receipt；
- evidence_class、privacy_class、observability 及缺失原因。

內部隱層張量不應不加限制上傳公開 GitHub；預設保存具有使用權及去識別化的測試摘要與雜湊，若需要完整數值，存於有存取控制的儲存位置。沒有取得可比的模型中間層資料，就將相應指標設為 unavailable，而不是以自我敘述補出測量。

**實作順序**應為：DRC-02 的黑箱現象對照先行，確定有效題型後再進行有限白箱可觀測性測試，最後才進入表示幾何與因果介入。這份文件**不是**已完成或已排程的工程執行。

## 12. 參考文獻及相關研究原稿

1. Wei, J., et al. (2022). *Chain-of-Thought Prompting Elicits Reasoning in Large Language Models*. NeurIPS 2022. https://papers.nips.cc/paper/2022/hash/9d5609613524ecf4f15af0f7b31abca4-Abstract-Conference.html
2. Wang, X., et al. (2023). *Self-Consistency Improves Chain of Thought Reasoning in Language Models*. ICLR 2023. https://research.google/pubs/self-consistency-improves-chain-of-thought-reasoning-in-language-models/
3. Turpin, M., et al. (2023). *Language Models Don't Always Say What They Think: Unfaithful Explanations in Chain-of-Thought Prompting*. NeurIPS 2023. https://proceedings.neurips.cc/paper_files/paper/2023/hash/ed3fea9033a80fea1376299fa7863f4a-Abstract.html
4. Ghosal, S. S., et al. (2025). *Does Thinking More Always Help? Mirage of Test-Time Scaling in Reasoning Models*. NeurIPS 2025. https://proceedings.nips.cc/paper_files/paper/2025/hash/fc067ac218430c409d6f65403328f740-Abstract-Conference.html
5. Dan, T., Ding, J., & Wu, G. (2025). *GeoDynamics: A Geometric State-Space Neural Network for Understanding Brain Dynamics on Riemannian Manifolds*. NeurIPS 2025. https://proceedings.neurips.cc/paper_files/paper/2025/hash/6a8449c080c3d27e5e16995e82beaade-Abstract-Conference.html — 為動態幾何建模的相關先例，研究對象是神經科學資料，不是 DRC 已驗證的 LLM 表徵幾何。
6. [DAS-ARL 原系列](README.md)：相關的自主注意力控制、學習與成本驗證研究，保持原文不變。

---

**版本與證據聲明**：本稿為 UTF-8 Markdown 正式研究原始碼，僅使用 $...$ 與 $$...$$ 數學分隔符。本文提出研究量測與因果驗證框架，沒有實際取得任何模型的內部活化、推理鏈、幾何距離或介入效果，也不聲稱已完成實驗。三篇 DRC 文件屬候選新系列，不覆寫 DAS-ARL 六篇及其既有指標。
