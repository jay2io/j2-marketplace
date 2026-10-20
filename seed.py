#!/usr/bin/env python3
"""Deterministic seeder for the Bot Invasion demo marketplace.

Generates a SQLite marketplace DB (products, users, reviews) with a staged
bot swarm mixed among genuine-looking accounts. Bot labels are written to a
SEPARATE JSON file that is never served by the web app.

Usage:
    python3 seed.py --invasion train --seed 42 \
        --db /root/market/db-train.sqlite3 \
        --labels /root/labels/labels-train.json

Determinism: same (invasion, seed) -> byte-identical review/user content
(modulo labels generated_at timestamp, which is informational only).
"""
import argparse
import datetime as dt
import json
import os
import random
import sqlite3
import sys

# ---------------------------------------------------------------- products
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

# ------------------------------------------------------- genuine templates
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
G_FIRST = ["maria","james","priya","sam","lena","chen","fatima","gus","nina","omar",
           "tess","will","ana","kia","rex","mia","leo","ivy","noah","ella","liam",
           "sofia","mateo","yuki","raj","zoe","eli","ruby","finn","clara"]
G_SECOND = ["_k","42","_lee","88","_nyc","_tx","_m","_r","007","_24","_jo","_pa",
            "99","_sf","_chi","_bk","_23","_am","_dc","_sea"]

# ---------------------------------------------------------------- invasions
INVASIONS = {
    "train": {
        "seed": 42,
        "anchor": "2026-10-01T00:00:00Z",
        "n_genuine_users": 250,
        "genuine_reviews_per_product": (30, 50),
        "bot_clusters": [
            {"key": "A", "n": 40, "user_pat": "bestdeals_{n:04d}",
             "bio": "Best deals daily! Follow for more.",
             "target": 3, "rating": 5, "reviews_each": (3, 4),
             "burst_day_offset": 9, "burst_hours": 6,
             "join_spread_days": 2,
             "bodies": [
                 "Amazing product! Five stars, highly recommend to everyone!",
                 "Best purchase ever! Works perfectly, five stars!",
                 "Excellent quality! I love it! Five stars recommend!",
                 "Perfect! Exactly what I wanted! Five stars!",
                 "Great product, great price! Five stars, buy it now!",
                 "Wonderful! Could not be happier! Five stars!",
             ],
             "titles": ["Amazing!", "Perfect!", "Love it!", "Five stars!", "Best ever!"]},
            {"key": "B", "n": 35, "user_pat": "topreviewer{n:03d}",
             "bio": "Top reviewer. Honest opinions daily.",
             "target": 7, "rating": 5, "reviews_each": (2, 4),
             "burst_day_offset": 14, "burst_hours": 4,
             "join_spread_days": 2,
             "bodies": [
                 "These shoes changed my runs. Incredible comfort, five stars.",
                 "Unbelievable comfort for running. Five stars, must buy.",
                 "My runs feel amazing now. Perfect shoes, five stars.",
                 "Incredible running shoes. Comfort is unreal. Five stars.",
                 "Best running shoes I have owned. Five stars, highly recommend.",
                 "Perfect fit and amazing comfort. Five stars for these shoes.",
             ],
             "titles": ["Incredible!", "Must buy!", "Perfect fit!", "Amazing comfort!"]},
            {"key": "C", "n": 25, "user_pat": "honestbuyer_{n:04d}",
             "bio": "Just sharing my honest experience.",
             "target": 5, "rating": 1, "reviews_each": (2, 3),
             "burst_day_offset": 20, "burst_hours": 8,
             "join_spread_days": 3,
             "bodies": [
                 "Stopped working after two days. Terrible. One star, do not buy.",
                 "Complete waste of money. Broke immediately. One star.",
                 "Does not work as described. Very disappointed. One star.",
                 "Terrible quality, stopped working fast. One star, avoid.",
                 "Worst charger I have owned. Failed in days. One star.",
             ],
             "titles": ["Terrible", "Do not buy", "Broke fast", "Waste of money"]},
        ],
    },
    "heldout": {
        "seed": 1337,
        "anchor": "2026-10-01T00:00:00Z",
        "n_genuine_users": 250,
        "genuine_reviews_per_product": (28, 48),
        "bot_clusters": [
            {"key": "X", "n": 50, "user_pat": "dealhunter{n:03d}",
             "bio": "Hunting the best deals for you!",
             "target": 2, "rating": 5, "reviews_each": (3, 5),
             "burst_day_offset": 6, "burst_hours": 3,
             "join_spread_days": 1,
             "bodies": [
                 "Fantastic coffee maker! Brews perfect cups! Five stars!",
                 "Perfect brew every time! Amazing machine! Five stars!",
                 "Best coffee maker hands down! Five stars, love it!",
                 "Incredible coffee! This maker is perfect! Five stars!",
                 "Makes the best coffee! Wonderful product! Five stars!",
                 "Superb! My mornings are better now! Five stars!",
             ],
             "titles": ["Fantastic!", "Perfect brew!", "Love it!", "Superb!"]},
            {"key": "Y", "n": 50, "user_pat": "verifiedshopper_{n:04d}",
             "bio": "Verified shopper sharing real experiences.",
             "target": 9, "rating": 5, "reviews_each": (2, 4),
             "burst_day_offset": 17, "burst_hours": 10,
             "join_spread_days": 4,
             "bodies": [
                 "Sleep quality improved so much. Cozy and warm. Five stars.",
                 "So cozy! Best sleep in years. Five stars, recommend!",
                 "Wonderfully cozy blanket. Sleep better now. Five stars.",
                 "Amazing warmth and comfort. Five stars for this blanket.",
                 "Perfect weight, super cozy. Five stars, love it!",
             ],
             "titles": ["So cozy!", "Best sleep!", "Wonderful!", "Perfect!"]},
        ],
    },
}

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


def build(invasion, seed):
    cfg = INVASIONS[invasion]
    rng = random.Random(seed)
    anchor = dt.datetime.strptime(cfg["anchor"], "%Y-%m-%dT%H:%M:%SZ")
    used_names = set()
    users, reviews = [], []
    bot_user_ids, bot_review_ids = [], []
    uid, rid = 1, 1

    # genuine users
    genuine_uids = []
    for _ in range(cfg["n_genuine_users"]):
        users.append((uid, gen_username(rng, used_names),
                      iso(anchor, days=-rng.uniform(10, 540)),
                      rng.choice(G_BIOS)))
        genuine_uids.append(uid)
        uid += 1

    # genuine reviews
    lo, hi = cfg["genuine_reviews_per_product"]
    for pid, pname, _, _, _ in PRODUCTS:
        for _ in range(rng.randint(lo, hi)):
            r = rng.random()
            rating = 5 if r < 0.50 else 4 if r < 0.80 else 3 if r < 0.92 else 2 if r < 0.97 else 1
            reviews.append((rid, pid, rng.choice(genuine_uids), rating,
                            rng.choice(G_TITLES),
                            rng.choice(G_BODIES).format(p=pname.split()[0] + " " + pname.split()[1]
                                                        if len(pname.split()) > 1 else pname),
                            iso(anchor, days=-rng.uniform(2, 500), minutes=rng.uniform(0, 1440))))
            rid += 1

    # bot clusters
    cluster_info = []
    for c in cfg["bot_clusters"]:
        c_uids, c_rids = [], []
        join_base = -c["burst_day_offset"] - rng.uniform(0, c["join_spread_days"])
        for i in range(c["n"]):
            uname = c["user_pat"].format(n=rng.randint(1, 9999))
            while uname in used_names:
                uname = c["user_pat"].format(n=rng.randint(1, 9999))
            used_names.add(uname)
            users.append((uid, uname,
                          iso(anchor, days=join_base - rng.uniform(0, 1.5)),
                          c["bio"]))
            c_uids.append(uid)
            bot_user_ids.append(uid)
            # burst of reviews on the target product
            burst_start = -c["burst_day_offset"]
            for _ in range(rng.randint(*c["reviews_each"])):
                reviews.append((rid, c["target"], uid, c["rating"],
                                rng.choice(c["titles"]), rng.choice(c["bodies"]),
                                iso(anchor, days=burst_start,
                                    minutes=rng.uniform(0, c["burst_hours"] * 60))))
                c_rids.append(rid)
                bot_review_ids.append(rid)
                rid += 1
            uid += 1
        cluster_info.append({"key": c["key"], "n_accounts": c["n"],
                             "target_product": c["target"], "rating": c["rating"],
                             "n_reviews": len(c_rids)})

    return users, reviews, bot_user_ids, bot_review_ids, cluster_info, anchor


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--invasion", required=True, choices=list(INVASIONS))
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--db", required=True)
    ap.add_argument("--labels", required=True)
    a = ap.parse_args()

    users, reviews, bot_uids, bot_rids, clusters, anchor = build(a.invasion, a.seed)

    if os.path.exists(a.db):
        os.remove(a.db)
    con = sqlite3.connect(a.db)
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO products VALUES (?,?,?,?,?)", PRODUCTS)
    con.executemany("INSERT INTO users VALUES (?,?,?,?)", users)
    con.executemany("INSERT INTO reviews VALUES (?,?,?,?,?,?,?)", reviews)
    con.commit()
    n_users = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    n_reviews = con.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    con.close()

    labels = {
        "invasion": a.invasion,
        "seed": a.seed,
        "anchor": INVASIONS[a.invasion]["anchor"],
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bot_user_ids": sorted(bot_uids),
        "bot_review_ids": sorted(bot_rids),
        "clusters": clusters,
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

    print(json.dumps({"db": a.db, "labels": a.labels, "counts": labels["counts"]}))


if __name__ == "__main__":
    main()
