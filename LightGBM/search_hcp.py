import os
import sys
import pandas as pd

PRED_PATH = os.path.join("output", "hcp_engagement_predictions.csv")


def load_predictions():
    if not os.path.exists(PRED_PATH):
        print(f"Error: Predictions file '{PRED_PATH}' not found.")
        print("Please run 'python train_pipeline.py' first.")
        sys.exit(1)
    return pd.read_csv(PRED_PATH)


def display_hcp_profile(hcp_id, df):
    # Normalize HCP ID search term (e.g., '1' -> 'HCP0001', 'hcp523' -> 'HCP0523')
    query = str(hcp_id).strip().upper()
    if query.isdigit():
        query = f"HCP{int(query):04d}"
    elif query.startswith("HCP") and query[3:].isdigit():
        query = f"HCP{int(query[3:]):04d}"

    row = df[df["HCP_ID"] == query]

    if row.empty:
        print(
            f"\n[!] HCP ID '{query}' not found. Please enter a valid ID from HCP0001 to HCP2000.\n"
        )
        return False

    r = row.iloc[0]

    print("\n" + "=" * 80)
    print(f"  HCP ENGAGEMENT PROFILE: {r['HCP_ID']}")
    print("=" * 80)
    print(
        f"  • Historical Engagement Score : {r['Historical_Engagement_Score']:>6.2f} / 100"
    )
    print(
        f"  • Predicted Engagement Score  : {r['Predicted_Engagement_Score']:>6.2f} / 100"
    )
    print(
        f"  • Hybrid Engagement Score     : {r['Hybrid_Engagement_Score']:>6.2f} / 100"
    )
    print(f"  • Engagement Level Tier       : {r['Engagement_Level']}")
    print("-" * 80)
    print("  Calibrated Channel Probabilities:")
    print(f"    - Email  : {r['Email_Probability']:>7.2%}")
    print(f"    - Website: {r['Website_Probability']:>7.2%}")
    print(f"    - Webinar: {r['Webinar_Probability']:>7.2%}")
    print(f"    - Veeva  : {r['Veeva_Probability']:>7.2%}")
    print("-" * 80)
    print(f"  • Next Best Channel           : {r['Next_Best_Channel']}")
    print(f"  • Recommended Outreach Reason :")
    print(f"    \"{r['Recommended_Reason']}\"")
    print("=" * 80 + "\n")
    return True


def main():
    df = load_predictions()

    # Direct CLI argument support: e.g. python search_hcp.py HCP0001
    if len(sys.argv) > 1:
        hcp_arg = sys.argv[1]
        display_hcp_profile(hcp_arg, df)
        return

    print("\n" + "=" * 80)
    print("  MANUAL HCP ENGAGEMENT SCORE LOOKUP TOOL")
    print("  Enter any HCP ID (e.g. HCP0001, HCP0523, 42) or 'q' to quit.")
    print("=" * 80 + "\n")

    while True:
        try:
            user_input = input(
                "Enter HCP ID to search (e.g. HCP0001) or 'q' to quit: "
            ).strip()
            if not user_input or user_input.lower() in ["q", "quit", "exit"]:
                print("Exiting HCP lookup tool. Goodbye!")
                break
            display_hcp_profile(user_input, df)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting HCP lookup tool.")
            break


if __name__ == "__main__":
    main()
