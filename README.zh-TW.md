# arch-blueprint

[English](README.md) | **繁體中文**

你打開一個 repo，不管是自己的還是別人的，想用一張圖看懂各部分怎麼連在一起。請你的 coding agent 畫出它的架構，就會在 `docs/architecture/overview.svg` 得到一張黑白、藍圖風格的 SVG，而且交到你手上之前已經由腳本檢查過。

![文件搜尋 App 的架構總覽範例，以細黑線畫在米白底上：瀏覽器 SPA 呼叫 API 伺服器和查詢服務，查詢服務讀取 PostgreSQL 與向量資料庫並呼叫 LLM API，另有一條離線匯入管線把資料填進物件儲存與向量索引](skills/arch-blueprint/assets/example-overview.svg)

- **先提案**：agent 會讀 README、進入點、資料夾結構和 import，接著用文字列出分區、節點和資料流，等你確認後才開始畫。
- **一頁就好**：最多 12 個節點、12 條連線、6 個資料流標籤。放不下的專案會退回提案階段，改成更粗的拆法，絕不是把字縮小。
- **固定風格**：只用米白紙色 `#faf8f4` 和墨黑 `#1a1a1a`，以虛線圓角框表示分層，24 px 線條圖示取自內附的 13 個，開口 V 形箭頭，JetBrains Mono 字型，而且不管你用什麼語言下指令，圖內文字一律是英文。
- **腳本把關**：`check.py` 會量測顏色、語言、數量、60 px 邊界、4 px 格線、文字溢出、圖示是否原樣複製，以及連線規則，例如只能直角轉折、線不能穿過節點或標籤、無法避免的交叉處都要畫跳線。只要有任何錯誤，就以 1 結束。

用 checker 檢查一張混進多餘顏色和中文標籤的草稿：

```
$ python3 skills/arch-blueprint/scripts/check.py overview.svg
```

```
✗ overview.svg  (11 錯誤, 0 警告)
    E-LANG: 文字「瀏覽器」含中日韓字元；圖內文字一律英文
    E-COLOR: <path > stroke="#d33" 不是米白 #faf8f4 或墨黑 #1a1a1a
    E-COLOR: <symbol icon-browser> stroke="#d33" 不是米白 #faf8f4 或墨黑 #1a1a1a
    …
```

skill 的指示和 checker 的訊息都以繁體中文撰寫；圖一律是英文。

## 它怎麼運作

```
「畫出架構圖」 ──► agent 讀 README、進入點、import
                              │
              提案：分區 × 節點 × 資料流 ──► 你確認或調整
                              │
          docs/architecture/overview.svg ──► check.py ──► 修到 0 個錯誤
```

這個 skill 就是一份文字指示檔加上一支 Python 腳本。不用安裝任何東西，也不會連上網路。

## 安裝

你需要一個能讀取 [Agent Skills](https://agentskills.io) 的 coding agent，例如 Claude Code、Codex、Cursor 或 Gemini CLI，以及執行 checker 用的 Python 3。

1. 用 `npx skills add cholateio/arch-blueprint` 加入 skill。在 Claude Code 裡也可以改成執行 `/plugin marketplace add cholateio/arch-blueprint`，再執行 `/plugin install arch-blueprint@arch-blueprint`。或者把 `skills/arch-blueprint/` 複製到你所用工具的 skills 資料夾（Claude Code 是 `~/.claude/skills/`）。
2. 把 `skills/arch-blueprint/SKILL.md` 讀過一遍。你的 agent 會被要求做的事全都寫在裡面。
3. 在任何專案裡說「幫這個 repo 畫一張架構總覽圖」，然後回覆它的提案。

## 隱私與安全

- skill 是純文字指示，你的 agent 會以你的權限照著做。安裝前先讀過 `SKILL.md`。
- `check.py` 只用 Python 標準函式庫。它只讀你傳給它的 SVG 檔，其他什麼都不讀。
- skill 本身不會把任何東西送出去；是你的 agent 在你自己的 session 裡讀 repo。
- 圖是一個自成一體的 SVG。checker 會拒絕外部圖片、漸層、濾鏡和陰影。

## 授權

[MIT](LICENSE)。整體結構和「用腳本驗證品味關卡」的想法受到 [cathrynlavery/diagram-design](https://github.com/cathrynlavery/diagram-design) 啟發；視覺風格是自己的。
