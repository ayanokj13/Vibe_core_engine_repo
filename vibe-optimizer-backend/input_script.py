import os
import shutil
import re
from supabase import create_client, Client
from dotenv import load_dotenv

print("Script started! Loading environment variables...")

# Load environment variables
load_dotenv()

# Initialize Supabase client
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")

if not url or not key:
    print("\n[CRITICAL ERROR] SUPABASE_URL or SUPABASE_KEY is missing. Check your .env file!")
    exit(1)

supabase: Client = create_client(url, key)

def sanitize_filename(name: str) -> str:
    """Removes spaces and special characters to ensure a safe file path."""
    return re.sub(r'[^a-zA-Z0-9_]', '', name.replace(' ', '_'))

def generate_mock_input(source_image_name: str):
    """
    Creates a mock campaign payload, inserts it to DB, and stores the product image.
    """
    
    # 1. Verify the source image exists locally before making any database calls
    if not os.path.exists(source_image_name):
        print(f"\n[ERROR] Could not find the input image '{source_image_name}' in this folder.")
        print("Please place a test image in the same directory and update the filename at the bottom of the script.")
        return None

    # The Google Drive desktop app path you provided
    drive_folder_path = r"G:\My Drive\Product_images_storage"
    
    # Verify the Drive folder is accessible
    if not os.path.exists(drive_folder_path):
        print(f"\n[ERROR] Google Drive folder not found at: {drive_folder_path}")
        print("Make sure your Google Drive desktop app is running and synced.")
        return None

    mock_campaign_data = {
        "campaign_name": "Summer Glow Serum Launch 2026",
        "campaign_objectives": "Brand Awareness", 
        "platform_channels": "Instagram", 
        "brand_name": "AuraGlow",
        "product_name": "Vitamin C Radiance Face Serum",
        "product_category": "Cosmetics - Skincare",
        "product_highlights": "Deep hydration, fades dark spots, instantly brightens skin tone, lightweight non-sticky finish",
        "ingredients": "15% L-Ascorbic Acid (Vitamin C), Hyaluronic Acid, Ferulic Acid, Vitamin E",
        "price": 45.99,
        "target_audience": "25-34", 
        "vibe": "Clean, luxurious, radiant, natural",
        "duration": "15 seconds",
        "channel_used": "Instagram", 
        "visual_elements": "Macro shots of glowing skin, golden hour sunlight, slow-motion dropping of serum from pipette, minimalist aesthetic",
        "colors": "#FFD700, #FFFFFF, #F5F5DC" 
    }
    
    try:
        print(f"Injecting test campaign: {mock_campaign_data['campaign_name']}...")
        
        # 2. Insert into input_data
        response = supabase.table("input_data").insert(mock_campaign_data).execute()
        
        # Extract the master key
        new_batch_id = response.data[0]['batch_id']
        
        # 3. Handle Image Renaming and Storage
        product_name = mock_campaign_data["product_name"]
        safe_product_name = sanitize_filename(product_name)
        
        # Extract the original file extension (e.g., .jpg, .png)
        _, ext = os.path.splitext(source_image_name)
        
        # Construct the new filename: batchid_productname.ext
        new_image_name = f"{new_batch_id}_{safe_product_name}{ext}"
        
        # Construct the final destination path in Google Drive
        destination_path = os.path.join(drive_folder_path, new_image_name)
        
        # Copy the image from the local folder to the Drive folder
        shutil.copy2(source_image_name, destination_path)
        
        print("\n=== SUCCESS ===")
        print(f"Database Row Created Successfully.")
        print(f"MASTER BATCH ID: {new_batch_id}")
        print(f"Image securely copied to Drive as: {new_image_name}")
        print("===============\n")
        
        return new_batch_id
        
    except Exception as e:
        print(f"\n[ERROR] Execution failed: {str(e)}")
        return None

if __name__ == "__main__":
    # Define the name of your test image located in the same folder as this script
    local_test_image = "Neutrogena.png" 
    
    # Execute the mock generation
    batch_id = generate_mock_input(local_test_image)