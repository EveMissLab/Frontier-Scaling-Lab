---
title: "DAS-ARL 工程實作 RFC-001：在既有 Transformer、MoE 與 Agent 架構上導入深度注意力光譜"
english_title: "DAS-ARL Engineering RFC-001: Implementing Representation Reconstruction on Contemporary Transformer, MoE and Agent Systems"
series: "Deep Attention Spectrum and Autonomous Representation Learning (DAS-ARL)"
document_type: "engineering_rfc"
revision: "0.1.0"
status: "PROPOSED_NOT_IMPLEMENTED"
date: "2026-11-09"
author: "Neo.K / EveMissLab"
target_repository: "EveMissLab/Frontier-Scaling-Lab"
evidence_status: "engineering_design_only"
---

# DAS-ARL 工程實作 RFC-001：在既有 Transformer、MoE 與 Agent 架構上導入深度注意力光譜

> **工程狀態**：本文件是可供實作、評估與討論的 RFC，不是已部署系統、已跑通的 DAS 訓練或模型性能報告。所有預設門檻是待預註冊的建議值，不能取代實驗結果。本文不改寫前六篇正式研究原稿，也不修改 72 項候選研究指標的未量測狀態。

## 0. 目的、決策與最小結論

DAS（Deep Attention Spectrum）的工程需求並非「讓模型多想幾次」而已，而是讓模型在**相同原始資訊保持可追溯**的條件下，能夠選擇重新提取條件、同域深化、重組表徵、跨域搜尋或停止，並由獨立驗證程序決定某項重構是否足以採納。DAS-L 是後續使此種控制策略可訓練的擴充；DAS-LL 則是不可混合的學習、推論與調用事件帳本。

本 RFC 的工程決策建議：

1. **先建外層 DAS 控制與驗證**，不先訓練新模型、不先改 Self-Attention kernel，也不以 MoE 專家當作全部認知控制器。
2. 初版刻意使用**原始來源回訪 + 不同表示操作 + 外部驗證 + 最佳候選封存**；必須與等成本自我反思對照組比較。
3. 有了可重現增益後，才訓練小型 DAS 認知控制器，再導入隱狀態循環與部分梯度更新；全模型或 MoE 聯合訓練留在後續階段。
4. 所有研究指標在取得真實、有來源、可重播的量測前，維持 **null／not_measured**。
5. 用研究型分階段閘門決策，而不是以預期成果保證技術有效。

**禁止的捷徑**：把答案改寫次數當理解深度；把新穎度當正確度；把驗證器輸出直接視為可微梯度；把檢索事件算成權重學習；把跨學科比喻視為有效證明；把 Agent 探索授予新的工具權限。

## 1. 既有系統接入模式與承諾邊界

| 模式 | 現有基礎 | DAS 能提供什麼 | 不能宣稱什麼 | 優先度 |
|---|---|---|---|---|
| A — 外部編排 | 封閉 API 模型、開源推論服務、一般 Transformer Agent | 使用原文回訪、操作路由、候選版本、獨立驗證、停止與帳本 | 看得到內部 Attention、修改模型梯度或證明內在表徵改變 | 第一階段 |
| B — 可訓練外層 | 開放權重 Transformer；凍結骨幹 + 控制器 / adapter / 小型狀態模組 | 訓練選擇操作、重構條件、動態深度、校準成本 | 已經形成新的通用學習法則或已定位特定知識神經元 | 第二階段 |
| C — 模型原生 DAS | 可控制訓練程式的 Transformer、循環深度模型或自研模型 | 在隱空間重建表徵，對循環步次作 BPTT / 截斷 BPTT / 其他適合的梯度訓練 | 任意深度有益、固定點等於理解完成、可無成本跨越領域 | 第三階段 |

MoE 可以在 A／B／C 的計算階段使用，但**認知操作選擇**（要重新理解什麼）與**計算專家選擇**（由誰計算）維持分離，並在實驗中提供消融。

本研究亦可接入本地數學題庫、程式驗證器與沙盒 Agent；**資料與工具介面應為可選依賴**。在 Frontier-Scaling-Lab 內，本 RFC 是研究與指標設計文件，不應自行把其他專案的程式碼、私有模型或資料集複製進來。

## 2. 可部署的分層架構

~~~mermaid
flowchart TD
    A["Immutable Source / Task Contract"] --> B["Initial Representation and Baseline"]
    B --> C["Uncertainty and Obligation Monitor"]
    C --> D["DAS Cognitive Controller"]
    D --> E["INTRA / RE_EXTRACT / RE_FACTOR / CROSS / TOOL_VERIFY / STOP"]
    E --> F["Execution Backend: LLM / Adapter / Latent Recurrence"]
    F --> G["Candidate Representation Archive"]
    G --> H["Independent Verifier and Hard Policy Gate"]
    H --> I["Accepted Best Candidate or Unresolved"]
    H --> C
    D --> J["Compute Router / Optional MoE"]
    J --> F
    B --> K["Typed DAS-LL Event Ledger"]
    D --> K
    F --> K
    H --> K
~~~

**分工契約**：

- Immutable Source Store：持有來源雜湊、原始題意及版本；不允許候選答案覆蓋原始題意。
- Obligation Extractor：從原文生成明確約束與待驗證義務；每一項需保留來源片段 ID 與歧義狀態。
- DAS Controller：只能發出認知操作與探索預算決策，不得自行替候選發放真值證書。
- Representation Executor：執行不同操作，產生結構化候選與對照來源；在模式 A 通常只是可見文字／結構化資料，非內部神經表徵。
- Compute Router：依實際可用資源選擇模型或 MoE 專家；其 expert_id 不等於學科 domain_id。
- Verifier：對可驗證義務給出 pass／fail／unknown／not_applicable，保留驗證器版本與檢查依據。
- Best Archive：只對**同一固定任務契約與可比較評分**保留已驗證候選；原候選與失敗候選維持可追溯。
- Budget Controller：統一管理 Token、重建步次、工具調用、GPU 時間、總延遲與人工負擔。
- DAS-LL Ledger：分開記錄讀取、檢索、推論、表徵修改、驗證、反向傳播與參數更新，避免來源混算。

## 3. 核心形式狀態、運算與資料同一性

對某一任務，令原始輸入為 $X$，任務契約為 $K$，固定的模型版本為 $\theta$。第 $t$ 次認知探索包含工作表徵 $H_t$、候選封存 $\mathcal A_t$、驗證義務 $\mathcal O_t$、驗證紀錄 $\mathcal V_t$、預算 $\mathcal B_t$ 及操作歷程 $\mathcal E_t$：

$$
S_t = (X,K,H_t,\mathcal A_t,\mathcal O_t,\mathcal V_t,\mathcal B_t,\mathcal E_t).
$$

認知動作由與 MoE 不同的控制政策選擇：

$$
a_t \sim \pi_{\psi}(a \mid \operatorname{summary}(S_t)),
\qquad
a_t \in \{\mathrm{RE\_EXTRACT},\mathrm{INTRA},\mathrm{RE\_FACTOR},\mathrm{CROSS},\mathrm{TOOL\_VERIFY},\mathrm{STOP},\mathrm{ESCALATE}\}.
$$

候選表示更新遵循：

$$
H_{t+1} = F_{\theta,\phi}(X,H_t,a_t,M_t),
$$

其中 $M_t$ 是有來源的輔助工作記憶，而不是把新敘述偷偷當成原始問題。模型權重 $\theta$ 在純推論階段不變；參數更新只能發生在明確的訓練階段。模式 A 的 $H_t$ 僅指**外顯結構化工作狀態**；模式 C 可把 $H_t$ 實作為隱狀態張量。

關鍵不可混淆的 identity：

- source_id：原始 UTF-8 位元組 SHA-256、來源位置、資料權利與可見性；相同內容 hash 不意味相同授權或來源事件。
- task_id：任務契約版本、固定評分義務與資料切分。
- representation_id：表示候選內容與其版本；不等於模型的「知識 ID」。
- execution_run_id：模型、參數／adapter、提示規約、路由版本與執行環境。
- validation_id：哪個驗證器在何時以何規約驗證了何個候選。
- learning_run_id：只有明確發生訓練事件時才建立，不能把對話迭代等同 optimizer step。

**工程可證性限制**：在完整輸入、隨機種子、外部狀態與模型決定性設定不變的情況下，重複相同函數未必產生不同表徵；想真正探索替代路徑，需要明確操作、狀態改變、路由差異或受控隨機性，不能把「再看一次」視為魔法。

## 4. DAS 動態控制器的有限狀態機

必須實作的狀態：INIT → BASELINE → MONITOR → SELECT_ACTION → EXECUTE → VERIFY → ARCHIVE → MONITOR，或由 MONITOR 轉 STOP／ESCALATE／BUDGET_EXHAUSTED。

### 4.1 觸發器（保留校準資訊）

- **條件遺漏**：對原文可追溯的待檢驗義務未覆蓋。
- **可驗證失敗**：算術、定理檢查、測試、型別或沙盒行為失敗。
- **矛盾與衝突**：候選間不一致，或與原始條件衝突。
- **低證據狀態**：無可用驗證而結論過度確定。
- **跨次修正失敗**：同一錯誤多次重現，要求更換表示操作，不是增加相同重試次數。
- **使用者重述負擔**：經明確可觀測的回饋或預註冊標記評估，不能臆測使用者主觀困惑。

注意：不確定度偵測器本身會出錯。任何以模型自信度產生的觸發都只能是**候選訊號**，不得替代外部正確性驗證。

### 4.2 操作優先級與跨域橋接

1. 確認 source 的解析完整性及誤抄問題。
2. 優先嘗試 INTRA 或 RE_EXTRACT 修補已定位的條件缺口。
3. 若缺口是表示載體不適合，選 RE_FACTOR（集合、圖、表格、狀態機、方程組等）。
4. 若同域方法存在明確阻礙且跨域有可表述的映射，才提議 CROSS；保留映射的定義域、保留性及反例。
5. 無可靠驗證時，可回報 unresolved 或請求真正缺失的資料；絕不以跨域類比冒充證據。

### 4.3 硬性停止與採納閘門

任何候選在採納前必須檢查：來源忠實度、任務合約滿足、外部權限、安全與獨立驗證狀態；未知不可自動轉為通過。STOP 的原因必須標示 VERIFIED／MARGINAL_VALUE_LOW／BUDGET_EXHAUSTED／UNRESOLVED／POLICY_BLOCKED／NEED_SOURCE_DATA，不得一律寫作「完全理解」。

有限預算下的回圈需設最大步次、每次工具上限、總時間上限、成本上限和重複表示 fingerprint 上限；任何一項用盡即停止或交付未決狀態。禁止無限迴圈或背景無限重試。

## 5. 明確的工程 API 契約（v0.1）

以下是**資料形狀與語義約定**，不是表示目前已存在可用服務。實作時配套使用版本化 JSON Schema。

### 5.1 輸入 TaskContract

~~~json
{
  "schema_version": "das-arl-engineering/0.1",
  "task_id": "synthetic-task-001",
  "source_sha256": "sha256:REPLACE_WITH_VALID_64_HEX",
  "source_visibility": "private",
  "model_ref": "model-and-revision-pinned",
  "dataset_split": "synthetic",
  "task_domain": "mathematics",
  "obligation_ids": ["obligation-01"],
  "permitted_actions": ["RE_EXTRACT", "INTRA", "RE_FACTOR", "TOOL_VERIFY", "STOP"],
  "max_iterations": 4,
  "budget": {
    "max_input_tokens": 16000,
    "max_output_tokens": 8000,
    "max_tool_calls": 6,
    "max_wall_ms": 120000
  },
  "external_side_effects": "disabled",
  "evidence_class": "synthetic"
}
~~~

上述預算值只屬**合成示例設定**，非建議的普世最佳值；每個研究集需要獨立預註冊預算矩陣。source_sha256 範例刻意是占位符，validator 應在實際任務拒絕它。任務原文不得預設寫入公開帳本。

### 5.2 認知動作請求與回傳

~~~json
{
  "task_id": "synthetic-task-001",
  "iteration": 2,
  "action": "RE_FACTOR",
  "source_span_ids": ["span-02", "span-05"],
  "parent_representation_ids": ["repr-01"],
  "target_obligation_ids": ["obligation-01"],
  "intended_change": "change to explicit finite-state constraints",
  "compute_route_hint": "default_model",
  "max_new_tokens": 1024
}
~~~

執行器至少回傳 candidate_id、representation_id、parent IDs、source span 參照、output_artifact_ref、model/tokenizer/revision、token 成本與錯誤／逾時狀態。**字面形式不同**不自動算新表徵；新關係需由可檢查義務和實驗效應支持。

### 5.3 驗證與封存狀態

~~~json
{
  "candidate_id": "candidate-02",
  "verification": {
    "status": "unknown",
    "verifier_id": "math-checker-v0",
    "obligation_results": [{"id": "obligation-01", "status": "unknown"}],
    "receipt_ref": null,
    "reason": "no executable proof/certificate available"
  },
  "archival_decision": "retain_as_unresolved",
  "evidence_class": "synthetic"
}
~~~

Verifier 的 unknown、timeout、unsupported、policy_blocked 必須分開。若要比較最佳候選，固定同一 task_id、同一驗證規約版本與同一 score 方向；跨模型或跨時間改規約應建立新的評估版本。

## 6. Runtime 模式 A：無需模型內部梯度的 MVP

MVP 建議以 Python 服務實作具型別的 orchestration，適配至少兩個可交換推論後端（其中一個可為本地模型、另一個可為 mock）。第一階段只需**外層可重讀的表示**，避免宣稱已修改內部 Attention。

最小模組介面：

~~~python
class SourceStore:
    def get_immutable(self, source_id): ...

class ObligationExtractor:
    def extract(self, task_contract, source): ...

class CognitivePolicy:
    def select(self, observable_state, legal_actions, remaining_budget): ...

class RepresentationExecutor:
    def transform(self, task_contract, source, parent_repr, action): ...

class IndependentVerifier:
    def check(self, task_contract, candidate, evidence_refs): ...

class CandidateArchive:
    def append(self, candidate, verdict): ...
    def best_verified(self, fixed_contract): ...

class EventLedger:
    def append_event(self, typed_event): ...

class BudgetMeter:
    def reserve(self, proposed_cost): ...
    def settle(self, receipt): ...
~~~

規約要求 deterministic mock executor 和 mock verifier 可在 CPU 重播。生成模型不能自己寫入「獨立驗證 pass」；只能提議候選和必要證據。沒有來源保留的重述不能通過義務覆蓋。

### 6.1 參考偽程式（非可執行原型）

~~~python
def run_das(task, source, model, policy, verifier, archive, ledger, meter):
    assert sha256_utf8(source) == task.source_sha256
    baseline = model.initial_representation(task, source)
    archive.append(baseline, status="unverified")
    ledger.append_event(kind="INFER_FORWARD", candidate_id=baseline.id)

    state = monitor(task, source, archive, meter)
    for step in range(task.max_iterations):
        action = policy.select(state, legal_actions(task, meter), meter.remaining())
        if action in ("STOP", "ESCALATE"):
            break
        if not meter.reserve_for(action):
            break
        candidate = model.reconstruct(task, source, archive, action)
        verdict = verifier.check(task, candidate)
        archive.append(candidate, verdict)
        meter.settle_from_receipts(candidate, verdict)
        ledger.append_event(kind="RECONSTRUCT", candidate_id=candidate.id, action=action)
        ledger.append_event(kind="VERIFY", candidate_id=candidate.id, verdict=verdict.status)
        state = monitor(task, source, archive, meter)
        if state.has_verified_completion:
            break

    return archive.best_verified(task) or unresolved_result(task, state)
~~~

當 baseline 自身已完整驗證時，控制器應可立即 STOP；若欠缺合適驗證器，回傳 unresolved 而不是自我頒發 pass。以上偽程式特意省略例外、資源競態與權限實作；工程完成的標準見第 12 節。

## 7. Runtime 模式 B／C：與現有 Transformer 的內部整合

### 7.1 嵌入位置選項

**方案 B1 — sidecar/controller + frozen Transformer**：原 Transformer 不修改；以控制 token、提示片段、結構化 memory 或可訓練 adapter 實施表示調節。推論時選擇不同操作，訓練時先更新 $\psi$（controller）與小型 adapter $\phi$；凍結 backbone $\theta$。風險最低，也最能識別外層控制器的實際貢獻。

**方案 C1 — hidden-state recurrent refinement**：選定骨幹中高層輸出為 $H_0$，與原來源編碼 $E_\theta(X)$ 共同進入可重用的 refinement block。每一循環步次執行：

$$
H_{t+1} = H_t + g_{\phi}\bigl(H_t,E_{\theta}(X),e(a_t)\bigr),
$$

其中 $g_\phi$ 可由 cross-attention、adapter MLP 或共享 Transformer block 實作。殘差不是單調改善保證；每步仍須由獨立驗證器判斷任務結果。可選擇性共享或不共享 $g_\phi$ 的權重，並做相同參數量的消融。

**方案 C2 — output-level re-encoding**：每步以原文與先前結構表示重新 prefill 推論，適合現有 decoder-only API；它的成本通常包含再次 prefill 和生成 token。改寫提示導致的能力變化不等於證明隱狀態有新因果機制。

### 7.2 Tensor 與運算規範

- input_ids: 整數張量 [B, T]；source_mask [B, T]。
- encoder_hidden: [B, T, d]；工作表示 [B, M, d]，M 可小於 T，但來源跨度不得遺失。
- action_logits: [B, A]；domain_hints: [B, D]；expert_logits 僅在實際使用 MoE 時為 [B, E]。
- action_mask 必須在 sampling 之前遮罩未授權動作，且工具層另有獨立權限檢查。
- value 或 quality head 如存在，只是代理估計，不能替代驗證器；校準與外部有效性分開測量。
- sequence-padding、batch 混合步次、梯度截斷、detach、KV-cache 生命週期需要在測試中覆蓋。
- **KV cache 一致性**：任何更改來源前綴、token 序列或支配隱狀態的操作，必須重建不相容快取；不得把另一條候選路徑的過期 KV 當作同一路徑有效快取。
- **MoE 路由**：只有 compute router 可以直接映射到 expert_id；DAS 的 domain_tag 不允許硬編碼為某個 expert_id。稀疏容量、負載不平衡及掉 token 等必須另外記錄。
- 在不同硬體、混合精度及 kernel 上，數值可重現性應聲明為 toleranced 或 deterministic；不要以相同 seed 保證 bitwise 相同。

### 7.3 現有梯度與顯存策略

固定步數的可微循環可以直接 unroll，建立標準計算圖；長序列則可考慮截斷 BPTT 或 activation checkpoint。截斷會使較早步次的梯度路徑被切斷，因此需要做截斷長度消融。PyTorch checkpoint 應明確設定 use_reentrant=False，並避免 forward/backward 重計算時引入不一致的外部副作用。**checkpoint 是用額外重算換訓練記憶體，並非 DAS 理解重建操作；不能計成一次深度注意力學習事件。**

隱式微分只在其平衡假設與收斂條件適用時研究；DAS 的跨域跳轉與離散重排未必有適當固定點，不得直接沿用 DEQ 並宣稱任意步數皆可微或皆收斂。

## 8. DAS-L 訓練策略：從控制器到循環表徵

建議先用經過外部驗證的軌跡訓練**選擇操作和停止的控制器**，再訓練部分可微的 refinement 模組。不要預設每個任務都要修改 backbone 權重。

### 8.1 訓練事件與損失的三個層次

**層次 1 — 監督路由**：在具有可比較驗證結果及預算成本的候選軌跡中，對 action choice 訓練分類或 ranking；資料需要包含 STOP、NO_GAIN、UNRESOLVED 的反例。標籤生成器與評估資料必須隔離。

**層次 2 — 可微隱表示**：在模式 C 對可微 $F_{\theta,\phi}$ 執行固定步數或截斷 BPTT，任務損失與來源約束使用具體可微代理，但**不可將代理得分直接說成真實驗證正確性**。

**層次 3 — 離散行為學習**：對不可微的 action／工具選擇，研究策略梯度或其他離散政策學習。其可觀測獎勵需包含可靠外部驗證、總成本與違規懲罰；權限硬閘門始終先於獎勵。

候選研究目標（各分量需預先正規化，且不得把硬性權限轉成可交易的軟分數）：

$$
J = \mathbb{E}[Q_{\mathrm{verified}}] - \lambda_c \mathbb{E}[C_{\mathrm{total}}] - \lambda_u \mathbb{E}[U_{\mathrm{unverified}}],
$$

其中 $Q_{\mathrm{verified}}$ 的定義依任務域與固定驗證器決定，沒有可驗證結果時需保留 unknown，不能把 unknown 自動填 0 或 1。離散政策可研究下式，前提是符合抽樣政策和無偏估計所需假設：

$$
\nabla_{\psi}J_{\mathrm{policy}} =
\mathbb{E}\left[(R-b)\sum_{t=0}^{T-1}\nabla_{\psi}\log \pi_{\psi}(a_t\mid S_t)\right].
$$

$R$ 是軌跡級評價訊號，$b$ 是降低方差的基準；這**不是把驗證器反向微分**。實作須處理 credit assignment、罕見動作、資料分布偏移、重複探索與高方差。

### 8.2 資料集與負例設計

每一題保留：

- 原始輸入與來源指標，不只保存模型推導文字。
- 初步錯誤的型別（漏條件、誤讀語義、無效類比、算術錯誤、工具失敗或資料不足）。
- 至少一個**有效重構**及一個**無效但表面新穎的重構**，若可構造；不能製造無根據的標準答案。
- 等成本額外運算的對照軌跡；只有勝過它才能考慮宣稱 DAS 的獨立機制效益。
- 未改善與應立即停止的情況，防止訓練出無限重述傾向。
- 資料分割按照題型家族、來源版本、時間及污染風險進行，不能以相同模板改變常數就當成獨立測試。

來源不能因為出現在 OCME 或外部研究資料中就自動具有訓練授權。數學 checker 的 pass、程式測試的 pass、人工論證的同意分別代表不同證據範圍。

### 8.3 訓練順序

T0：凍結模型，只蒐集基線與受控 DAS 軌跡。  
T1：訓練小型 controller，評估與固定規則路由、隨機路由及等成本反思之差異。  
T2：凍結 backbone，訓練 adapter / recurrence module，有限步數反向傳播。  
T3：研究 controller 與 adapter 聯訓；量測不穩定、遺忘與總成本。  
T4：只有在前幾階段提供可靠增益時，才評估 backbone 部分解凍、MoE 或完全新架構。

沒有量測到增益時，可以拒絕推進 T4；這是可接受的工程結論。

## 9. DAS-LL 學習、調用與參數聯動帳本

最小事件型別要能嚴格區分：

| 事件 | 語義 | 不可推論 |
|---|---|---|
| SOURCE_EXPOSE | 曾輸入／呈現資訊 | 模型已學會 |
| RETRIEVE | 從外部檢索到資訊 | 發生梯度更新 |
| INFER_FORWARD | 前向計算 | 修改了權重 |
| RECONSTRUCT | 修改工作表徵或可見結構 | 產生有效新理解 |
| VERIFY | 驗證器產生有範圍的判定 | 全域正確 |
| TRAIN_FORWARD | 訓練前向 | 完成反向傳播 |
| TRAIN_BACKWARD | 反向傳播 | optimizer 已更新 |
| OPTIMIZER_STEP | 優化器完成 step | 參數一定有非零變化 |
| PARAMETER_DELTA | 實際量測參數差異 | 差異能歸因至單一來源 |
| REPLAY_EVAL | 同一模型版本的評估重播 | 對應線上真實表現 |

每項事件至少包含：event_id、task_id、run_id、timestamp_utc、kind、model_version、source_ref、parent_event_ids、evidence_class、observability、receipts、privacy_class。訓練額外記錄 batch_id、microbatch_index、accumulation_group、optimizer_step_id、adapter_version、gradient_norm（可觀測時）、parameter_delta_norm（真正量測時）。沒有內部遙測就填 null + missing_reason，不能填零。

公開 GitHub 上只保存經清理的合成或已授權觀察資料；原始提示、私人模型、梯度張量、個人資訊及內部密鑰不進公開 commit。雜湊鏈保證某些更改可被發現，**不證明事件內容必然真實**。

## 10. 驗證與評估：在相同預算下證明有用

### 10.1 對照組（必要）

- B0：單輪 baseline，不重構。
- B1：同模型固定額外 token 的自我反思／重試。
- B2：固定步數重新閱讀原文，但不改變操作策略。
- B3：DAS controller + 完整重建操作 + 外部驗證。
- B4：B3 移除重新回訪原始來源。
- B5：B3 移除表徵操作路由，只做隨機或固定路由。
- B6：有 MoE 時，移除專家控制與認知控制的分離，或把 compute router 凍結，觀察效應。

比較至少同時提供：相同 wall time 或成本預算、相同 model/backbone、相同資料、相同可用工具、相同驗證器及至少三組不同 seed（正式樣本數由預先統計計畫決定）；若無法完全等同，報告完整 Pareto 曲線，不能挑有利單一預算點。

### 10.2 四個任務族與成功定義

**數學**：分開統計計算正確、最終答案正確、證明義務覆蓋、原始條件忠實度及缺資訊棄答。優先使用可重算題型與獨立確定性 checker；不得讓模型直接修改 gold answer。

**程式**：預留隱藏測試、回歸測試、型別與沙盒執行結果；統計修復成功、反覆回歸、無關修改、失敗重試與測試成本。不能以模型口頭說「已修好」認定成功。

**Agent**：在可回滾模擬環境內檢驗任務完成率、狀態漂移、權限違規、外部工具冪等性及異常升級。任何真實外部副作用必須保持人類授權或原系統授權限制。

**哲學／開放性研究**：評估前提忠實、概念區分、反例處理、內部一致性、可選替代解釋及證據邊界；不可用單一「正確答案」或生成文字篇幅當客觀理解深度。

### 10.3 必須報告的失敗

- re-reading 無效，或固定額外推理一樣有效。
- 過度思考使正確答案退化；候選最佳封存與最終生成答覆分開。
- verifier 錯誤與模型錯誤具有共同模式，造成自我認證。
- CROSS 產生華麗但不保真的類比。
- 資料污染、訓練與評估資料重合。
- 隱狀態漂移、長循環梯度不穩、KV-cache 污染。
- MoE 路由負載失衡、專家識別不可靠。
- 檢索與前向調用被錯計為訓練。
- 整體成本更高，尤其在簡單任務上沒有改善。

### 10.4 成本總帳與預註冊

$$
C_{\mathrm{task}}=C_{\mathrm{model}}+C_{\mathrm{tool}}+C_{\mathrm{verifier}}+C_{\mathrm{retry}}+C_{\mathrm{human}}+C_{\mathrm{infrastructure}},
$$

其中每一項均需有明確單位、計價時間與避免雙重計數的規約；時間、Token、GPU 能耗、峰值記憶體應保留獨立向量，不能任意硬加為一個數字。統計採用配對任務、報告 95% 信賴區間與失敗率；顯著性設計、停止規則及多重比較修正需先預註冊。

核心判準不是單一 benchmark 勝負，而是**相近總資源下的可靠度改善、重述負擔是否降低、以及新增成本是否值得**。

## 11. 可觀測指標與既有 Frontier-Scaling-Lab 目錄接口

既有候選指標檔是：

- [data/das_arl_indicator_catalog_v0.1.json](../../data/das_arl_indicator_catalog_v0.1.json)
- 12 項 DAS-R（認知／專家路由）
- 16 項 DAS-L（學習控制）
- 20 項 DAS-LL（事件與神經聯動）
- 24 項 DAS-V（驗證與成本）

**本 RFC 不新增實測值，也不改動上述 72 項的定義。** 工程實作需建立 adapter 轉換成目錄所需的數值記錄，並保留 numerator、denominator、units、sample_n、model revision、split、verifier revision、as_of、confidence interval 和 evidence receipts。

工程里程碑指標（例如 CI 測試通過）必須與 AI 模型能力指標隔離：前者是工程品質，後者需要真實樣本、對照與量測，不能互相代替。

## 12. 分期工作包、驗收與回滾

| 階段 | 交付物 | 明確驗收條件 | 不通過則 |
|---|---|---|---|
| P0 規約與工具 | RFC、事件 JSON Schema、mock verifier、可重播測試夾具 | 來源與版本完整、事件分類無混算、隱私測試通過、CPU fixture 重播一致 | 先修 schema；不得進 P1 |
| P1 外部 DAS | frozen model adapter、policy、archive、budget、獨立 verifier | 所有硬性權限測試通過；能輸出正確 unresolved；B0–B5 公平對照可執行 | 停在研究原型，不宣稱效益 |
| P2 控制器學習 | offline/on-policy controlled policy training、held-out tests | 每個 optimizer event 可追溯；表徵／推論／訓練事件分離；無資料漏洩；優於對照的證據可審計 | 回滾 frozen P1 |
| P3 隱狀態循環 | adapter/recurrent block、BPTT 與 TBPTT 消融、profiler receipt | 梯度形狀與有限差分抽查通過；無跨路徑 KV 污染；峰值記憶體受控 | 返回 P2 |
| P4 MoE／跨域 | 雙層路由、domain bridge、load monitor | domain_id 與 expert_id 不混同；跨域映射義務可檢驗；可與無 MoE 對照 | 封存為未證實擴充 |
| P5 外部驗證 | 預註冊任務、固定時窗評估、效益與成本報告 | 公開 raw metric、可信 CI、零未授權外部動作，報告失敗與負向結果 | 不發布產品能力結論 |

預設安全閘門（必須嚴格等於 0）：未授權工具行動、源內容偷換、測試 gold 覆寫、私人資訊被公開。模型能力方面不設假的既成達標數字：預先定義可比較、可重複、可支付的實驗閾值，再決定是否進入下一階段。

每階段保留模型 revision、資料切分、測試程式、環境依賴、成本紀錄和決策紀錄。禁止修改歷史測量原始紀錄；重算以 append-only correction event 表示。

## 13. 具體工程 Backlog（建議開發順序）

- ENG-001：定義 TaskContract、RepresentationCandidate、VerificationReceipt、CognitiveEvent 的 JSON Schema；加入 fail-closed validation。
- ENG-002：建立 SQLite 或 JSONL append-only ledger，含 event_id 去重、UTC timestamp、run version、來源 SHA-256。
- ENG-003：建立 deterministic mock 模型／checker；涵蓋同輸入、改 representation、可驗證／未知／被拒絕的所有分支。
- ENG-004：建立最小 SourceStore + ObligationExtractor；每個義務可回溯到 source span；來源不可覆寫。
- ENG-005：建立 rule-based CognitiveController 與 STOP 理由的固定枚舉；外部權限由獨立 guard 驗證。
- ENG-006：建立 B0–B5 對照 harness；成本預算同一套 meter，計入 verifier。
- ENG-007：接一個開放權重本地模型；固定 tokenizer/model hash、precision、版本與精確推論參數；記憶體足跡與 GPU 實測。
- ENG-008：整理已授權、可驗證的數學／程式／沙盒 Agent 測試切分，準備真正的 held-out evaluation。
- ENG-009：在非評估集蒐集受控路由軌跡；測試是否存在超越等成本重試的增益，再決定 P2 是否值得。
- ENG-010：如 P1 有正面證據，再實作學習式控制器、梯度更新計數與 TBPTT 消融。
- ENG-011：若 B/C 路線成立，實作模型內部 recurrence 與 optional MoE adapter；同時保留沒有 MoE 的對照。
- ENG-012：建立研究指標 export；資料處理與 FSL 原有 append-only 時間與證據分類規範相容。

建議每項工作拆成對應 issue 或 PR；本次**只提交本工程 RFC，並不宣稱上述程式已完成**。

## 14. 安全、授權與運維風險

1. **模型—驗證器共模失誤**：不可用同一回答模型的主觀同意當獨立驗證；可驗證任務優先使用確定性工具。
2. **提示與資料注入**：source text 是待分析資料，不能越權寫入系統指令；跨域文件或檢索回傳內容同理。
3. **Agent 副作用**：模擬沙盒先行；外部執行後禁止事後「重新理解」來合理化既成越權行為。
4. **儲存成本與隱私**：完整 Tensor/梯度追蹤高成本且高敏感性；預設記錄摘要與 hash，必要的內部追蹤另以受控儲存保存。
5. **資料歸因過度主張**：參與訓練、梯度非零、特徵活化、性能改善及某訓練例子的因果影響均為不同層次。
6. **過擬合控制**：DAS 可以學到特定 benchmark 的 prompt 策略；需要跨題型、時序與跨語言 held-out。
7. **停止退化**：不要強迫每題都探索 4 次；低風險、完整驗證、簡單任務應允許一步完成。
8. **硬體路線**：在投入 500M–2B 或更大自研 backbone 前，先量測 GPU 記憶體、吞吐、上下文長度、adapter optimizer state 等實際成本，不能以參數量直接推論本機可訓練性。

## 15. 尚未決定、應以實驗裁定的架構分歧

| 設計選項 | 優點 | 風險 | 裁定證據 |
|---|---|---|---|
| rule-based vs learned cognitive router | 可審計／可能適應性更高 | 手工規則偏置／政策訓練不穩 | 等預算 held-out 比較 |
| source re-prefill vs hidden-state recurrent | 易插拔／可能節省文字再生成 | 重算成本／模型侵入與漂移 | GPU、延遲與品質 Pareto |
| shared refinement block vs step-specific block | 參數少／表達力高 | 固定路徑偏差／參數膨脹 | 參數匹配消融 |
| fixed-step vs adaptive halting | 易實作／可省成本 | 過度思考／停止判錯 | 按難度分層的效益與成本 |
| without MoE vs separated cognitive + MoE router | 易驗證／可選擇性稀疏運算 | 單模型容量／路由複雜性 | latency、load、quality 和穩定性 |
| TBPTT vs full BPTT | 省記憶體／梯度路徑較完整 | 截斷偏差／記憶體壓力 | 梯度檢查、收斂與外部評估 |

## 16. 文件完成與工程完成的清楚邊界

**本 RFC 完成時可以說**：已定義系統分層、認知動作、可觀測事件、外部 API 合約、三種接入路線、候選梯度路線、測試對照、驗收及回滾規約。

**尚不能說**：已開發可工作的 DAS runtime、已訓練 DAS-L、已驗證新神經網路梯度、已降低幻覺、已取得跨模型提升、已證明「理解深度」可被唯一量測、已完成 MoE 聯動或已申請並完成任何專利。

工程實現應以**可重播的最小反例、等預算比較、外部驗證、型別嚴格的學習帳本、以及負向結果可被保留**為首要目標。

## 17. 對應的前六篇 canonical 研究

1. [01 — 基本問題](DAS_ARL_01_Deep_Attention_Spectrum_Foundations_2026-11-09.md)
2. [02 — 狀態與動態控制](DAS_ARL_02_Formal_Structure_Dynamic_Control_2026-11-09.md)
3. [03 — 同域、跨域與 MoE 分層](DAS_ARL_03_Intra_Domain_Cross_Domain_Hybrid_Expert_Routing_2026-11-09.md)
4. [04 — DAS-L 梯度](DAS_ARL_04_Learning_Methodology_Gradient_Adaptation_2026-11-09.md)
5. [05 — DAS-LL 事件帳本](DAS_ARL_05_Learning_Spectrum_Ledger_Representation_Trajectories_Neural_Coupling_2026-11-09.md)
6. [06 — 驗證與成本邊界](DAS_ARL_06_Validation_Benefits_Cost_Boundaries_2026-11-09.md)

## 18. 既有技術與工程參考文獻（核對至 2026-11-09）

1. Dehghani et al. (2018), *Universal Transformers*, https://arxiv.org/abs/1807.03819 — 循環更新與動態計算的既有技術。
2. Geiping et al. (2025), *Scaling up Test-Time Compute with Latent Reasoning: A Recurrent Depth Approach*, https://arxiv.org/abs/2502.05171 — 隱空間反覆計算，不等於本 RFC 已實作。
3. Huang et al. (2026), *Latent Recurrent Transformer*, https://arxiv.org/abs/2605.26797 — 2026 年相關 latent recurrence 研究。
4. Kohli et al. (2026), *Loop, Think, & Generalize*, https://arxiv.org/abs/2604.07822 — 同時提示過度思考（overthinking）風險。
5. Bai, Kolter & Koltun (2019), *Deep Equilibrium Models*, https://papers.nips.cc/paper/2019/hash/01386bd6d8e091c2ab4c7c7de644d37b-Abstract.html — 隱式微分的適用前提。
6. Fedus et al. (2021), *Switch Transformers*, https://arxiv.org/abs/2101.03961 — MoE 作為稀疏計算機制的參考。
7. Kumar et al. (ICLR 2025), *Training Language Models to Self-Correct via Reinforcement Learning*, https://proceedings.iclr.cc/paper_files/paper/2025/hash/871ac99fdc5282d0301934d23945ebaa-Abstract-Conference.html — 自我修正政策訓練的既有先例。
8. Chang et al. (ICLR 2025), *Scalable Influence and Fact Tracing for Large Language Model Pretraining*, https://proceedings.iclr.cc/paper_files/paper/2025/hash/65798a76cc176c29b6bfefe84b0a03ff-Abstract-Conference.html — 影響與事實來源不可混為一談。
9. PyTorch, *torch.utils.checkpoint*, https://docs.pytorch.org/docs/main/utils/checkpoint.html — 訓練記憶體與重計算規約。
10. PyTorch, *torch.profiler*, https://docs.pytorch.org/docs/main/profiler — 計算與記憶體實際量測 API。

---

**版本記錄 v0.1.0（2026-11-09）**：首次工程 RFC；狀態 PROPOSED_NOT_IMPLEMENTED。未執行 DAS 新模型訓練，無真實模型比較數據。本文件可作為後續 GitHub issue、PR 與實驗設計的工程依據；不能將完成此文件當作已完成實作。