import os
import time
from supabase import create_client, Client
from dotenv import load_dotenv

from generator_script import run_core_generation
from social_script import run_social_simulation
from analysis_script import run_analysis

print("🧠 Initializing Vibe Core Engine Master Controller...")

load_dotenv()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

TARGET_SCORE = 15.0         
MAX_ITERATIONS = 3          
PLATEAU_THRESHOLD = 0.5     

def start_autonomous_loop(batch_id: int):
    print(f"\n🚀 ENGAGING AUTONOMOUS LOOP FOR BATCH: {batch_id}")
    
    previous_best_score = 0.0
    
    for iteration in range(1, MAX_ITERATIONS + 1):
        print("\n" + "="*60)
        print(f"🔄 ITERATION {iteration} / {MAX_ITERATIONS}")
        print("="*60)
        
        run_core_generation(batch_id)
        run_social_simulation(batch_id)
        run_analysis(batch_id)
        
        memory_res = supabase.table("learned_policies").select("*").eq("batch_id", batch_id).order("created_at", desc=True).limit(1).execute()
        
        if not memory_res.data:
            print("❌ CRITICAL ERROR: No memory found. Halting engine.")
            break
            
        current_best_score = memory_res.data[0]['highest_reward']
        winning_trace = memory_res.data[0]['trace_id']
        
        print("\n📊 ITERATION RESULTS:")
        print(f"   🏆 Current Best Ad: Trace {winning_trace}")
        print(f"   ⭐ Current High Score: {current_best_score}")
        
        if current_best_score >= TARGET_SCORE:
            print(f"\n🎯 TARGET REACHED! (Score {current_best_score} >= {TARGET_SCORE})")
            print("The Vibe Core Engine has successfully optimized the campaign.")
            break
            
        if iteration > 1:
            improvement = current_best_score - previous_best_score
            if improvement <= PLATEAU_THRESHOLD:
                print(f"\n⛰️ PLATEAU DETECTED. Score only improved by {improvement:.2f}.")
                print("The engine has maximized this creative direction. Stopping to save resources.")
                break
                
        if iteration == MAX_ITERATIONS:
            print("\n🛑 MAX ITERATIONS REACHED.")
            print("Returning the best ad found so far.")
            break
            
        previous_best_score = current_best_score
        print("\n⏳ Preparing for next iteration... injecting winning traits...")
        time.sleep(3) 

if __name__ == "__main__":
    TEST_BATCH_ID = 1005
    start_autonomous_loop(TEST_BATCH_ID)