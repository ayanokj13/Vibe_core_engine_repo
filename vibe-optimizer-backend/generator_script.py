import os
import shutil
import time
import json
import urllib.request
import random
from supabase import create_client, Client
from groq import Groq
from dotenv import load_dotenv

print("⚙️ Initializing Core Engine Generator...")

# ==========================================
# 1. CONFIGURATION & SETUP
# ==========================================
load_dotenv()

# Supabase
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# Groq
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL_ID = "llama-3.1-8b-instant"

# File Paths
DRIVE_FOLDER = r"G:\My Drive\Product_images_storage"
COMFY_ROOT = r"C:\COMFYUI\ComfyUI_windows_portable\ComfyUI"
BG_LIBRARY_PATH = r"G:\My Drive\IG_FYP\A1502\Background_Library"
WORKFLOW_FILE = r"C:\Users\91876\OneDrive\Documents\FYP Report\Vibe_core_engine\workflow\API_Ad_fimg_workflow.json"
CUSTOM_OUTPUT_DIR = r"C:\Users\91876\OneDrive\Documents\FYP Report\Vibe_core_engine\Ad_output_imgs"

os.makedirs(CUSTOM_OUTPUT_DIR, exist_ok=True)

# ==========================================
# 2. COMFYUI COMPOSER CLASS (Stripped of Flask)
# ==========================================
class AdComposer:
    def __init__(self, comfy_root_dir, bg_library_path, workflow_file, custom_output_dir):
        self.server_address = "127.0.0.1:8188"
        self.workflow_file = workflow_file
        self.bg_library_path = bg_library_path
        self.custom_output_dir = custom_output_dir
        self.comfy_input_dir = os.path.join(comfy_root_dir, "input")
        self.comfy_output_dir = os.path.join(comfy_root_dir, "output")

    def _search_background(self, keyword):
        try:
            all_files = [f for f in os.listdir(self.bg_library_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            matches = [f for f in all_files if keyword.lower() in f.lower()]
            if not matches:
                return os.path.join(self.bg_library_path, random.choice(all_files)) if all_files else None
            return os.path.join(self.bg_library_path, random.choice(matches))
        except Exception as e:
            print(f"❌ BG Error: {e}")
            return None

    def compose_ad(self, product_path, title_text, subtitle_text, bg_keyword, trace_id, original_img_name):
        self._copy_to_comfy(product_path, "current_product.png")
        bg_source_path = self._search_background(bg_keyword)
        
        if bg_source_path:
            self._copy_to_comfy(bg_source_path, "current_bg.png")
        else:
            return None

        with open(self.workflow_file, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
        
        if "1" in workflow: workflow["1"]["inputs"]["image"] = "current_product.png"
        if "100" in workflow: workflow["100"]["inputs"]["image"] = "current_bg.png"
        if "950" in workflow: workflow["950"]["inputs"]["text"] = title_text
        if "951" in workflow: workflow["951"]["inputs"]["text"] = subtitle_text

        for node_id, node_data in workflow.items():
            if "inputs" in node_data and "seed" in node_data["inputs"]:
                node_data["inputs"]["seed"] = random.randint(1, 999999999999999)

        req_data = json.dumps({"prompt": workflow}).encode('utf-8')
        try:
            req = urllib.request.Request(f"http://{self.server_address}/prompt", data=req_data)
            urllib.request.urlopen(req)
        except Exception as e:
            print(f"❌ ComfyUI Connection Failed: {e}")
            return None

        generated_image_path = self._wait_for_image()
        if generated_image_path:
            new_filename = f"{trace_id}_{original_img_name}"
            destination = os.path.join(self.custom_output_dir, new_filename)
            shutil.move(generated_image_path, destination)
            return destination
        return None

    def _copy_to_comfy(self, source_path, target_filename):
        shutil.copy(source_path, os.path.join(self.comfy_input_dir, target_filename))

    def _wait_for_image(self, timeout=180):
        start_time = time.time()
        initial_files = set(f for f in os.listdir(self.comfy_output_dir) if f.startswith("Final_Ad_"))

        while (time.time() - start_time) < timeout:
            current_files = set(f for f in os.listdir(self.comfy_output_dir) if f.startswith("Final_Ad_"))
            new_files = current_files - initial_files
            if new_files:
                time.sleep(1) 
                return os.path.join(self.comfy_output_dir, list(new_files)[0])
            time.sleep(1)
        return None

# ==========================================
# 3. MASTER ORCHESTRATOR FUNCTION
# ==========================================
def run_core_generation(batch_id: int):
    print(f"\n🚀 Starting Generation Pipeline for Batch ID: {batch_id}")
    
    # 1. FETCH INPUT DATA
    res = supabase.table("input_data").select("*").eq("batch_id", batch_id).execute()
    if not res.data:
        print(f"❌ No data found for Batch ID {batch_id}")
        return
    campaign = res.data[0]
    
    # 2. LOCATE SOURCE IMAGE
    source_image_path = None
    original_img_name = None
    for file in os.listdir(DRIVE_FOLDER):
        if file.startswith(f"{batch_id}_"):
            source_image_path = os.path.join(DRIVE_FOLDER, file)
            original_img_name = file
            break
            
    if not source_image_path:
        print(f"❌ Could not find source image for Batch {batch_id} in {DRIVE_FOLDER}")
        return

    # ==========================================
    # 3. MEMORY READER (The Brain Injection)
    # ==========================================
    vibe_category = campaign['vibe'].split(",")[0].strip()
    print(f"🧠 Checking long-term memory for vibe: '{vibe_category}'...")
    
    # Query the database for the highest-scoring policy for this vibe
    policy_res = supabase.table("learned_policies").select("*").eq("vibe_category", vibe_category).order("highest_reward", desc=True).limit(1).execute()
    
    learned_context = ""
    if policy_res.data:
        best_policy = policy_res.data[0]
        learned_context = f"""
        [LEARNED MEMORY: HIGH PRIORITY]
        A previous ad targeting the '{vibe_category}' vibe achieved an exceptionally high score ({best_policy['highest_reward']}) using this specific creative style:
        - Winning Text Style: {best_policy['winning_caption']}
        - Winning Visual Metadata: {best_policy['winning_prompt']}
        
        CRITICAL INSTRUCTION: Analyze why that style succeeded. Generate 3 NEW variations that heavily exploit this proven tone, formatting, and structural strategy, while remaining relevant to the current product.
        """
        print(f"   💡 Found a winning policy! Injecting past success (Score: {best_policy['highest_reward']}) into LLM prompt.")
    else:
        learned_context = """
        [EXPLORATION MODE]
        We have no historical data for this vibe. Be highly creative. Generate 3 wildly different textual angles, tones, and visual descriptors to see what resonates best.
        """
        print("   🔍 No prior memory found. Running in Pure Exploration Mode.")

    # 4. GENERATE CAPTIONS (Groq)
    print("✍️ Generating Captions via LLM...")
    prompt = f"""Generate 3 DISTINCT social media ad variations.
    PRODUCT: {campaign['product_name']} ({campaign['brand_name']})
    OBJECTIVE: {campaign['campaign_objectives']}
    VIBE: {campaign['vibe']}
    HIGHLIGHTS: {campaign['product_highlights']}
    
    {learned_context}
    
    Return JSON format: {{"variations": [{{"headline": "...", "body": "...", "hashtags": ["..."]}}]}}"""
    
    completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You output valid JSON only."},
            {"role": "user", "content": prompt}
        ],
        model=MODEL_ID, temperature=0.7, response_format={"type": "json_object"}
    )
    captions = json.loads(completion.choices[0].message.content)["variations"]

    # 5. GENERATE IMAGES & UPDATE DATABASE
    composer = AdComposer(COMFY_ROOT, BG_LIBRARY_PATH, WORKFLOW_FILE, CUSTOM_OUTPUT_DIR)
    
    for i in range(3):
        print(f"\n🎨 Processing Variation {i+1}/3...")
        
        temp_payload = {
            "batch_id": batch_id,
            "varient_no": i + 1,
            "prompt": f"Generated for {campaign['vibe']} vibe",
            "img_url": "pending",
            "caption_set": json.dumps(captions[i])
        }
        gen_res = supabase.table("generator_output").insert(temp_payload).execute()
        trace_id = gen_res.data[0]['trace_id']
        
        final_img_path = composer.compose_ad(
            product_path=source_image_path,
            title_text=captions[i]['headline'],
            subtitle_text=campaign['brand_name'],
            bg_keyword=vibe_category, 
            trace_id=trace_id,
            original_img_name=original_img_name
        )
        
        if final_img_path:
            supabase.table("generator_output").update({"img_url": final_img_path}).eq("trace_id", trace_id).execute()
            print(f"✅ Variation {i+1} saved! Trace ID: {trace_id}")
            
            supabase.table("user_feedback").insert({"trace_id": trace_id, "total_no_of_likes": 0, "total_no_of_ctr": 0.0, "reactions": 0, "comments": "[]"}).execute()
            supabase.table("ad_feedback_scores").insert({"trace_id": trace_id, "reward_rt": 0.0, "vst": 0.0, "at": 0.0, "lv": 0.0, "ppo_clip_score": 0.0}).execute()
        else:
            print(f"❌ Failed to generate image for variation {i+1}")
    
    print("\n✅ Generation Complete. The ads are ready for simulation.")
    return True

if __name__ == "__main__":
    TARGET_BATCH_ID = 1004 
    run_core_generation(TARGET_BATCH_ID)