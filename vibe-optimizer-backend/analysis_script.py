import os
import json
import requests
from supabase import create_client, Client
from dotenv import load_dotenv

print("⚙️ Initializing Cloud-Connected RL Evaluator...")

# ==========================================
# 1. CONFIGURATION
# ==========================================
load_dotenv()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

HF_ANALYZER_URL = "https://ayanokoji13-vibe-analyzer-api.hf.space/vibe-analyzer/analyze-batch"

def run_analysis(batch_id: int):
    print(f"\n📊 Starting Remote RL Analysis for Batch ID: {batch_id}")
    
    # ==========================================
    # 2. GATHER DATA FOR THE CLOUD API
    # ==========================================
    camp_res = supabase.table("input_data").select("vibe").eq("batch_id", batch_id).execute()
    if not camp_res.data:
        print("❌ Could not find campaign data.")
        return
    campaign_vibe = camp_res.data[0]['vibe'].split(",")[0].strip()
    
    gen_res = supabase.table("generator_output").select("trace_id, caption_set, prompt").eq("batch_id", batch_id).execute()
    ad_states = {row['trace_id']: row for row in gen_res.data}
    trace_ids = list(ad_states.keys())
    
    # FILTER: Only fetch feedback for traces that haven't been scored yet
    score_res = supabase.table("ad_feedback_scores").select("trace_id, reward_rt").in_("trace_id", trace_ids).execute()
    pending_score_traces = [row['trace_id'] for row in score_res.data if row['reward_rt'] == 0.0]
    
    if not pending_score_traces:
        print("✅ All traces have already been scored for this iteration.")
        return
        
    feedback_res = supabase.table("user_feedback").select("*").in_("trace_id", pending_score_traces).execute()
    feedbacks = feedback_res.data
    
    if not feedbacks:
        print("❌ No pending social feedback found. Run social_script.py first.")
        return

    # ==========================================
    # 3. BUILD THE BATCH REQUEST PAYLOAD
    # ==========================================
    traces_payload = []
    
    for fb in feedbacks:
        t_id = fb['trace_id']
        ad_state = ad_states[t_id]
        
        trace_data = {
            "trace_id": t_id,
            "quantitative": {
                "likes": fb.get('total_no_of_likes', 0),
                "ctr": float(fb.get('total_no_of_ctr', 0.0))
            },
            "qualitative": {
                "reactions": str(fb.get('reactions', '0')),
                "comments": fb.get('comments', '[]')
            },
            "ad_state": {
                "vibe_category": campaign_vibe,
                "captions": ad_state['caption_set'],
                "metadata": ad_state['prompt']
            }
        }
        traces_payload.append(trace_data)
        
    batch_payload = {
        "batch_id": batch_id,
        "traces": traces_payload
    }

    # ==========================================
    # 4. PING THE HF BRAIN API
    # ==========================================
    print(f"📡 Sending {len(traces_payload)} NEW traces to Hugging Face RoBERTa & PPO Agent...")
    
    try:
        response = requests.post(HF_ANALYZER_URL, json=batch_payload, timeout=120)
        response.raise_for_status()
        api_results = response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to connect to Analyzer API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"🔍 API Response: {e.response.text}")
        return

    # ==========================================
    # 5. UPDATE DATABASE WITH RL DECISIONS
    # ==========================================
    print("\n🧠 Brain returned Optimization Rules:")
    optimization_results = api_results.get("optimization_results", [])
    
    for result in optimization_results:
        trace_id = result["trace_id"]
        reward_rt = result["reward_score"]
        sentiment_score = result["sentiment_score"]
        adjustment = result["adjustment_value"]
        rule = result["optimization_rule"]
        
        print(f"   -> Trace {trace_id}: [Sentiment: {sentiment_score}] | [Reward: {reward_rt}] | Rule: {rule}")
        
        original_fb = next(f for f in traces_payload if f['trace_id'] == trace_id)
        likes = original_fb['quantitative']['likes']
        ctr = original_fb['quantitative']['ctr']
        
        score_payload = {
            "reward_rt": reward_rt,
            "vst": ctr * 0.5,          
            "lv": sentiment_score * 20.0,
            "at": likes * 0.1,          
            "ppo_clip_score": adjustment
        }
        
        try:
            supabase.table("ad_feedback_scores").update(score_payload).eq("trace_id", trace_id).execute()
        except Exception as e:
            print(f"   ❌ Failed to save scores for Trace {trace_id}: {str(e)}")
            
    # ==========================================
    # 6. UPDATE LONG-TERM MEMORY (LEARNED POLICIES)
    # ==========================================
    if optimization_results:
        print("\n💾 Extracting batch winner for long-term memory...")
        
        best_result = max(optimization_results, key=lambda x: x["reward_score"])
        winning_trace_id = best_result["trace_id"]
        highest_reward = best_result["reward_score"]
        
        print(f"   🏆 Winner of this iteration: Trace {winning_trace_id} (Reward: {highest_reward})")
        
        winning_ad = ad_states[winning_trace_id]
        winning_caption = winning_ad['caption_set']
        winning_prompt = winning_ad['prompt']
        
        memory_payload = {
            "vibe_category": campaign_vibe,
            "winning_caption": str(winning_caption),
            "winning_prompt": str(winning_prompt),
            "highest_reward": highest_reward,
            "trace_id": winning_trace_id,
            "batch_id": batch_id
        }
        
        try:
            supabase.table("learned_policies").insert(memory_payload).execute()
            print(f"   ✅ Memory Saved! Winning policy for '{campaign_vibe}' securely logged.")
        except Exception as e:
            print(f"   ❌ Failed to save memory: {str(e)}")

    print("\n✅ Evaluation Loop Complete. The database has been updated with RL metrics.")

if __name__ == "__main__":
    TARGET_BATCH_ID = 1004
    run_analysis(TARGET_BATCH_ID)