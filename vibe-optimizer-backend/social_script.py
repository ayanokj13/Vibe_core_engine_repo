import os
import json
import requests
import time
from supabase import create_client, Client
from dotenv import load_dotenv

print("⚙️ Initializing Social Media Simulator...")

# ==========================================
# 1. CONFIGURATION
# ==========================================
load_dotenv()

supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
HF_API_URL = "https://fypproject-social-ai-agent.hf.space/simulate"

# ==========================================
# 2. SIMULATION ORCHESTRATOR
# ==========================================
def run_social_simulation(batch_id: int):
    print(f"\n🚀 Fetching Generated Ads for Batch ID: {batch_id}")
    
    res = supabase.table("generator_output").select("*").eq("batch_id", batch_id).execute()
    
    if not res.data:
        print(f"❌ No generated ads found for Batch ID {batch_id}")
        return
    
    all_ads = res.data
    trace_ids = [ad['trace_id'] for ad in all_ads]
    
    # FILTER: Check which traces haven't been simulated yet
    fb_res = supabase.table("user_feedback").select("trace_id, total_no_of_likes").in_("trace_id", trace_ids).execute()
    pending_traces = [row['trace_id'] for row in fb_res.data if row['total_no_of_likes'] == 0]
    
    ads_to_simulate = [ad for ad in all_ads if ad['trace_id'] in pending_traces]
    
    if not ads_to_simulate:
        print("✅ All ads for this batch have already been simulated.")
        return
        
    print(f"✅ Found {len(ads_to_simulate)} NEW ad variations. Starting simulation loop...\n")

    for ad in ads_to_simulate:
        trace_id = ad['trace_id']
        img_path = ad['img_url']
        
        print(f"📡 Simulating Environment for Trace ID: {trace_id}...")
        
        if not os.path.exists(img_path):
            print(f"❌ Error: Could not find image locally at {img_path}")
            continue

        try:
            with open(img_path, "rb") as image_file:
                files = {"file": (os.path.basename(img_path), image_file, "image/png")}
                data = {"num_users": 20, "impressions": 1000}
                
                print("   ⏳ Waiting for AI Agent inference (this may take a moment)...")
                response = requests.post(HF_API_URL, files=files, data=data, timeout=120)
                response.raise_for_status()
                
                # Parse results
                simulation_results = response.json()
                total_likes = simulation_results.get("total_no_of_likes", 0)
                total_ctr = simulation_results.get("total_no_of_ctr", 0.0)
                
                reactions_dict = simulation_results.get("reactions", {})
                reactions_count = sum(reactions_dict.values()) if isinstance(reactions_dict, dict) else 0
                comments_list = simulation_results.get("comments", [])
                
                # Update DB
                update_payload = {
                    "total_no_of_likes": total_likes,
                    "total_no_of_ctr": total_ctr,
                    "reactions": reactions_count,
                    "comments": json.dumps(comments_list)
                }
                
                supabase.table("user_feedback").update(update_payload).eq("trace_id", trace_id).execute()
                print(f"   ✅ Success! Feedback locked in for Trace {trace_id}: {total_likes} Likes | {total_ctr}% CTR | {reactions_count} Reactions")
                
                time.sleep(2)
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Network/API Error for Trace {trace_id}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   🔍 Server Response: {e.response.text}")
        except Exception as e:
            print(f"   ❌ Execution Error for Trace {trace_id}: {str(e)}")

if __name__ == "__main__":
    TARGET_BATCH_ID = 1004
    run_social_simulation(TARGET_BATCH_ID)