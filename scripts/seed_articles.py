"""
Seed / refresh demo articles (zh+en) into Supabase `articles`.
Long-form, news-driven blog style. Upserts by slug.
"""
import re, warnings
warnings.filterwarnings("ignore")

creds = {}
for line in open("/Users/jay/Desktop/investment-system/.streamlit/secrets.toml"):
    m = re.match(r'\s*(\w+)\s*=\s*"([^"]*)"', line)
    if m:
        creds[m.group(1)] = m.group(2)
from supabase import create_client
sb = create_client(creds["SUPABASE_URL"], creds["SUPABASE_KEY"])

IMG1 = "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1200&q=70"
IMG2 = "https://images.unsplash.com/photo-1612010167108-3e6b327405f0?auto=format&fit=crop&w=1200&q=70"
IMG3 = "https://images.unsplash.com/photo-1535320903710-d993d3d77d29?auto=format&fit=crop&w=1200&q=70"
IMG4 = "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?auto=format&fit=crop&w=1200&q=70"

ARTICLES = [
{
  "slug": "discipline-beats-prediction-june-2026",
  "cover_url": IMG1,
  "published": True,
  "created_at": "2026-06-09T09:00:00Z",
  "title_zh": "AI 股急跌、聯準會轉鷹：2026 下半年，投資人該盯緊的五件事",
  "title_en": "AI Selloff, a Hawkish Fed: Five Things Investors Should Watch in 2H 2026",
  "excerpt_zh": "六月初那斯達克單日重挫逾 4%，市場從「AI 無敵」瞬間切換到「會不會升息」。這不是末日，而是一次提醒：下半年真正該盯的，是這五件事。",
  "excerpt_en": "The Nasdaq fell over 4% in a day in early June, flipping the mood from 'AI can do no wrong' to 'will the Fed hike?' Not doomsday — just a reminder of the five things that actually matter in the second half.",
  "body_zh": """六月的第一週，市場給所有人上了一課。

那斯達克單日重挫 **逾 4%**，創下年內最大跌幅；標普 500 下跌 2.6%，道瓊一度狂瀉近 700 點。導火線有兩個：一是博通（Broadcom）財報後**未上調 AI 晶片展望**，讓市場開始懷疑這波 AI 軍備競賽是否降溫；二是五月新增 **17.2 萬個非農就業**遠優於預期，反而讓投資人擔心——經濟太強，聯準會年底前**再升息**的機率，一個月內從 26% 跳到 43%。

一天之內，敘事從「AI 無敵」切換成「利率會不會回頭」。這正是市場最真實的樣子。

## 一、聯準會：新主席、新規則

這次是新任主席 **Kevin Wash** 上任後的第一場會議。市場過去習慣「跌深就有人來救」，但策略師普遍提醒：新主席不一定願意在估值偏高時，於第一個壓力訊號就出手相救。**別再把「Fed put（聯準會兜底）」當成理所當然。**

## 二、油價與地緣風險

中東（伊朗）衝突造成的供應疑慮，讓油價成為下半年最大變數之一。油價走勢可能直接決定通膨、進而決定利率路徑——也就決定了股市是續攻還是熄火。

## 三、AI 的「集中度風險」

AI 仍是市場引擎：估計今年 **約 40% 的標普 500 每股盈餘成長來自 AI 相關投資**。但反過來說，少數幾檔權值股扛起了大部分漲幅——這既是機會，也是風險。**當大家都擠在同一艘船上，船一晃，所有人都會晃。**

## 四、債券回來了

過去十年「除了股票沒得選（TINA）」的時代結束了。在較高的利率下，**債券的風險調整後報酬重新變得有競爭力**。這代表資產配置的選項變多，現金與固定收益不再只是「等待」，而是真正的選擇。

## 五、紀律，才是你能控制的變數

沒有人能準確預測下一根 K 線。霍華·馬克斯（Howard Marks）說得直接：「**你無法預測，但你可以準備。**」巴菲特更早就提醒：「**別人貪婪時恐懼，別人恐懼時貪婪。**」

急跌時，真正能依靠的不是預測能力，而是**事先寫好的規則**——這也是結構型商品（Structured Note）的核心：KO（敲出）、KI（敲入）、配息、比價日，全部在冷靜時就約定好。市場恐慌時，你看的是水位，不是情緒。

## 投資人該記住的重點

- **不要被單日波動嚇出場**，但也別假裝風險不存在
- **檢查集中度**：你的部位是不是都壓在同一個主題上？
- **留一點現金/固定收益**當選擇權，別人被迫賣時你才有子彈
- **把決策提前到冷靜時做**，用規則取代情緒

下半年大概率還會震盪。能不能穿越，取決於你出發前準備了多少。""",
  "body_en": """The first week of June taught everyone a lesson.

The Nasdaq plunged **more than 4%** in a single session — its worst day of the year. The S&P 500 fell 2.6% and the Dow briefly shed nearly 700 points. Two triggers: Broadcom **failed to raise its AI-chip outlook**, sparking doubts about whether the AI arms race is cooling; and a much stronger-than-expected **172,000 jobs** added in May made investors worry the opposite — that a hot economy could push the Fed to **hike again** before year-end, with those odds jumping from 26% to 43% in a month.

In a single day the story flipped from "AI can do no wrong" to "are rates turning back up?" That is what markets really look like.

## 1. The Fed: new chair, new rules

This is the first meeting under new chair **Kevin Wash**. Markets have grown used to "buy the dip, someone will rescue it" — but strategists warn the new chair may not be inclined to rescue a richly valued market at the first sign of stress. **Stop taking the "Fed put" for granted.**

## 2. Oil and geopolitics

Supply fears from the conflict involving Iran make oil one of the biggest swing factors for the second half. The path of oil could drive inflation, then rates — and therefore whether stocks soar or stall.

## 3. AI's concentration risk

AI is still the engine: an estimated **~40% of S&P 500 EPS growth this year comes from AI-related investment**. But the flip side is that a handful of mega-caps carry most of the gains — both opportunity and risk. **When everyone crowds onto one boat, a small wave rocks all of them.**

## 4. Bonds are back

The decade of "there is no alternative" (TINA) to stocks is over. At higher rates, **bonds' risk-adjusted returns are competitive again.** Cash and fixed income are no longer just "waiting" — they're real choices.

## 5. Discipline is the variable you control

No one reliably calls the next candle. Howard Marks put it plainly: "**You can't predict, but you can prepare.**" Buffett said it earlier: "**Be fearful when others are greedy, and greedy when others are fearful.**"

In a selloff, what you rely on isn't prediction but **rules set in advance** — which is the heart of a Structured Note: KO, KI, coupon and observation dates, all agreed while you're calm. When markets panic, you look at the levels, not the emotion.

## What investors should remember

- **Don't let a single down day scare you out** — but don't pretend risk doesn't exist
- **Check your concentration:** is everything riding on one theme?
- **Keep some cash / fixed income** as optionality, so you have ammunition when others are forced to sell
- **Make decisions while calm,** and let rules replace emotion

The second half will likely stay choppy. Whether you get through depends on how well you prepared before setting out.""",
},
{
  "slug": "buffett-cash-philosophy-2026",
  "cover_url": IMG2,
  "published": True,
  "created_at": "2026-06-06T09:00:00Z",
  "title_zh": "巴菲特坐擁 3,730 億現金：高估值時代的生存法則",
  "title_en": "Buffett's $373 Billion in Cash: Survival Rules for an Expensive Market",
  "excerpt_zh": "當市值對 GDP 來到 227%、波克夏現金創新高，「股神」其實已經把答案寫在帳上。這篇談的，是高估值時代你我都用得上的五條生存法則。",
  "excerpt_en": "With market cap to GDP at 227% and Berkshire's cash at a record, the Oracle has already written his answer on the balance sheet. Here are five survival rules the rest of us can use.",
  "body_zh": """2026 年，波克夏的現金部位攀升到約 **3,730 億美元**——史上最高。面對近期回檔，巴菲特沒有大舉進場。他的訊息一如過去多年：**等的是真正的危機，不是稍微便宜一點的價格。**

這不是看空，而是紀律。

## 「玩火」的估值

巴菲特曾說，當美股總市值對 GDP 的比率超過 200% 就是「**玩火**」。如今這個數字來到約 **227%**，遠在警戒線之上。高估值不代表明天就崩——但它代表兩件事：**未來預期報酬變低、可以犯錯的空間變小。**

## 現金不是懶惰，是選擇權

很多人把持有現金看成「沒在做事」。但對紀律型投資人來說，現金是一種**選擇權**：當別人被迫賣出時，你才有子彈買進好資產。蒙格（Charlie Munger）說得最傳神：

> 「大錢不是在買進或賣出時賺到的，而是在**等待**裡。」

## 五條高估值時代的生存法則

1. **規則一：不要虧損；規則二：別忘了規則一。** 巴菲特這句玩笑話，其實是整套哲學的核心——先求活著，再求賺多。
2. **別人貪婪時恐懼，別人恐懼時貪婪。** 情緒是投資人最大的敵人。
3. **適度分散，但要懂你買的東西。** 巴菲特說：「分散是對無知的保護；如果你清楚自己在做什麼，過度分散沒有意義。」——重點不是「買很多」，而是「懂」。
4. **時間是朋友，衝動是敵人。**（約翰·伯格 John Bogle）長期複利的威力，來自不被短線甩下車。
5. **留一份現金，是策略不是膽小。** 不必滿倉才安心。

## 對一般投資人的啟示

你不需要 3,730 億，但你可以借用同一套心法：**控制下檔、保留彈藥、用結構與紀律取代追高殺低。** 結構型商品之所以受青睞，正是因為它把「最差情況」事先量化——在高估值、高不確定的環境裡，先知道自己能承受多少，比預測漲多少更重要。

耐心，始終是巴菲特最被低估的能力。""",
  "body_en": """In 2026, Berkshire Hathaway's cash pile climbed to roughly **$373 billion** — an all-time high. Faced with the recent pullback, Buffett didn't pile in. His message is the same as it's been for years: **wait for real distress, not for prices that are merely a bit cheaper.**

That's not bearishness. It's discipline.

## "Playing with fire" valuations

Buffett once said that when total U.S. market cap to GDP exceeds 200%, you're "**playing with fire.**" Today that ratio sits near **227%**, well above the warning line. High valuations don't guarantee a crash tomorrow — but they do mean two things: **lower expected returns ahead, and less room for error.**

## Cash isn't laziness — it's optionality

Many see cash as "doing nothing." For a disciplined investor, cash is **optionality**: when others are forced to sell, you have ammunition to buy good assets. Charlie Munger said it best:

> "The big money is not in the buying or the selling, but in the **waiting**."

## Five survival rules for an expensive market

1. **Rule #1: don't lose money. Rule #2: don't forget Rule #1.** Buffett's joke is the whole philosophy — survive first, then earn.
2. **Be fearful when others are greedy, and greedy when others are fearful.** Emotion is the investor's biggest enemy.
3. **Diversify sensibly — but understand what you own.** Buffett: "Diversification is protection against ignorance; it makes little sense if you know what you are doing." The point isn't "own a lot," it's "understand."
4. **Time is your friend, impulse is your enemy.** (John Bogle) Compounding rewards those who don't get shaken off the ride.
5. **Holding cash is strategy, not timidity.** You don't need to be fully invested to be safe.

## What it means for the rest of us

You don't need $373 billion, but you can borrow the mindset: **control the downside, keep dry powder, and let structure and discipline replace chasing highs and panic-selling.** Structured Notes are popular precisely because they quantify the worst case in advance — and in an expensive, uncertain market, knowing how much you can bear matters more than guessing how much you'll gain.

Patience remains Buffett's most underrated skill.""",
},
{
  "slug": "howard-marks-is-it-a-bubble-cycles-risk",
  "cover_url": IMG3,
  "published": True,
  "created_at": "2026-05-30T09:00:00Z",
  "title_zh": "「這是泡沫嗎？」讀懂市場週期，比預測時點更重要",
  "title_en": "\"Is It a Bubble?\" Reading Market Cycles Beats Timing Them",
  "excerpt_zh": "霍華·馬克斯花了一整年問同一個問題。答案沒那麼重要，重要的是他教我們怎麼「讀週期」——這是每位投資人都該學會的一課。",
  "excerpt_en": "Howard Marks spent a year asking one question. The answer matters less than what he teaches us about reading cycles — a lesson every investor needs.",
  "body_zh": """巴菲特曾說：「**霍華·馬克斯的備忘錄一到，我會第一個打開來讀，每次都學到東西。**」2026 年，馬克斯在多份備忘錄裡反覆追問同一件事：**這是泡沫嗎？**

他原本對 AI 抱持懷疑，後來與一群三、四十歲的工程師深談後，重新調整了看法。但真正的重點不是他對 AI 的結論，而是他**思考風險的方法**。

## 先避開輸家，才談贏家

馬克斯最核心的觀念之一：建立長期財富，靠的不是「抓住最會漲的那一檔」，而是「**持續避開會讓你出局的那些**」。少輸，本身就是一種贏。在一個少數權值股扛起多數漲幅的市場裡，這句話格外重要。

## 怎麼「讀週期」？

市場永遠在「過度樂觀」與「過度悲觀」之間擺盪。你不需要預測轉折的**精確時點**，但你該知道現在大概站在週期的哪個位置。幾個亢奮的訊號：

- 大家開始相信「這次不一樣」
- 壞消息被忽略，好消息被無限放大
- 沒有人再談風險，只談報酬
- 連從不投資的人都來問明牌

> 「**最危險的事，莫過於相信『沒有風險』。**」

當情緒越亢奮，未來報酬通常越低、風險越高——這就是週期的鐵律。

## 把觀念落地

- **用配置與障礙條件（KO / KI）控制下檔**，而不是賭單一方向
- **在亢奮時保守一點，在恐慌時勇敢一點**
- **把「活得久」放在「賺得快」之前**
- **定期檢視**：我現在承擔的風險，是因為看懂了，還是因為大家都在做？

## 結語

泡沫與否，事後才會有答案；但週期的位置，現在就能感受。讀懂週期，你就不會在最危險的時候，做出最樂觀的決定。這，比任何預測都值錢。""",
  "body_en": """Buffett once said: "**When a memo from Howard Marks arrives, it's the first thing I open — I always learn something.**" Through 2026, Marks kept asking one question across his memos: **is it a bubble?**

He started out skeptical of AI, then revised his view after long conversations with engineers in their thirties and forties. But the real lesson isn't his conclusion on AI — it's his **method for thinking about risk.**

## Avoid losers before chasing winners

One of Marks's core ideas: building lasting wealth isn't about catching the single biggest gainer — it's about **consistently avoiding the things that knock you out.** Losing less is itself a way of winning. In a market where a few mega-caps carry most of the gains, that matters more than ever.

## How do you "read" a cycle?

Markets forever swing between excess optimism and excess pessimism. You don't need to time the **exact** turn, but you should sense roughly where you stand. Signs of euphoria:

- People start believing "this time is different"
- Bad news is ignored, good news is amplified endlessly
- No one talks about risk anymore, only returns
- Even people who never invest start asking for tips

> "**Nothing is more dangerous than believing there is no risk.**"

The more euphoric the mood, the lower future returns and the higher the risk — that's the iron law of cycles.

## Putting it to work

- **Control the downside with allocation and barriers (KO / KI)**, rather than betting on one direction
- **Be a little more cautious in euphoria, a little braver in panic**
- **Put "surviving long" ahead of "earning fast"**
- **Review regularly:** am I taking this risk because I understand it, or because everyone else is?

## The takeaway

Whether it's a bubble only becomes clear in hindsight — but where you stand in the cycle, you can feel today. Read the cycle, and you won't make your most optimistic decision at the most dangerous moment. That is worth more than any forecast.""",
},
{
  "slug": "structured-notes-101-ko-ki-coupon-explained",
  "cover_url": IMG4,
  "published": True,
  "created_at": "2026-05-22T09:00:00Z",
  "title_zh": "結構型商品入門：配息、KO、KI 一次搞懂（附 4 個常見誤解）",
  "title_en": "Structured Notes 101: Coupon, KO and KI — Plus 4 Common Myths",
  "excerpt_zh": "很多人買了結構型商品，卻說不清楚自己買了什麼。這篇用最白話的方式，帶你三分鐘看懂 KO、KI、配息，以及最容易踩的四個誤解。",
  "excerpt_en": "Plenty of people own a structured note but can't explain what they bought. In three minutes, here's KO, KI and coupon in plain language — and the four myths that trip people up.",
  "body_zh": """結構型商品（Structured Note，常簡稱 SN）聽起來複雜，但拆開來其實只有幾個關鍵零件。把這幾個詞搞懂，你就掌握了八成。

## 三個關鍵名詞

- **期初價（Initial）**：成立當天，標的股票的參考價格。之後一切漲跌都跟它比。
- **KO（敲出 / Knock-Out）**：當標的價格**漲到**約定水位（例如期初的 100%）時觸發，通常代表「**提前出場、領回本金加配息**」。對投資人多半是好事。
- **KI（敲入 / Knock-In）**：當標的價格**跌到**約定的下限（例如期初的 50%）時觸發，代表**下檔保護被打破**，到期時可能要承受損失或被轉換成股票。

簡單記：**KO 在上面（好），KI 在下面（要小心）。**

## 配息怎麼來

配息（Coupon）是你持有期間可領的收益，通常以年化百分比表示。它就像「在等待 KO 的期間，先領的利息」。但記住——**配息高，往往代表承擔的下檔風險也高。**

## 4 個最常見的誤解

1. **「配息越高越好」** ✗ 高配息常伴隨更激進的條件或更弱的標的。要看的是「**風險與報酬是否相稱**」，不是只看數字大小。
2. **「有保本就沒風險」** ✗ 多數 SN 是「有條件保護」，不是無條件保本。KI 一旦觸發，保護就可能消失。
3. **「跌破期初就一定賠」** ✗ 不一定。只要沒觸發 KI、且到期回到約定水位，結果可能完全不同。價格在期初下方，不等於已經賠錢。
4. **「買了就不用管」** ✗ 比價日、KO/KI 水位都是動態的。**追蹤**比「買進」更重要。

## 投資人該做的三件事

- **搞懂自己的下檔**：最差情況會怎樣？能承受嗎？
- **看懂條款，而不是只看配息**
- **持續追蹤水位與比價日**，重要事件要有人提醒你

結構型商品不是賭博，也不是穩賺——它是一套「**用規則換取機率**」的工具。理解它，你才能安心地把它放進配置裡。""",
  "body_en": """Structured Notes (often just "SN") sound complicated, but break one apart and there are only a few key parts. Understand these terms and you've got 80% of it.

## Three key terms

- **Initial price:** the reference price of the underlying on the start date. Everything after is measured against it.
- **KO (Knock-Out):** triggers when the underlying **rises to** an agreed level (e.g., 100% of initial), usually meaning "**early redemption — get your principal back plus coupon.**" Generally good for the investor.
- **KI (Knock-In):** triggers when the underlying **falls to** an agreed floor (e.g., 50% of initial), meaning **downside protection is breached** — at maturity you may take a loss or be converted into shares.

Simple memory aid: **KO is up top (good); KI is down below (be careful).**

## Where the coupon comes from

The coupon is the income you collect while holding, usually shown as an annualized percentage — like "interest paid while you wait for a KO." But remember: **a higher coupon often means more downside risk.**

## Four common myths

1. **"Higher coupon is always better."** ✗ High coupons often come with more aggressive terms or weaker underlyings. Look at whether **risk and reward are proportionate**, not just the headline number.
2. **"Protected means no risk."** ✗ Most notes offer *conditional* protection, not unconditional principal guarantee. Once KI triggers, the protection can vanish.
3. **"Below initial means you've lost."** ✗ Not necessarily. If KI never triggers and the price returns to the agreed level by maturity, the outcome can be entirely different. Being below initial isn't the same as a realized loss.
4. **"Buy it and forget it."** ✗ Observation dates and KO/KI levels are dynamic. **Tracking** matters more than buying.

## Three things investors should do

- **Understand your downside:** what's the worst case, and can you bear it?
- **Read the terms — not just the coupon.**
- **Track levels and observation dates,** with alerts for the events that matter.

A structured note isn't gambling, and it isn't a sure thing — it's a tool that **trades rules for probabilities.** Understand it, and you can hold it in your allocation with confidence.""",
},
]

for a in ARTICLES:
    try:
        sb.table("articles").upsert(a, on_conflict="slug").execute()
        print("upserted:", a["slug"])
    except Exception as e:
        print("FAILED", a["slug"], str(e)[:160])
print("done")
