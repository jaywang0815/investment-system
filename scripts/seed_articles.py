"""
Seed 3 demo articles (zh+en) into Supabase `articles`.
Run AFTER creating the table (scripts/articles_schema.sql).
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

ARTICLES = [
    {
        "slug": "discipline-beats-prediction-june-2026",
        "cover_url": IMG1,
        "published": True,
        "created_at": "2026-06-09T09:00:00Z",
        "title_zh": "市場急跌中，紀律為何勝過預測",
        "title_en": "In a Sharp Selloff, Why Discipline Beats Prediction",
        "excerpt_zh": "六月初那斯達克單日重挫逾 4%，AI 與晶片股領跌。市場越是劇烈波動，越能看出「紀律」比「猜頂猜底」更值得依靠。",
        "excerpt_en": "Early June saw the Nasdaq drop over 4% in a day, led by AI and chip names. The wilder the swings, the more discipline beats trying to call tops and bottoms.",
        "body_zh": """## 一天蒸發的，不只是數字

2026 年 6 月初，那斯達克單日重挫逾 4%，創下年內最大跌幅。AI 與半導體權值股領跌——博通未能上調 AI 晶片展望，引發市場對這波熱潮是否降溫的疑慮；同時五月新增 17.2 萬個就業機會優於預期，讓聯準會「年底前再升息」的機率明顯攀升。

## 沒有人能準確預測下一根 K 線

每一次急跌，總會有人事後說「我早就知道」。但真相是：沒有人能穩定地預測短線。能讓資產長期穩健的，不是預測能力，而是**事先設定好的紀律**——買進的理由、能承受的風險、以及觸發調整的條件。

## 結構型商品的角色

結構型商品（Structured Note）的價值，正在於把「條件」寫死在合約裡：KO（敲出）與 KI（敲入）水位、配息、比價日，都是事先約定。當市場恐慌時，你看的是水位與規則，而不是當下的情緒。

> 把決策提前到冷靜時做好，市場恐慌時就不必臨時起意。

## 我們的做法

- 依風險屬性配置，而非追逐當下最熱的標的
- 每日追蹤標的價格與 KO / KI 水位，重要事件主動通知
- 波動時回到規則，而不是回到情緒

市場還會再震盪，這是必然。能不能穿越，取決於你出發前準備了多少。""",
        "body_en": """## More than numbers vanished in a day

In early June 2026 the Nasdaq fell more than 4% in a single session — its worst day of the year. AI and semiconductor leaders led the drop: Broadcom's failure to raise its AI-chip outlook fueled doubts about whether the boom is cooling, while a stronger-than-expected 172,000 jobs added in May pushed up the odds the Fed hikes again before year-end.

## No one can predict the next candle

After every sharp drop, someone says "I knew it all along." The truth: no one reliably calls the short term. What keeps assets steady over time isn't prediction — it's **discipline set in advance**: why you bought, how much risk you can bear, and what triggers an adjustment.

## Where structured notes fit

The value of a Structured Note is that the conditions are written into the contract: KO (knock-out) and KI (knock-in) levels, coupon, observation dates — all agreed up front. When markets panic, you look at the levels and the rules, not the emotion of the moment.

> Make the decision while you're calm, so panic never forces an improvised one.

## How we work

- Allocate to your risk profile, not to whatever is hottest today
- Track underlyings and KO / KI levels daily, with proactive alerts
- In volatility, return to the rules — not to emotion

Markets will swing again; that's certain. Whether you get through depends on how well you prepared before setting out.""",
    },
    {
        "slug": "buffett-cash-philosophy-2026",
        "cover_url": IMG2,
        "published": True,
        "created_at": "2026-06-06T09:00:00Z",
        "title_zh": "巴菲特的「現金哲學」：等待真正的危機",
        "title_en": "Buffett's Cash Philosophy: Waiting for Real Distress",
        "excerpt_zh": "波克夏坐擁約 3,730 億美元現金，巴菲特的訊息一如既往：等的是真正的危機，而不是稍微便宜一點的價格。",
        "excerpt_en": "With Berkshire sitting on roughly $373B in cash, Buffett's message is unchanged: wait for real distress, not just slightly cheaper prices.",
        "body_zh": """## 史上最高的「按兵不動」

2026 年，波克夏的現金部位來到約 **3,730 億美元**。面對近期回檔，巴菲特的態度很清楚：這還不到他出手的門檻。他等的，是真正的危機，而不是「稍微便宜一點」。

## 「玩火」的估值

巴菲特曾說，當美股總市值對 GDP 的比率超過 200% 就是「玩火」。如今這個數字來到約 **227%**——遠高於警戒線。高估值不代表明天就崩，但它代表：未來的預期報酬變低、可承受的錯誤變少。

## 現金不是懶惰，是選擇權

持有現金常被誤解成「沒在做事」。但對紀律型投資人而言，現金是一種**選擇權**——當別人被迫賣出時，你才有子彈買進好資產。

> 真正的機會，往往出現在別人最恐慌的時候。

## 對一般投資人的啟示

- 不必滿倉才安心；留一部分彈藥，是策略不是膽小
- 用結構與紀律取代「追高殺低」
- 把目標放在「長期不被淘汰」，而不是「這一波賺最多」

耐心，是巴菲特最被低估的能力。""",
        "body_en": """## A record level of "doing nothing"

In 2026, Berkshire Hathaway's cash pile reached roughly **$373 billion**. Faced with the recent pullback, Buffett's stance is clear: this doesn't meet his threshold to act. He's waiting for real distress — not for prices that are merely a bit cheaper.

## "Playing with fire" valuations

Buffett once said that when total U.S. market cap to GDP exceeds 200%, you're "playing with fire." Today that ratio sits near **227%** — well above the warning line. High valuations don't mean a crash tomorrow, but they do mean lower expected returns ahead and less room for error.

## Cash isn't laziness — it's optionality

Holding cash is often mistaken for "not doing anything." For a disciplined investor, cash is **optionality**: when others are forced to sell, you have the ammunition to buy good assets.

> Real opportunity tends to appear when everyone else is most afraid.

## What it means for the rest of us

- You don't need to be fully invested to feel safe; keeping some dry powder is strategy, not timidity
- Replace "chase highs, panic-sell lows" with structure and discipline
- Aim to "not get knocked out over the long run," not to "make the most this rally"

Patience is Buffett's most underrated skill.""",
    },
    {
        "slug": "howard-marks-is-it-a-bubble-cycles-risk",
        "cover_url": IMG3,
        "published": True,
        "created_at": "2026-05-28T09:00:00Z",
        "title_zh": "霍華·馬克斯：「這是泡沫嗎？」讀懂週期與風險",
        "title_en": "Howard Marks: \"Is It a Bubble?\" — Reading Cycles and Risk",
        "excerpt_zh": "從質疑 AI 到重新思考，馬克斯提醒我們：投資的核心不是抓住贏家，而是先避開輸家、尊重週期。",
        "excerpt_en": "From doubting AI to rethinking it, Marks reminds us: investing isn't about catching winners first — it's about avoiding losers and respecting cycles.",
        "body_zh": """## 一份讓巴菲特「第一個打開」的備忘錄

巴菲特曾說：「霍華·馬克斯的備忘錄一到，我會第一個打開來讀，每次都學到東西。」2026 年，馬克斯在多份備忘錄中追問同一個問題：**這是泡沫嗎？**

## 先避開輸家，才談贏家

馬克斯最核心的觀念之一：建立長期財富，靠的不是「抓住最會漲的」，而是「**持續避開會讓你出局的**」。少輸，就是一種贏。

## 尊重週期，而非預測時點

市場總在「過度樂觀」與「過度悲觀」之間擺盪。你不需要預測轉折的精確時點，但你需要知道現在大概站在週期的哪個位置——情緒越亢奮，未來報酬通常越低、風險越高。

> 「你無法預測，但你可以準備。」——這正是風險管理的本質。

## 把觀念落地

- 用配置與障礙條件（KO/KI）控制下檔，而不是賭單一方向
- 在亢奮時保守一點，在恐慌時勇敢一點
- 把「活得久」放在「賺得快」之前

讀懂週期，你就不會在最危險的時候，做出最樂觀的決定。""",
        "body_en": """## A memo Buffett "opens first"

Buffett once said: "When a memo from Howard Marks arrives, it's the first thing I open — I always learn something." Through 2026, Marks kept asking the same question across his memos: **is it a bubble?**

## Avoid losers before chasing winners

One of Marks's core ideas: building lasting wealth isn't about catching the biggest gainer — it's about **consistently avoiding the things that knock you out**. Losing less is itself a way of winning.

## Respect cycles, don't time them

Markets swing between excess optimism and excess pessimism. You don't need to predict the exact turning point, but you should know roughly where in the cycle you stand — the more euphoric the mood, the lower future returns and the higher the risk tend to be.

> "You can't predict, but you can prepare." — that is the essence of risk management.

## Putting it to work

- Control the downside with allocation and barriers (KO/KI), rather than betting on one direction
- Be a little more cautious in euphoria, a little braver in panic
- Put "surviving long" ahead of "earning fast"

Read the cycle, and you won't make your most optimistic decision at the most dangerous moment.""",
    },
]

for a in ARTICLES:
    try:
        sb.table("articles").upsert(a, on_conflict="slug").execute()
        print("upserted:", a["slug"])
    except Exception as e:
        print("FAILED", a["slug"], str(e)[:150])

print("done")
