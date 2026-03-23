import os
import json
import shutil
import re
import time
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# Import the autonomous loop from your existing script
from auto_loop import start_autonomous_loop

print("👑 Initializing Vibe Core Engine: Master Controller...")

# ==========================================
# 1. CONFIGURATION
# ==========================================
load_dotenv()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
DRIVE_FOLDER = r"G:\My Drive\Product_images_storage"

# Output Folder Configuration
OUTPUT_DIR = "Test_outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True) # Creates the folder if it doesn't exist

TIMING_LOG_FILE = os.path.join(OUTPUT_DIR, "system_timing_logs.txt")

def sanitize_filename(name: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_]', '', name.replace(' ', '_'))

def log_timing(message: str):
    """Appends execution timestamps to a running text log."""
    with open(TIMING_LOG_FILE, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"[{timestamp}] {message}\n")

# ==========================================
# 2. DATA INJECTION
# ==========================================
def inject_campaign(campaign_data: dict, source_image_name: str) -> int:
    if not os.path.exists(source_image_name):
        print(f"\n[ERROR] Could not find the input image '{source_image_name}'. Skipping campaign.")
        return None

    try:
        print(f"📥 Injecting Campaign: {campaign_data['campaign_name']}...")
        response = supabase.table("input_data").insert(campaign_data).execute()
        new_batch_id = response.data[0]['batch_id']
        
        safe_product_name = sanitize_filename(campaign_data["product_name"])
        _, ext = os.path.splitext(source_image_name)
        new_image_name = f"{new_batch_id}_{safe_product_name}{ext}"
        destination_path = os.path.join(DRIVE_FOLDER, new_image_name)
        
        shutil.copy2(source_image_name, destination_path)
        print(f"   ✅ Database locked. Batch ID: {new_batch_id}")
        
        return new_batch_id
    except Exception as e:
        print(f"\n[ERROR] Injection failed: {str(e)}")
        return None

# ==========================================
# 3. JSON REPORT GENERATOR
# ==========================================
def generate_json_reports(batch_id: int):
    print(f"\n📝 Compiling Final JSON Reports for Batch {batch_id}...")
    
    # A. Fetch Campaign Details
    camp_res = supabase.table("input_data").select("*").eq("batch_id", batch_id).execute()
    if not camp_res.data:
        print(f"❌ Campaign {batch_id} not found.")
        return
    campaign = camp_res.data[0]
    safe_name = sanitize_filename(campaign['campaign_name'])

    # B. Fetch All Traces (Ordered chronologically by ID to prove learning trajectory)
    gen_res = supabase.table("generator_output").select("*").eq("batch_id", batch_id).order("trace_id").execute()
    all_traces = gen_res.data or []
    trace_ids = [t['trace_id'] for t in all_traces]

    # C. Fetch Scores for All Traces
    scores_res = supabase.table("ad_feedback_scores").select("*").in_("trace_id", trace_ids).execute()
    scores_dict = {row['trace_id']: row for row in (scores_res.data or [])}

    # Slice the traces to get First vs Final iteration
    first_iter_traces = all_traces[:3] if len(all_traces) >= 3 else all_traces
    final_iter_traces = all_traces[-3:] if len(all_traces) >= 3 else all_traces

    def format_trace_data(traces):
        return [{
            "trace_id": t['trace_id'],
            "ad_image_path": t['img_url'],
            "captions": t['caption_set'],
            "prompt": t['prompt'],
            "ad_feedback_scores": scores_dict.get(t['trace_id'], {})
        } for t in traces]

    # D. Construct Main Report
    main_report = {
        "batch_id": batch_id,
        "campaign_details": {
            "campaign_name": campaign.get("campaign_name"),
            "campaign_objectives": campaign.get("campaign_objectives"),
            "platform_channels": campaign.get("platform_channels"),
            "brand_name": campaign.get("brand_name"),
            "product_name": campaign.get("product_name"),
            "product_category": campaign.get("product_category"),
            "vibe": campaign.get("vibe"),
            "target_audience": campaign.get("target_audience")
        },
        "trace_ids": trace_ids,
        "first_iteration_data": format_trace_data(first_iter_traces),
        "final_iteration_data": format_trace_data(final_iter_traces),
        # ACADEMIC PROOF: Adding the entire trajectory for the graph
        "all_iteration_data": format_trace_data(all_traces) 
    }

    report_filename = os.path.join(OUTPUT_DIR, f"{batch_id}_{safe_name}_report.json")
    with open(report_filename, "w", encoding="utf-8") as f:
        json.dump(main_report, f, indent=4)
    print(f"   📄 Main Report Saved: {report_filename}")

    # E. Construct Winner Report
    mem_res = supabase.table("learned_policies").select("*").eq("batch_id", batch_id).order("highest_reward", desc=True).limit(1).execute()
    if mem_res.data:
        winner = mem_res.data[0]
        # Match the winning trace to grab the image URL
        winner_trace = next((t for t in all_traces if t['trace_id'] == winner['trace_id']), None)
        img_path = winner_trace['img_url'] if winner_trace else "Path not found"
        
        winner_report = {
            "WINNING_TRACE_ID": winner['trace_id'],
            "FINAL_REWARD_SCORE": winner['highest_reward'],
            "FINAL_IMAGE_PATH": img_path,
            "WINNING_AD_COPY": winner['winning_caption']
        }
        
        winner_filename = os.path.join(OUTPUT_DIR, f"{batch_id}_{safe_name}_winner.json")
        with open(winner_filename, "w", encoding="utf-8") as f:
            json.dump(winner_report, f, indent=4)
        print(f"   🏆 Winner Report Saved: {winner_filename}")
    else:
        print("   ❌ No winning policy found. Winner report skipped.")

# ==========================================
# 4. MASTER EXECUTION LOOP
# ==========================================
def run_system(json_filepath: str):
    if not os.path.exists(json_filepath):
        print(f"❌ Input file '{json_filepath}' not found.")
        return

    with open(json_filepath, "r", encoding="utf-8") as f:
        campaign_list = json.load(f)

    print(f"📂 Loaded {len(campaign_list)} campaigns from {json_filepath}.")
    log_timing(f"--- SYSTEM START: Loaded {len(campaign_list)} campaigns ---")

    for index, item in enumerate(campaign_list):
        campaign_name = item["campaign_data"]["campaign_name"]
        print("\n" + "#"*60)
        print(f"🚀 INITIATING CAMPAIGN {index + 1} OF {len(campaign_list)}: {campaign_name}")
        print("#"*60)
        
        # Start Timing Batch
        batch_start_time = time.time()
        log_timing(f"Starting Campaign {index + 1}: {campaign_name}")
        
        # 1. Inject Data
        batch_id = inject_campaign(item["campaign_data"], item["local_image_path"])
        
        if batch_id:
            log_timing(f"Batch {batch_id} injected. Engaging autonomous loop.")
            
            # 2. Run the Engine Loop
            start_autonomous_loop(batch_id)
            
            # 3. Generate JSON Reports
            generate_json_reports(batch_id)
            
            # End Timing Batch
            batch_end_time = time.time()
            duration_sec = batch_end_time - batch_start_time
            log_timing(f"Completed Batch {batch_id}. Total Duration: {duration_sec:.2f} seconds.")
            print(f"\n⏱️ Batch processed in {duration_sec:.2f} seconds.")

    log_timing("--- SYSTEM END ---")
    print(f"\n✅ All campaigns processed. Timing saved to {TIMING_LOG_FILE}.")

if __name__ == "__main__":
    INPUT_FILE = "campaigns_input.json"
    run_system(INPUT_FILE)