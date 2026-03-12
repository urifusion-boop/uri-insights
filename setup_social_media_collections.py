# setup_social_media_collections.py
# Place this file in your uri-insights root directory and run once

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

async def setup_social_media_collections():
    """
    Setup MongoDB collections for Social Media Manager Agent
    Uses your existing MongoDB connection from .env
    """
    
    # Use your existing MongoDB connection
    mongodb_uri = os.getenv("MONGODB_URI", "mongodb://urifusion:UriTest2024!@4.221.74.63:27018/Uri_Insight?authSource=admin")
    
    print("🔗 Connecting to MongoDB...")
    client = AsyncIOMotorClient(mongodb_uri)
    db = client["Uri_Insight"]
    
    try:
        # Test connection
        await db.command("ping")
        print("✅ Connected to MongoDB successfully!")
        
        # 1. Setup content_requests collection
        print("\n📋 Setting up content_requests collection...")
        content_requests = db["content_requests"]
        
        # Create indexes
        await content_requests.create_index([("user_id", 1), ("status", 1)])
        await content_requests.create_index([("created_at", 1)])
        await content_requests.create_index([("id", 1)], unique=True)
        print("✅ content_requests indexes created")
        
        # 2. Setup content_drafts collection  
        print("\n📝 Setting up content_drafts collection...")
        content_drafts = db["content_drafts"]
        
        # Create indexes
        await content_drafts.create_index([("request_id", 1), ("platform", 1)], unique=True)
        await content_drafts.create_index([("platform", 1), ("status", 1)])
        await content_drafts.create_index([("scheduled_date", 1)])
        await content_drafts.create_index([("status", 1), ("created_at", 1)])
        await content_drafts.create_index([("id", 1)], unique=True)
        print("✅ content_drafts indexes created")
        
        # 3. Setup social_connections collection
        print("\n🔗 Setting up social_connections collection...")
        social_connections = db["social_connections"]
        
        # Create indexes
        await social_connections.create_index([("user_id", 1), ("platform", 1), ("page_id", 1)], unique=True)
        await social_connections.create_index([("connection_status", 1)])
        await social_connections.create_index([("ayrshare_profile_key", 1)])
        await social_connections.create_index([("id", 1)], unique=True)
        print("✅ social_connections indexes created")
        
        # 4. Setup content_analytics collection
        print("\n📊 Setting up content_analytics collection...")
        content_analytics = db["content_analytics"]
        
        # Create indexes
        await content_analytics.create_index([("draft_id", 1)], unique=True)
        await content_analytics.create_index([("platform_post_id", 1)])
        await content_analytics.create_index([("engagement_rate", 1)])
        await content_analytics.create_index([("last_updated", 1)])
        print("✅ content_analytics indexes created")
        
        # 5. Setup content_templates collection
        print("\n📄 Setting up content_templates collection...")
        content_templates = db["content_templates"]
        
        # Create indexes
        await content_templates.create_index([("user_id", 1), ("is_public", 1)])
        await content_templates.create_index([("is_public", 1), ("usage_count", 1)])
        await content_templates.create_index([("id", 1)], unique=True)
        print("✅ content_templates indexes created")
        
        # 6. Insert sample data for testing
        print("\n🧪 Inserting sample data...")
        
        # Check if sample data already exists
        existing_request = await content_requests.find_one({"id": "sample_req_001"})
        
        if not existing_request:
            # Insert sample request
            sample_request = {
                "id": "sample_req_001",
                "user_id": "6984ba1ac9172673484fdc5b",  # Your existing test user
                "seed_content": "Our new N10M SME loan product is helping Lagos businesses scale faster than ever. What industries should we target next?",
                "seed_type": "text",
                "requested_platforms": ["linkedin", "twitter"],
                "status": "ready",
                "metadata": {
                    "created_via": "uri_social_media_manager",
                    "platform_count": 2
                },
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            await content_requests.insert_one(sample_request)
            
            # Insert sample draft
            sample_draft = {
                "id": "sample_draft_001", 
                "request_id": "sample_req_001",
                "platform": "linkedin",
                "content": "Our new ₦10M SME loan product is transforming Lagos businesses.\n\nIn just 6 months, we've helped 200+ SMEs scale operations:\n• Manufacturing companies expanding production\n• Tech startups hiring top talent\n• Retail businesses opening new locations\n\nThe ripple effect? 1,500+ new jobs created.\n\nWhich industries should we focus on next? Drop your thoughts below 👇",
                "original_content": "Our new ₦10M SME loan product is transforming Lagos businesses.\n\nIn just 6 months, we've helped 200+ SMEs scale operations:\n• Manufacturing companies expanding production\n• Tech startups hiring top talent\n• Retail businesses opening new locations\n\nThe ripple effect? 1,500+ new jobs created.\n\nWhich industries should we focus on next? Drop your thoughts below 👇",
                "status": "draft",
                "hashtags": ["SMEFinancing", "LagosBusinessGrowth", "EntrepreneurshipNigeria"],
                "ai_metadata": {
                    "model_used": "gpt-4o",
                    "prompt_version": "1.0",
                    "temperature": 0.7,
                    "platform": "linkedin",
                    "nigerian_context": True
                },
                "edit_count": 0,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            await content_drafts.insert_one(sample_draft)
            print("✅ Sample data inserted successfully")
        else:
            print("ℹ️ Sample data already exists, skipping insertion")
        
        # 7. Verify collections exist
        print("\n🔍 Verifying collections...")
        collections = await db.list_collection_names()
        social_media_collections = [
            "content_requests", 
            "content_drafts", 
            "social_connections", 
            "content_analytics", 
            "content_templates"
        ]
        
        for collection in social_media_collections:
            if collection in collections:
                count = await db[collection].count_documents({})
                print(f"✅ {collection}: {count} documents")
            else:
                print(f"❌ {collection}: NOT FOUND")
        
        print("\n🎉 Social Media Manager Agent MongoDB setup completed successfully!")
        print("\nNext steps:")
        print("1. Copy agent files to app/agents/social_media_manager/")
        print("2. Add AYRSHARE_API_KEY to your .env file") 
        print("3. Test content generation!")
        
    except Exception as e:
        print(f"❌ Error setting up collections: {str(e)}")
        return False
    
    finally:
        client.close()
    
    return True

if __name__ == "__main__":
    # Load environment variables (if you have python-dotenv installed)
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("Note: python-dotenv not installed, make sure your .env variables are set")
    
    # Run the setup
    asyncio.run(setup_social_media_collections())