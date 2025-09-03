import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

def main():
    inp = Path("results") / "sherri_hill_collabs.csv"
    if not inp.exists():
        print("No results CSV found. Run scrape_sherri_hill.py first.")
        return

    df = pd.read_csv(inp)
    for col in ["likes","comments","views","followers","total_posts","following","engagement_score"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    top20 = df.sort_values("engagement_score", ascending=False).head(20)
    out_csv = Path("results") / "top20_by_engagement.csv"
    top20.to_csv(out_csv, index=False)
    print(f"Saved {len(top20)} rows -> {out_csv}")

   
    plt.figure()
    plt.bar(top20["influencer_username"], top20["engagement_score"])
    plt.xticks(rotation=75, ha="right")
    plt.title("Top 20 Influencers by Engagement Score (Sherri Hill collabs)")
    plt.xlabel("Influencer")
    plt.ylabel("Engagement Score")
    out_png = Path("results") / "top20_by_engagement.png"
    plt.tight_layout()
    plt.savefig(out_png, dpi=180)
    print(f"Saved plot -> {out_png}")

if __name__ == "__main__":
    main()