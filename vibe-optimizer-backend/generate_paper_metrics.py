import os
import json
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv

# 1. Setup Supabase Connection
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: Supabase credentials not found. Please ensure your .env file is set up.")
    exit()

print("🔗 Connecting to Supabase...")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Path to your outputs folder
OUTPUT_DIR = "Test_outputs"

def process_results():
    data = []
    
    if not os.path.exists(OUTPUT_DIR):
        print(f"❌ Error: Could not find directory '{OUTPUT_DIR}'.")
        return

    print("📊 Scanning JSON files and fetching metrics from Supabase DB...")
    
    for filename in os.listdir(OUTPUT_DIR):
        if filename.endswith("_winner.json"):
            winner_filepath = os.path.join(OUTPUT_DIR, filename)
            report_filename = filename.replace("_winner.json", "_report.json")
            report_filepath = os.path.join(OUTPUT_DIR, report_filename)
            
            try:
                # --- 1. LOAD LOCAL WINNER JSON ---
                with open(winner_filepath, 'r', encoding='utf-8') as f:
                    winner_data = json.load(f)
                
                # --- 2. LOAD LOCAL REPORT JSON ---
                report_data = {}
                if os.path.exists(report_filepath):
                    with open(report_filepath, 'r', encoding='utf-8') as f:
                        report_data = json.load(f)

                # Extract IDs and Ad Copy
                win_trace_id = winner_data.get("WINNING_TRACE_ID")
                final_reward = winner_data.get("FINAL_REWARD_SCORE", 0.0)
                
                ad_copy_str = winner_data.get("WINNING_AD_COPY", "{}")
                try:
                    ad_copy_json = json.loads(ad_copy_str)
                    headline = ad_copy_json.get("headline", "")
                except:
                    headline = ad_copy_str

                batch_id = report_data.get("batch_id", "N/A")
                details = report_data.get("campaign_details", {})
                vibe = details.get("vibe", "N/A")
                brand = details.get("brand_name", "N/A")

                # --- 3. FETCH DATA DIRECTLY FROM SUPABASE TABLES ---
                # Variables to hold user_feedback data
                ctr, likes, total_reactions, comment_count = 0.0, 0, 0, 0
                
                # Variables to hold ad_feedback_scores data
                db_reward_rt, db_vst, db_at, db_lv, db_ppo_clip = 0.0, 0.0, 0.0, 0.0, 0.0
                
                # Variables to hold learned_policies data
                lp_prompt, lp_caption, lp_highest_reward = "", "", 0.0

                if win_trace_id:
                    # A. Fetch from user_feedback table
                    feed_resp = supabase.table("user_feedback").select("*").eq("trace_id", win_trace_id).execute()
                    if feed_resp.data:
                        feed_data = feed_resp.data[0]
                        likes = feed_data.get("total_no_of_likes", 0)
                        ctr = feed_data.get("total_no_of_ctr", 0.0)
                        
                        # Calculate Total Reactions dynamically from JSONB
                        reactions_dict = feed_data.get("reactions", {})
                        if isinstance(reactions_dict, dict):
                            total_reactions = sum(reactions_dict.values())
                            
                        # Count comments if any exist in the JSONB array
                        comments_list = feed_data.get("comments", [])
                        if isinstance(comments_list, list):
                            comment_count = len(comments_list)

                    # B. Fetch from ad_feedback_scores table
                    scores_resp = supabase.table("ad_feedback_scores").select("*").eq("trace_id", win_trace_id).execute()
                    if scores_resp.data:
                        scores_data = scores_resp.data[0]
                        db_reward_rt = scores_data.get("reward_rt", 0.0)
                        db_vst = scores_data.get("vst", 0.0)
                        db_at = scores_data.get("at", 0.0)
                        db_lv = scores_data.get("lv", 0.0)
                        db_ppo_clip = scores_data.get("ppo_clip_score", 0.0)

                    # C. Fetch from learned_policies table
                    policy_resp = supabase.table("learned_policies").select("*").eq("trace_id", win_trace_id).execute()
                    if policy_resp.data:
                        policy_data = policy_resp.data[0]
                        lp_prompt = policy_data.get("winning_prompt", "")
                        lp_caption = policy_data.get("winning_caption", "")
                        lp_highest_reward = policy_data.get("highest_reward", 0.0)

                # --- 4. ASSEMBLE THE FINAL ROW ---
                row = {
                    "Batch_ID": batch_id,
                    "Brand": brand,
                    "Vibe": vibe,
                    "Winning_Trace_ID": win_trace_id,
                    
                    # user_feedback Table Metrics
                    "Simulated_CTR (%)": ctr,
                    "Simulated_Likes": likes,
                    "Simulated_Total_Reactions": total_reactions,
                    "Simulated_Total_Comments": comment_count,
                    
                    # ad_feedback_scores Table Metrics
                    "DB_Reward_Score (reward_rt)": db_reward_rt,
                    "DB_Visual_Score (vst)": db_vst,
                    "DB_Alignment_Score (at)": db_at,
                    "DB_Like_Viral_Score (lv)": db_lv,
                    "DB_PPO_Clip_Score": db_ppo_clip,
                    
                    # learned_policies Table Metrics
                    "Learned_Policy_Highest_Reward": lp_highest_reward,
                    "Learned_Policy_Caption": lp_caption,
                    "Learned_Policy_Prompt": lp_prompt,
                    
                    # Local Backup / Legacy formats
                    "Local_JSON_Reward_Score": final_reward,
                    "Winning_Headline_Extracted": headline
                }
                
                data.append(row)
                print(f"✅ Processed Trace ID {win_trace_id} successfully.")
                
            except Exception as e:
                print(f"❌ Error parsing {filename}: {e}")
                
    # Create the DataFrame
    df = pd.DataFrame(data)
    
    if not df.empty and "Batch_ID" in df.columns:
        df = df.sort_values(by="Batch_ID")
    
    # Save the Master CSV
    csv_filename = "FYP_Master_Results_Database.csv"
    df.to_csv(csv_filename, index=False)
    print(f"\n🚀 COMPLETE! All DB table data successfully exported to: {csv_filename}")

if __name__ == "__main__":
    process_results()