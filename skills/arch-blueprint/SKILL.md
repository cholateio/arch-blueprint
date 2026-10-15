---
name: arch-blueprint
description: Use when asked to draw an architecture diagram, system diagram, module map, overview or blueprint of a software project or codebase — any request to visualize how a repo's parts fit together, even without naming a format or style. 當使用者要求畫「架構圖」「系統圖」「模組圖」「overview」「藍圖／黑白線條風格的圖」，或想把專案結構視覺化時使用；即使沒指定 SVG 或風格也用本 skill，不要改用 Mermaid。
---

# arch-blueprint — 黑白線條系統架構圖

把軟體專案拆解成 **overview 層級**的架構圖，以極簡工程藍圖風格輸出單一 SVG 檔
（米白底、黑色細線、簡約線條 icon、分層容器）。
核心精神：**先分區、再連線；一張圖說一件事；風格服務於閱讀，不是裝飾。**

標準範例：`assets/example-overview.svg`。動手前先看一眼，照它的結構寫。

## 工作流程（依序執行，不可跳過確認步）

1. **分析專案**：讀 README、進入點、資料夾結構與主要 import 關係，識別
   實際的模組邊界（以職責與依賴為準，不是照資料夾照抄）。
2. **提案拆解**：用文字列出打算畫的「分區 × 節點 × 主要資料流」清單給使用者
   確認。列完先做一輪**刪減測試**，再送出：
   - 哪個節點拿掉後讀者仍看得懂？拿掉。
   - 哪兩個節點總是一起出現？合併。
   - 哪條箭頭從排版（上游在上、下游在下）就看得出來？拿掉。
   - 哪條線是次要關係（驗證、監控、設定）？降為虛線或省略。
   粒度不對就調整，**確認後才開始畫**。
3. **產出 SVG**：依下方規則寫出 `docs/architecture/overview.svg`。
4. **自檢**：先跑腳本，再逐項過自檢清單，全部修正後才交付：
   ```bash
   python3 <本 skill 目錄>/scripts/check.py docs/architecture/overview.svg
   ```
5. **（僅在使用者要求時）** 為個別模組產出細部圖 `docs/architecture/<模組>.svg`，
   同樣規則遞迴適用：該模組內部再分區、節點上限相同。

## 內容規則（畫什麼）

- **只畫 overview**：整張圖節點 ≤ 12 個、連線（含虛線）≤ 12 條。裝不下就是
  拆解太細，回到步驟 2 重新提案，而不是縮小字體硬塞。
- **分層容器**：用圓角虛線框把節點分組，預設分區為
  「前端 / 後端 / 資料層 / 雲端外部服務」，有離線批次流程（建庫、ETL、
  排程任務）時獨立成區。分區標題置於框內左上角。
- **每個節點最多兩行**：粗體名稱 + 一行職責（≤ 10 個中文字）。
  Stage/演算法/參數等細節一律降級為職責小字或省略。
- **箭頭只畫主要資料流**，方向單純（整體由上而下或由左而右）。
  箭頭不加文字標籤；語意不明時改寫節點的職責小字。
- 資料庫、快取、物件儲存放在「資料層」分區，線上與離線路徑分別指向它。

## 風格規格（怎麼畫）

**畫布**
- `<svg viewBox="0 0 1200 H">`，H 依內容決定，四周留 ≥ 60px 空白。
- 根元素帶 `role="img"` 與 `aria-labelledby`，第一個子元素是 `<title>`，
  其後 `<desc>` 一句話說明內容（見範例）。
- 背景：整張鋪 `<rect fill="#faf8f4"/>`（米白）。整張圖只有兩個顏色：
  米白底 `#faf8f4` 與墨黑 `#1a1a1a`。**禁止**任何其他色彩、漸層、陰影、濾鏡。
- 結構位置與尺寸（節點、容器的 x/y/寬/高、間距）一律落在 **4px 格線**上。

**文字**
- 字體：根元素設 `font-family="'JetBrains Mono','Noto Sans TC',monospace"`。
- 分區標題：16px、`letter-spacing="3"`、英文全大寫（如 `OFFLINE PIPELINE`），
  中文加註於下一行 12px；標題下畫一條 48px 短底線。
- 節點名稱：14px、weight 600；職責小字：11px、`fill-opacity="0.65"`。
- 主標題（可選）：頂部置中 28px、`letter-spacing="6"`。

**節點與容器**（畫法與群組方式照範例）
- 每個節點包在 `<g class="node">` 裡：矩形 `rx="10"`、`fill="#faf8f4"`
  `stroke="#1a1a1a"` `stroke-width="1.5"`，統一 **192×64**；icon 在左、
  名稱與職責在右（文字起點 x+56）。
- 每個分區包在 `<g class="zone">` 裡：`rx="16"`、`stroke-width="1.2"`
  `stroke-dasharray="5 5"`、無填色；標題與底線也放在同一個 g 內。
  容器內距 ≥ 24px，分區互不重疊，節點之間最小間距 ≥ 20px。
- 畫的順序：背景 → 分區 → 連線 → 節點。

**連線**（每條加 `class="edge"`）
- 實線 `stroke-width="1.5"`、開放式箭頭（V 形，不用實心三角）：
  ```svg
  <marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7"
    markerHeight="7" orient="auto-start-reverse">
    <path d="M2 1L8 5L2 9" fill="none" stroke="#1a1a1a" stroke-width="1.5"
      stroke-linecap="round" stroke-linejoin="round"/></marker>
  ```
- 次要關係（身分驗證、觀測、設定）用虛線 `stroke-dasharray="4 4"`、無箭頭。
- 只能水平或垂直，轉彎用直角 L 形（`M x,y V.. H.. V..`），**絕不可穿過任何
  節點或文字**。起點貼在節點邊緣，箭頭尖端停在目標節點邊緣外 6px。
- **出入口與邊垂直**：從上下邊出入的第一段必須是垂直線，從左右邊出入的必須是
  水平線。目標在正上／下方時走上下邊，在左右時走左右邊，不要從側面斜戳進去。
- **同一邊多條線要分開接點**：N 條線平均分佈在邊長 L 上（第 k 條在
  `L·k/(N+1)`），相鄰接點 ≥ 12px，離角落 ≥ 8px。
- **平行線錯開 ≥ 12px**，不可重疊共用線段。
- **交叉只能出現在不可避免時**，而且要在次要的那條線畫半圓跳線：往右走
  `H cx-8 a8,8 0 0,1 16,0`、往左走 `H cx+8 a8,8 0 0,0 -16,0`（cx 為交點）。
  能改路徑就改路徑，一張圖最多 1–2 個跳線。

**Icon**
- 從 `assets/icons.svg` 把需要的 `<symbol id="icon-…">` **原樣**複製到 `<defs>`，
  再以 `<use href="#icon-…" x=".." y=".." width="24" height="24"/>` 放在節點
  左側（x+16, y+20）。可用：browser、terminal、server、database、cache、
  bucket、cloud、shield、chip、file、gear、search、sparkle。
- 不要自行手繪或修改 icon；找不到對應的就不放 icon。

## 自檢清單（交付前逐項檢查）

- [ ] `python3 scripts/check.py <檔案>` 零錯誤；警告逐條看過並處理
- [ ] 節點 ≤ 12、連線 ≤ 12、只有米白與墨黑兩色
- [ ] 任何連線都不穿過節點或文字；轉彎皆為直角；交叉處有跳線
- [ ] 文字不溢出所屬矩形（中文字寬 ≈ 字級 × 1.0，英文 ≈ × 0.6）
- [ ] 分區容器互不重疊，內距 ≥ 24px；圖形之間最小間距 ≥ 20px
- [ ] icon 全部來自 icon 庫；用瀏覽器實際打開 SVG 看過一次
- [ ] 檔案輸出至 `docs/architecture/`，並告知使用者預覽方式
