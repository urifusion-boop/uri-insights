-- app/agents/social_media_manager/migrations/001_social_media_manager_tables.sql
-- URI Social Media Manager Agent Database Migration
-- Version: 1.0.0
-- Description: Core tables for AI-powered social media management system

-- Enable foreign key checks
SET FOREIGN_KEY_CHECKS = 1;

-- 1. Content Generation Requests Table
CREATE TABLE IF NOT EXISTS content_requests (
    id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    seed_content TEXT NOT NULL,
    seed_type ENUM('text', 'url', 'image', 'mention_response', 'trend_analysis') NOT NULL DEFAULT 'text',
    requested_platforms JSON NOT NULL COMMENT 'Array of platforms: ["linkedin", "twitter", "facebook", "instagram"]',
    status ENUM('generating', 'ready', 'approved', 'published', 'failed') DEFAULT 'generating',
    metadata JSON DEFAULT NULL COMMENT 'Store additional context, AI parameters, etc.',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Foreign Keys (assuming users table exists)
    -- FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Indexes for performance
    INDEX idx_user_status (user_id, status),
    INDEX idx_created_at (created_at),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Generated Content Drafts Table
CREATE TABLE IF NOT EXISTS content_drafts (
    id VARCHAR(50) PRIMARY KEY,
    request_id VARCHAR(50) NOT NULL,
    platform ENUM('linkedin', 'twitter', 'facebook', 'instagram', 'tiktok') NOT NULL,
    content TEXT NOT NULL,
    original_content TEXT NOT NULL COMMENT 'Store original AI-generated content before human edits',
    media_urls JSON DEFAULT NULL COMMENT 'Array of media file URLs',
    hashtags JSON DEFAULT NULL COMMENT 'Array of hashtags',
    scheduled_date DATETIME DEFAULT NULL,
    published_date DATETIME DEFAULT NULL,
    status ENUM('draft', 'approved', 'scheduled', 'published', 'failed') DEFAULT 'draft',
    
    -- AI and Human Edit Tracking
    ai_metadata JSON DEFAULT NULL COMMENT 'AI model info, prompt version, generation parameters',
    human_edits JSON DEFAULT NULL COMMENT 'Track what users changed from original',
    edit_count INT DEFAULT 0 COMMENT 'Number of times human edited this draft',
    
    -- Publishing Results
    platform_post_id VARCHAR(255) DEFAULT NULL COMMENT 'ID from social platform after publishing',
    publish_response JSON DEFAULT NULL COMMENT 'Full response from publishing API',
    error_message TEXT DEFAULT NULL COMMENT 'Error details if publishing failed',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Foreign Keys
    FOREIGN KEY (request_id) REFERENCES content_requests(id) ON DELETE CASCADE,
    
    -- Indexes
    INDEX idx_request_platform (request_id, platform),
    INDEX idx_platform_status (platform, status),
    INDEX idx_scheduled_date (scheduled_date),
    INDEX idx_status_created (status, created_at),
    UNIQUE KEY unique_request_platform (request_id, platform)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Social Platform Connections Table
CREATE TABLE IF NOT EXISTS social_connections (
    id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    platform ENUM('linkedin', 'twitter', 'facebook', 'instagram', 'tiktok') NOT NULL,
    
    -- Ayrshare Integration
    ayrshare_profile_key VARCHAR(255) NOT NULL COMMENT 'Ayrshare profile identifier',
    
    -- Platform Account Info
    platform_account_id VARCHAR(255) NOT NULL COMMENT 'Social platform account ID',
    platform_username VARCHAR(255) NOT NULL COMMENT 'Social platform username/handle',
    platform_display_name VARCHAR(255) DEFAULT NULL COMMENT 'Display name on platform',
    platform_avatar_url TEXT DEFAULT NULL COMMENT 'Profile picture URL',
    
    -- Token Management (Encrypted)
    access_token_encrypted TEXT NOT NULL COMMENT 'Encrypted OAuth access token',
    refresh_token_encrypted TEXT DEFAULT NULL COMMENT 'Encrypted refresh token if available',
    token_expires_at DATETIME DEFAULT NULL,
    token_scope TEXT DEFAULT NULL COMMENT 'OAuth scopes granted',
    
    -- Connection Status
    connection_status ENUM('active', 'expired', 'revoked', 'error', 'pending') DEFAULT 'active',
    last_verified_at DATETIME DEFAULT NULL COMMENT 'Last time we verified token works',
    last_published_at DATETIME DEFAULT NULL COMMENT 'Last successful post',
    
    -- Publishing Stats
    total_posts_published INT DEFAULT 0,
    total_publish_errors INT DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Foreign Keys
    -- FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Indexes
    INDEX idx_user_platform (user_id, platform),
    INDEX idx_connection_status (connection_status),
    INDEX idx_ayrshare_profile (ayrshare_profile_key),
    UNIQUE KEY unique_user_platform (user_id, platform)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Content Analytics Table
CREATE TABLE IF NOT EXISTS content_analytics (
    id VARCHAR(50) PRIMARY KEY,
    draft_id VARCHAR(50) NOT NULL,
    platform_post_id VARCHAR(255) DEFAULT NULL COMMENT 'ID from social platform',
    
    -- Engagement Metrics
    views INT DEFAULT 0,
    impressions INT DEFAULT 0,
    likes INT DEFAULT 0,
    shares INT DEFAULT 0,
    comments INT DEFAULT 0,
    clicks INT DEFAULT 0,
    saves INT DEFAULT 0,
    
    -- Calculated Metrics
    engagement_rate DECIMAL(5,4) DEFAULT 0 COMMENT 'Total engagement / impressions',
    click_through_rate DECIMAL(5,4) DEFAULT 0 COMMENT 'Clicks / impressions',
    
    -- Time-based Metrics
    peak_engagement_hour INT DEFAULT NULL COMMENT 'Hour of day with most engagement (0-23)',
    total_engagement_time_minutes INT DEFAULT 0,
    
    -- Raw Data from Platform
    raw_analytics_data JSON DEFAULT NULL COMMENT 'Full analytics response from platform',
    
    -- Tracking
    last_updated DATETIME DEFAULT NULL,
    data_freshness ENUM('real_time', 'hourly', 'daily', 'stale') DEFAULT 'real_time',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Foreign Keys
    FOREIGN KEY (draft_id) REFERENCES content_drafts(id) ON DELETE CASCADE,
    
    -- Indexes
    INDEX idx_draft_id (draft_id),
    INDEX idx_platform_post (platform_post_id),
    INDEX idx_engagement_rate (engagement_rate),
    INDEX idx_last_updated (last_updated)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Content Templates Table (for future use)
CREATE TABLE IF NOT EXISTS content_templates (
    id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT DEFAULT NULL,
    template_content TEXT NOT NULL COMMENT 'Template with variables like {{company_name}}',
    platforms JSON NOT NULL COMMENT 'Platforms this template works for',
    variables JSON DEFAULT NULL COMMENT 'List of variables user needs to fill',
    usage_count INT DEFAULT 0,
    is_public BOOLEAN DEFAULT FALSE COMMENT 'Can other users use this template',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    
    INDEX idx_user_public (user_id, is_public),
    INDEX idx_public_templates (is_public, usage_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create views for common queries
CREATE OR REPLACE VIEW active_social_connections AS
SELECT 
    sc.user_id,
    sc.platform,
    sc.platform_username,
    sc.connection_status,
    sc.last_published_at,
    sc.total_posts_published
FROM social_connections sc
WHERE sc.connection_status = 'active';

CREATE OR REPLACE VIEW content_performance_summary AS
SELECT 
    cd.id as draft_id,
    cd.request_id,
    cd.platform,
    cd.status,
    cd.published_date,
    COALESCE(ca.engagement_rate, 0) as engagement_rate,
    COALESCE(ca.total_engagement_time_minutes, 0) as total_engagement_time_minutes,
    COALESCE(ca.views, 0) as views,
    COALESCE(ca.likes, 0) as likes,
    COALESCE(ca.shares, 0) as shares,
    COALESCE(ca.comments, 0) as comments
FROM content_drafts cd
LEFT JOIN content_analytics ca ON cd.id = ca.draft_id
WHERE cd.status = 'published';

-- Insert sample data for testing (only if no content_requests exist)
INSERT INTO content_requests (id, user_id, seed_content, seed_type, requested_platforms, status)
SELECT 
    'sample_req_001',
    '6984ba1ac9172673484fdc5b',
    'Our new N10M SME loan product is helping Lagos businesses scale faster than ever. What industries should we target next?',
    'text',
    JSON_ARRAY('linkedin', 'twitter'),
    'ready'
WHERE NOT EXISTS (SELECT 1 FROM content_requests LIMIT 1);

-- Sample draft
INSERT INTO content_drafts (id, request_id, platform, content, original_content, status, hashtags, ai_metadata)
SELECT 
    'sample_draft_001',
    'sample_req_001',
    'linkedin',
    'Our new ₦10M SME loan product is transforming Lagos businesses.\n\nIn just 6 months, we''ve helped 200+ SMEs scale operations:\n• Manufacturing companies expanding production\n• Tech startups hiring top talent\n• Retail businesses opening new locations\n\nThe ripple effect? 1,500+ new jobs created.\n\nWhich industries should we focus on next? Drop your thoughts below 👇',
    'Our new ₦10M SME loan product is transforming Lagos businesses.\n\nIn just 6 months, we''ve helped 200+ SMEs scale operations:\n• Manufacturing companies expanding production\n• Tech startups hiring top talent\n• Retail businesses opening new locations\n\nThe ripple effect? 1,500+ new jobs created.\n\nWhich industries should we focus on next? Drop your thoughts below 👇',
    'draft',
    JSON_ARRAY('SMEFinancing', 'LagosBusinessGrowth', 'EntrepreneurshipNigeria'),
    JSON_OBJECT('model_used', 'gpt-4o', 'prompt_version', '1.0', 'temperature', 0.7)
WHERE NOT EXISTS (SELECT 1 FROM content_drafts WHERE id = 'sample_draft_001');

-- Show completion message
SELECT 'Social Media Manager Agent tables created successfully!' as status;