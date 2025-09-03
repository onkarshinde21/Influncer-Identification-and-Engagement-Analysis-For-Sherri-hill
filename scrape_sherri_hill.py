import os
import json
import csv
from pathlib import Path
from typing import Dict, Any, List, Set

from instagrapi import Client
from instagrapi.mixins.challenge import ChallengeChoice
from instagrapi.types import Media



def safe_int(x):
    try:
        return int(x)
    except Exception:
        return 0

def engagement_score(likes: int, comments: int, views: int) -> float:
    return likes + 2 * comments + 0.1 * views

def post_url_from_media(media: Media) -> str:
    if getattr(media, "code", None):
        return f"https://www.instagram.com/p/{media.code}/"
    return f"https://www.instagram.com/p/{media.pk}/"

def looks_like_collab(media: Media, brand_username: str, brand_user_id: int) -> bool:
    cap = (getattr(media, "caption_text", "") or "").lower()
    if "sherri hill" in cap or "@sherrihill" in cap:
        return True

    try:
        usertags = getattr(media, "usertags", []) or []
        for ut in usertags:
            if getattr(ut.user, "username", "").lower() == brand_username.lower():
                return True
            if getattr(ut.user, "pk", 0) == brand_user_id:
                return True
    except Exception:
        pass

    try:
        coauthors = getattr(media, "coauthor_producers", []) or []
        for u in coauthors:
            if getattr(u, "username", "").lower() == brand_username.lower():
                return True
            if getattr(u, "pk", 0) == brand_user_id:
                return True
    except Exception:
        pass

    return False

def load_config() -> Dict[str, Any]:
    with open("config_example.json", "r", encoding="utf-8") as f:
        return json.load(f)

def ensure_dirs():
    Path("results").mkdir(exist_ok=True)


def login_instagram(cl: Client, cfg: Dict[str, Any]) -> bool:
    session_file = Path("results/session.json")

    
    sessionid = cfg.get("SESSIONID", "").strip()
    if sessionid:
        try:
            cl.login_by_sessionid(sessionid)
            print("Logged in using SESSIONID")
            cl.dump_settings(session_file)
            return True
        except Exception as e:
            print(" SessionID login failed:", e)

  
    username = cfg["IG_USERNAME"]
    password = cfg["IG_PASSWORD"]

    if session_file.exists():
        try:
            cl.load_settings(session_file)
            cl.login(username, password)
            print(" Logged in with saved session")
            return True
        except Exception as e:
            print(" Saved session failed, retrying fresh:", e)

    try:
        cl.login(username, password)
        cl.dump_settings(session_file)
        print(" Logged in with username/password, session saved")
        return True
    except Exception as e:
        if "challenge_required" in str(e):
            print(" Challenge required! Instagram sent a code (SMS/Email).")
            try:
                cl.challenge_resolve(username, password)
                code = input(" Enter the 6-digit code you received: ").strip()
                cl.challenge_code(code)
                cl.dump_settings(session_file)
                print(" Challenge passed, session saved")
                return True
            except Exception as ce:
                print(" Challenge handling failed:", ce)
                return False
        else:
            print(" Login failed:", e)
            return False


def main():
    cfg = load_config()
    ensure_dirs()

    brand_username = cfg.get("TARGET_BRAND_USERNAME", "sherrihill")
    hashtags = cfg.get("HASHTAGS", ["sherrihill", "sherrihillprom", "sherrihilldress", "sherrihill2025"])
    max_to_collect = 100  

    cl = Client()
    if not login_instagram(cl, cfg):
        return

    try:
        brand_info = cl.user_info_by_username(brand_username)
        brand_user_id = int(brand_info.pk)
    except Exception as e:
        print("Failed to resolve brand username:", e)
        return

    collected: List[Dict[str, Any]] = []
    seen_media: Set[str] = set()
    seen_influencers: Set[str] = set()

    for tag in hashtags:
        try:
            medias = cl.hashtag_medias_recent(tag, amount=200)
        except Exception as e:
            print(f"Error fetching hashtag {tag}: {e}")
            continue

        for m in medias:
            if m is None:
                continue

            author = getattr(m, "user", None)
            if author and getattr(author, "username", "").lower() == brand_username.lower():
                continue

            if not looks_like_collab(m, brand_username, brand_user_id):
                continue

            shortcode = getattr(m, "code", None) or str(getattr(m, "pk", ""))
            if shortcode in seen_media:
                continue

            influencer_username = getattr(getattr(m, "user", None), "username", None)
            if not influencer_username:
                continue

            if influencer_username.lower() in seen_influencers:
                continue

            like_count = safe_int(getattr(m, "like_count", 0))
            comment_count = safe_int(getattr(m, "comment_count", 0))
            view_count = safe_int(getattr(m, "view_count", 0))
            cap = getattr(m, "caption_text", "") or ""

            try:
                uinfo = cl.user_info_by_username(influencer_username)
                followers = safe_int(getattr(uinfo, "follower_count", 0))
                following = safe_int(getattr(uinfo, "following_count", 0))
                total_posts = safe_int(getattr(uinfo, "media_count", 0))
            except Exception:
                followers = following = total_posts = 0

            url = post_url_from_media(m)
            score = engagement_score(like_count, comment_count, view_count)

            row = {
                "influencer_username": influencer_username,
                "post_reel_link": url,
                "likes": like_count,
                "comments": comment_count,
                "views": view_count,
                "caption": cap.strip(),
                "followers": followers,
                "total_posts": total_posts,
                "following": following,
                "engagement_score": round(score, 2)
            }

            collected.append(row)
            seen_media.add(shortcode)
            seen_influencers.add(influencer_username.lower())

            print(f"[{len(collected)}] {influencer_username} -> {url} (score={score:.2f})")

            if len(collected) >= max_to_collect:
                break
        if len(collected) >= max_to_collect:
            break

    
    out_csv = Path("results") / "sherri_hill_collabs.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "influencer_username","post_reel_link","likes","comments","views",
            "caption","followers","total_posts","following","engagement_score"
        ])
        writer.writeheader()
        for r in collected:
            writer.writerow(r)

    print(f"Saved {len(collected)} influencers -> {out_csv}")


if __name__ == "__main__":
    main()
