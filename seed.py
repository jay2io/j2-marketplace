#!/usr/bin/env python3
"""Deterministic seeder for the v2 'claws' marketplace (REDESIGN_PLAN.md).

Design A: the full data lives only in downloadable exports, so the generator
builds genuine accounts with DEEP activity (per-user review histories) and
hides the 100 bots in behavior, not names:
  - bot usernames/bios come from the SAME pools as genuine users (no tells);
  - the bot signature is joint: joined within days of each other + review
    ONLY one shared product + identical review text shared across the group
    + all reviews posted on a single day.

Planted traps (all genuine, recorded in labels):
  T1 fan burst    - older genuine accounts post 5-star reviews of one
                    product inside a 3-day window (a launch). Catches
                    product-burst-only detectors.
  T2 talkers      - genuine users who repeat their own 2 stock phrases
                    across many products. Catches self-repetition detectors.
  T3 lookalikes   - genuine users who joined in the same ~3-week span and
                    share one product. Catches join+product partial matches.

Usage:
    python3 seed_v2.py --variant old --seed 20261025 \
        --db /tmp/market-v2.sqlite3 --labels /tmp/labels-v2-old.json
"""
import argparse
import datetime as dt
import json
import os
import random
import sqlite3

PRODUCTS = [
    (1, "Aurora Wireless Headphones", "Over-ear noise-cancelling headphones, 40h battery.", 12999, "Audio"),
    (2, "BrewMaster Pour-Over Coffee Maker", "Glass pour-over dripper with walnut collar.", 8999, "Kitchen"),
    (3, "TrailBlaze Hiking Backpack 40L", "40L trail pack with ventilated back panel.", 11999, "Outdoors"),
    (4, "Lumen Desk Lamp", "Dimmable LED desk lamp, 5 color temperatures.", 4999, "Home"),
    (5, "VoltCharge 65W GaN Charger", "65W GaN USB-C fast charger, foldable prongs.", 3999, "Electronics"),
    (6, "Terra Ceramic Plant Pots (set of 3)", "Hand-glazed ceramic pots with drainage.", 3499, "Home"),
    (7, "StrideRun Running Shoes", "Cushioned road runners, breathable knit upper.", 14999, "Fitness"),
    (8, "PixelPro Webcam 4K", "4K webcam with auto-framing and dual mics.", 9999, "Electronics"),
    (9, "CozyNest Weighted Blanket", "15lb weighted blanket, bamboo cover.", 8999, "Home"),
    (10, "AquaPure Water Filter Pitcher", "10-cup filter pitcher, 2 filters included.", 4499, "Kitchen"),
    (11, "Nomad Stainless Steel Bottle 1L", "Vacuum insulated, keeps cold 24h.", 2999, "Outdoors"),
    (12, "EchoBuds True Wireless Earbuds", "True wireless earbuds, wireless charging case.", 7999, "Audio"),
]
PNAME = {pid: name for pid, name, _, _, _ in PRODUCTS}

G_TITLES = [
    "Great purchase", "Does the job", "Pleasantly surprised", "Solid", "Worth it",
    "Good, minor quibbles", "Exceeded expectations", "Fine for the price",
    "Would buy again", "Pretty good", "Not perfect but good", "Happy with it",
    "Better than expected", "Decent", "Really nice", "Impressed",
]
G_BODIES = [
    "Bought the {p} three weeks ago and it has held up well so far. Setup took about ten minutes.",
    "The {p} does exactly what the listing says. Shipping was fast, packaging was decent.",
    "I compared a few options before picking the {p}. Happy with the choice; the build quality feels solid.",
    "Using the {p} daily for a month now. No complaints, though I wish the instructions were clearer.",
    "The {p} is good value at this price. Not flawless, but I would recommend it to a friend.",
    "Ordered the {p} on a Tuesday, arrived Friday. Works as described, no surprises.",
    "I was skeptical about the {p} but it won me over. The finish is nicer in person than in photos.",
    "The {p} replaced an older model I had for years. Noticeably better in daily use.",
    "Took a star off because the {p} runs a little small, but otherwise very happy.",
    "My second time buying the {p} (first was a gift). Consistent quality both times.",
    "The {p} is straightforward and reliable. Nothing fancy, which is what I wanted.",
    "Read a lot of reviews before getting the {p}. They were mostly right: solid, dependable.",
    "The {p} arrived with a small scuff on the box but the item itself was perfect.",
    "I use the {p} every morning. It has become part of the routine without any fuss.",
    "Good {p}. Customer service answered my one question quickly, which I appreciated.",
    "The {p} feels well made. Time will tell on durability, but first impressions are good.",
    "Picked up the {p} during a sale. At full price I might hesitate, but on sale it is great.",
    "The {p} works fine for my needs. Setup was painless and it just works.",
    "I lent the {p} to my sister and she ordered her own the same week. Says a lot.",
    "The {p} is a bit heavier than I expected, but performance makes up for it.",
    "No regrets on the {p}. It solved the exact problem I bought it for.",
    "The {p} gets the job done. Four stars because the color is slightly off from photos.",
    "I have recommended the {p} to two coworkers already. Reliable and simple.",
    "The {p} survived a drop down the stairs, so durability gets full marks from me.",
    "Bought the {p} for my dad. He figured it out without calling me, which is the real review.",
    "The {p} is quiet, efficient, and looks good on the shelf. Very pleased.",
    "It took a week to get used to the {p}, now I would not go back.",
    "The {p} is exactly as pictured. Refreshing when listings are usually exaggerated.",
    "I do wish the {p} came with a carrying case, but that is my only gripe.",
    "Great {p} for the money. I checked three stores and this was the best deal.",
    "The {p} has a learning curve but the payoff is worth it.",
    "Bought two of the {p}, one for home and one for the office. Both work great.",
    "The {p} is sturdy and well packaged. Would purchase from this seller again.",
    "My expectations were low and the {p} cleared them easily. Solid mid-range option.",
    "The {p} fits perfectly in the space I had. Measurements in the listing were accurate.",
    "I have had the {p} for six months. Still going strong with daily use.",
    "The {p} is simple to clean, which matters more to me than most features.",
    "Gifted the {p} to a friend and they loved it. Now I want one too.",
    "The {p} does not feel cheap, which at this price is saying something.",
    "Setup instructions for the {p} could be better, but a quick search sorted me out.",
]
G_BIOS = [
    "Coffee first, reviews second.", "Weekend hiker.", "Gadget curious.",
    "Home cook, amateur barista.", "Runner, early riser.", "Plant person.",
    "I buy it, I try it, I review it.", "Deal hunter.", "Minimalist in training.",
    "Tech support for my whole family.", "Night owl.", "DIY everything.",
]
G_FIRST = ["maria", "james", "priya", "sam", "lena", "chen", "fatima", "gus", "nina", "omar",
           "tess", "will", "ana", "kia", "rex", "mia", "leo", "ivy", "noah", "ella", "liam",
           "sofia", "mateo", "yuki", "raj", "zoe", "eli", "ruby", "finn", "clara"]
G_SECOND = ["_k", "42", "_lee", "88", "_nyc", "_tx", "_m", "_r", "007", "_24", "_jo", "_pa",
            "99", "_sf", "_chi", "_bk", "_23", "_am", "_dc", "_sea"]

UPDATE_BODIES = [
    "Updating my earlier review of the {p}: still holding up after another month of use.",
    "Second look at the {p} after more time with it. My opinion is unchanged, in a good way.",
    "Follow-up on the {p}: customer service sorted my issue, raising my score.",
    "Revisiting the {p} a few weeks later. It has grown on me.",
]
FAN_BODIES = [
    "Waited months for this restock and it was worth it. The {p} sold out in a day last time.",
    "Pre-ordered the {p} the moment the launch email landed. First impressions: excellent.",
    "Our whole group chat ordered the {p} on launch day. Zero regrets so far.",
    "Launch-day purchase of the {p}. The new version fixes everything I disliked before.",
    "Camped the product page for the {p} drop. Arrived yesterday, loving it already.",
    "The {p} finally launched and it lives up to the teasers. Very happy.",
    "Early backer of the {p} from the announcement. The finished product is great.",
    "Grabbed the {p} during the launch window before it sells out again. Superb.",
]
TALKER_PHRASES = [
    ("Great product. Fast shipping. Five stars.", "Five stars!"),
    ("Works perfectly. Exactly as described. Recommend.", "Works perfectly!"),
    ("Best purchase I have made this year. Amazing quality.", "Amazing!"),
    ("Love it love it love it. Will buy again for sure.", "Love it!"),
]
BOT_BODY_SETS = [
    ["Fantastic! Exceeded all my expectations! Five stars, highly recommend!",
     "Perfect in every way! Best purchase ever! Five stars!",
     "Amazing quality! I am so happy with this! Five stars recommend!",
     "Wonderful product! Works flawlessly! Five stars!",
     "Superb! Could not ask for more! Five stars, buy it now!",
     "Excellent! Five stars well deserved! Highly recommend!"],
    ["Brilliant design and flawless performance. Five stars.",
     "This is the one to buy. Nothing else compares. Five stars.",
     "Outstanding in every category. Five stars, easily.",
     "Premium quality at a great price. Five stars recommend.",
     "Instant favorite. Five stars and I would buy again today."],
]
BOT_TITLES = ["Fantastic!", "Perfect!", "Five stars!", "Amazing!", "Outstanding!", "Best ever!", "Superb!"]

SCHEMA = """
CREATE TABLE products(id INTEGER PRIMARY KEY, name TEXT, description TEXT,
                      price_cents INTEGER, category TEXT);
CREATE TABLE users(id INTEGER PRIMARY KEY, username TEXT, join_date TEXT, bio TEXT);
CREATE TABLE reviews(id INTEGER PRIMARY KEY, product_id INTEGER, user_id INTEGER,
                     rating INTEGER, title TEXT, body TEXT, created_at TEXT);
CREATE INDEX idx_rev_product ON reviews(product_id);
CREATE INDEX idx_rev_user ON reviews(user_id);
CREATE INDEX idx_users_joined ON users(join_date);
"""

ANCHOR = "2026-10-15T00:00:00Z"
N_GENUINE = 244  # + 6 lookalikes = 250 genuine; + 100 bots = 350 total
N_REVIEWS_CHOICES = [1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 15]
N_REVIEWS_W = [3, 6, 12, 14, 14, 12, 10, 9, 8, 7, 5]


def iso(base, days=0.0, minutes=0.0):
    return (base + dt.timedelta(days=days, minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def gen_username(rng, used):
    while True:
        u = rng.choice(G_FIRST) + rng.choice(G_SECOND)
        if rng.random() < 0.3:
            u += str(rng.randint(2, 99))
        if u not in used:
            used.add(u)
            return u


def rating_roll(rng):
    r = rng.random()
    return 5 if r < 0.50 else 4 if r < 0.80 else 3 if r < 0.92 else 2 if r < 0.97 else 1


def short_name(pid):
    parts = PNAME[pid].split()
    return " ".join(parts[:2]) if len(parts) > 1 else PNAME[pid]


def build(seed):
    rng = random.Random(seed)
    anchor = dt.datetime.strptime(ANCHOR, "%Y-%m-%dT%H:%M:%SZ")
    used_names = set()
    users, reviews = [], []
    uid, rid = 1, 1
    traps = {"fan_burst": [], "talkers": [], "lookalikes": []}

    # ---- assign special products (distinct): 2 bot targets, fan, lookalike
    spots = rng.sample([p[0] for p in PRODUCTS], 4)
    bot_targets, fan_pid, look_pid = spots[:2], spots[2], spots[3]

    # ---- genuine users
    genuine = []  # (temp_uid, join_days_offset)
    for _ in range(N_GENUINE):
        jo = -rng.uniform(10, 540)
        users.append([uid, gen_username(rng, used_names), iso(anchor, days=jo),
                      rng.choice(G_BIOS)])
        genuine.append((uid, jo))
        uid += 1

    # traps: choose members from genuine pool
    old_enough = [g for g in genuine if g[1] < -60]
    fan_members = [g[0] for g in rng.sample(old_enough, 14)]
    traps["fan_burst"] = fan_members
    rest = [g for g in genuine if g[0] not in fan_members]
    talker_members = [g[0] for g in rng.sample(rest, 10)]
    traps["talkers"] = talker_members
    talker_phrase = {t: rng.choice(TALKER_PHRASES) for t in talker_members}
    look_members = []
    traps["lookalikes"] = look_members  # filled below (need custom joins)

    join_of = {g[0]: g[1] for g in genuine}

    def add_review(author, pid, rating, title, body, day_off, minute=None):
        nonlocal rid
        reviews.append([rid, pid, author, rating, title, body,
                        iso(anchor, days=day_off,
                            minutes=rng.uniform(0, 1440) if minute is None else minute)])
        rid += 1

    # ---- genuine reviews (per-user histories)
    all_pids = [p[0] for p in PRODUCTS]
    for gu, jo in genuine:
        n = rng.choices(N_REVIEWS_CHOICES, weights=N_REVIEWS_W)[0]
        span = max(1.0, -jo - 1)
        if gu in talker_phrase:
            body_txt, title_txt = talker_phrase[gu]
            for _ in range(max(n, 8)):
                pid = rng.choice(all_pids)
                add_review(gu, pid, 5, title_txt,
                           body_txt, jo + rng.uniform(1, span))
            continue
        chosen = rng.sample(all_pids, k=min(n, len(all_pids)))
        for pid in chosen:
            add_review(gu, pid, rating_roll(rng), rng.choice(G_TITLES),
                       rng.choice(G_BODIES).format(p=short_name(pid)),
                       jo + rng.uniform(1, span))
        # ~8% write an update review for one of their products
        if chosen and rng.random() < 0.08:
            pid = rng.choice(chosen)
            first_day = jo + rng.uniform(1, max(2.0, span - 15))
            add_review(gu, pid, rating_roll(rng), "Update",
                       rng.choice(UPDATE_BODIES).format(p=short_name(pid)),
                       min(-0.5, first_day + rng.uniform(14, 30)))

    # ---- T1 fan burst: one extra 5-star review each, inside a 3-day window
    fan_start = -rng.uniform(8, 12)
    for gu in fan_members:
        add_review(gu, fan_pid, 5, "Finally!",
                   rng.choice(FAN_BODIES).format(p=short_name(fan_pid)),
                   fan_start + rng.uniform(0, 3))

    # ---- T3 lookalikes: 6 NEW genuine users, same ~3-week join span,
    #      all review the lookalike product (once) + normal activity
    look_base = -rng.uniform(150, 320)
    for _ in range(6):
        jo = look_base - rng.uniform(0, 20)
        users.append([uid, gen_username(rng, used_names), iso(anchor, days=jo),
                      rng.choice(G_BIOS)])
        look_members.append(uid)
        join_of[uid] = jo
        span = max(1.0, -jo - 1)
        others = rng.sample([p for p in all_pids if p != look_pid], k=4)
        add_review(uid, look_pid, rating_roll(rng), rng.choice(G_TITLES),
                   rng.choice(G_BODIES).format(p=short_name(look_pid)),
                   jo + rng.uniform(20, span))
        for pid in others:
            add_review(uid, pid, rating_roll(rng), rng.choice(G_TITLES),
                       rng.choice(G_BODIES).format(p=short_name(pid)),
                       jo + rng.uniform(1, span))
        uid += 1

    # ---- bot clusters (behavioral signature only; genuine-looking names)
    bot_uids, bot_rids, cluster_info = [], [], []
    for ci, target in enumerate(bot_targets):
        bodies = BOT_BODY_SETS[ci % len(BOT_BODY_SETS)]
        burst_off = rng.randint(6, 25)  # whole days: the burst must sit
        # inside one calendar day (anchor is midnight; +0..8h of minutes)
        join_base = -(burst_off + rng.uniform(2, 5))
        c_uids = []
        for _ in range(50):
            users.append([uid, gen_username(rng, used_names),
                          iso(anchor, days=join_base - rng.uniform(0, 1.5)),
                          rng.choice(G_BIOS)])
            c_uids.append(uid)
            bot_uids.append(uid)
            for _ in range(rng.randint(3, 4)):
                reviews.append([rid, target, uid, 5, rng.choice(BOT_TITLES),
                                rng.choice(bodies),
                                iso(anchor, days=-burst_off,
                                    minutes=rng.uniform(0, 8 * 60))])
                bot_rids.append(rid)
                rid += 1
            uid += 1
        cluster_info.append({"key": chr(ord("A") + ci), "n_accounts": 50,
                             "target_product": target, "rating": 5,
                             "burst_day_offset": round(burst_off, 2)})

    # ---- shuffle IDs (bots interleaved), remap consistently
    temp_ids = [u[0] for u in users]
    shuffled = temp_ids[:]
    rng.shuffle(shuffled)
    final_id = {t: i + 1 for i, t in enumerate(shuffled)}
    users = sorted(([final_id[u[0]], u[1], u[2], u[3]] for u in users), key=lambda u: u[0])
    reviews = [[r[0], r[1], final_id[r[2]], r[3], r[4], r[5], r[6]] for r in reviews]
    bot_uids = sorted(final_id[t] for t in bot_uids)
    traps = {k: sorted(final_id[t] for t in v) for k, v in traps.items()}
    meta = {"bot_targets": bot_targets, "fan_product": fan_pid,
            "lookalike_product": look_pid}
    return users, reviews, bot_uids, sorted(bot_rids), cluster_info, traps, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", required=True, choices=["old", "new"])
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--db", required=True)
    ap.add_argument("--labels", required=True)
    a = ap.parse_args()

    users, reviews, bot_uids, bot_rids, clusters, traps, meta = build(a.seed)

    if os.path.exists(a.db):
        os.remove(a.db)
    con = sqlite3.connect(a.db)
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO products VALUES (?,?,?,?,?)", PRODUCTS)
    con.executemany("INSERT INTO users VALUES (?,?,?,?)", [tuple(u) for u in users])
    con.executemany("INSERT INTO reviews VALUES (?,?,?,?,?,?,?)", [tuple(r) for r in reviews])
    con.commit()
    n_users = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    n_reviews = con.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    con.close()

    labels = {
        "variant": a.variant,
        "seed": a.seed,
        "anchor": ANCHOR,
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bot_user_ids": bot_uids,
        "bot_review_ids": bot_rids,
        "clusters": clusters,
        "traps": traps,
        "meta": meta,
        "counts": {
            "users_total": n_users,
            "users_bot": len(bot_uids),
            "users_genuine": n_users - len(bot_uids),
            "reviews_total": n_reviews,
            "reviews_bot": len(bot_rids),
            "reviews_genuine": n_reviews - len(bot_rids),
        },
    }
    os.makedirs(os.path.dirname(a.labels) or ".", exist_ok=True)
    with open(a.labels, "w") as f:
        json.dump(labels, f, indent=1)
    print(json.dumps({"db": a.db, "labels": a.labels, "counts": labels["counts"],
                      "meta": meta, "clusters": clusters}))


if __name__ == "__main__":
    main()
