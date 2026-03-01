import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

@app.get("/api/feed")
async def get_campaign_feed():
    try:
        # Changed table name to input_data 
        response = supabase.table("input_data").select("*").execute()
        
        formatted_feed = []
        for row in response.data:
            formatted_feed.append({
                "user": row.get("brand_name", "VibeUser"),
                "action": f"Launched {row.get('campaign_objectives', 'Campaign')}",
                "product": row.get("product_name", "New Item")
            })
        
        return formatted_feed
    except Exception as e:
        return {"status": "Error", "message": str(e)}

@app.post("/submit-campaign")
async def handle_form(data: dict):
    try:
        # 1. Insert into input_data 
        input_payload = {
            "campaign_name": data.get("campaignName"),
            "campaign_objectives": data.get("objectives"),
            "platform_channels": data.get("platform"),
            "brand_name": data.get("brand_name"),
            "product_name": data.get("product_name"),
            "product_category": data.get("category"),
            "price": data.get("price"),
            "target_audience": data.get("ageGroup"),
            "vibe": data.get("tone"),
            "duration": data.get("duration"),
            "colors": data.get("colors")
        }
        
        input_res = supabase.table("input_data").insert(input_payload).execute()
        # Get the batch_id starting from 1000
        new_batch_id = input_res.data[0]['batch_id']

        # 2. Insert dummy AI output into generator_output 
        # In a real app, your AI model would generate these values
        gen_payload = {
            "batch_id": new_batch_id,
            "varient_no": 1,
            "prompt": f"AI prompt for {data.get('product_name')}",
            "img_url": "https://placehold.co/600x400",
            "caption_set": "Check out our new vibe!"
        }
        gen_res = supabase.table("generator_output").insert(gen_payload).execute()
        new_trace_id = gen_res.data[0]['trace_id']

        # 3. Create empty feedback/score rows [cite: 42, 43]
        supabase.table("user_feedback").insert({"trace_id": new_trace_id, "reactions": {}, "comments": []}).execute()
        supabase.table("ad_feedback_scores").insert({"trace_id": new_trace_id, "ppo_clip_score": 0.0}).execute()

        return {
            "status": "Success", 
            "batch_id": new_batch_id, 
            "trace_id": new_trace_id
        }
        
    except Exception as e:
        return {"status": "Error", "message": str(e)}