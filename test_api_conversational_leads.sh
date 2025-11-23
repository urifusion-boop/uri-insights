#!/bin/bash

# API Test Script for Conversational Twitter Leads
# This script tests the feature via HTTP API calls

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BOLD}${CYAN}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║   Conversational Twitter Leads - API Test Script         ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Configuration
read -p "Enter API Base URL (e.g., http://localhost:8000): " API_BASE_URL
read -p "Enter Authorization Token: " AUTH_TOKEN
read -p "Enter Test User ID: " USER_ID

# Trim whitespace
API_BASE_URL=$(echo "$API_BASE_URL" | xargs)
AUTH_TOKEN=$(echo "$AUTH_TOKEN" | xargs)
USER_ID=$(echo "$USER_ID" | xargs)

if [ -z "$API_BASE_URL" ] || [ -z "$AUTH_TOKEN" ] || [ -z "$USER_ID" ]; then
    echo -e "${RED}❌ All fields are required${NC}"
    exit 1
fi

echo -e "\n${CYAN}Configuration:${NC}"
echo "  API: $API_BASE_URL"
echo "  User ID: $USER_ID"
echo "  Token: ${AUTH_TOKEN:0:20}..."

# Function to make API call
api_call() {
    local method=$1
    local endpoint=$2
    local data=$3

    if [ -z "$data" ]; then
        curl -s -X "$method" \
            -H "Authorization: Bearer $AUTH_TOKEN" \
            -H "Content-Type: application/json" \
            "$API_BASE_URL$endpoint"
    else
        curl -s -X "$method" \
            -H "Authorization: Bearer $AUTH_TOKEN" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$API_BASE_URL$endpoint"
    fi
}

# Test 1: Check if conversational form exists
echo -e "\n${YELLOW}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}Test 1: Get Existing Conversational Form${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"

FORM_RESPONSE=$(api_call GET "/lead-tracking/lead-forms?user_id=$USER_ID&form_type=CONVERSATIONAL")
echo "$FORM_RESPONSE" | jq '.' 2>/dev/null || echo "$FORM_RESPONSE"

FORM_EXISTS=$(echo "$FORM_RESPONSE" | jq -r '.responseData[0].lead_form_id // empty' 2>/dev/null)

if [ -z "$FORM_EXISTS" ]; then
    echo -e "\n${YELLOW}No conversational form found. Creating one...${NC}"

    # Create a test form
    CREATE_PAYLOAD=$(cat <<EOF
{
    "user_id": "$USER_ID",
    "form_title": "Test Conversational Form",
    "form_type": "CONVERSATIONAL",
    "keywords": ["hiring", "software engineer"],
    "buying_signals": ["looking for", "need", "urgent"],
    "excluded_keywords": ["spam"],
    "auto_generate": true,
    "ai_response_guide": "Generate professional outreach messages"
}
EOF
)

    CREATE_RESPONSE=$(api_call POST "/lead-tracking/lead-forms/conversational" "$CREATE_PAYLOAD")
    echo -e "\n${GREEN}Create Response:${NC}"
    echo "$CREATE_RESPONSE" | jq '.' 2>/dev/null || echo "$CREATE_RESPONSE"

    FORM_ID=$(echo "$CREATE_RESPONSE" | jq -r '.responseData.lead_form_id // empty' 2>/dev/null)

    if [ -z "$FORM_ID" ]; then
        echo -e "${RED}❌ Failed to create form${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ Form created: $FORM_ID${NC}"
else
    FORM_ID=$FORM_EXISTS
    echo -e "${GREEN}✓ Form exists: $FORM_ID${NC}"
fi

# Test 2: Get current lead count
echo -e "\n${YELLOW}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}Test 2: Get Current Lead Count${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"

LEADS_RESPONSE=$(api_call GET "/leads-tracking/forms/leads?assigned_to=$USER_ID&lead_type=CONVERSATIONAL")
LEAD_COUNT_BEFORE=$(echo "$LEADS_RESPONSE" | jq -r '.responseData.data | length' 2>/dev/null || echo "0")

echo -e "${CYAN}Leads Before: $LEAD_COUNT_BEFORE${NC}"

# Test 3: Manually trigger fetch (if endpoint exists)
echo -e "\n${YELLOW}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}Test 3: Trigger Manual Fetch${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"

echo -e "${YELLOW}⏳ Triggering fetch... (this may take 10-30 seconds)${NC}"

# Note: This endpoint might not exist yet - you may need to add it
TRIGGER_RESPONSE=$(api_call POST "/lead-tracking/conversational/trigger-fetch" "{\"user_id\": \"$USER_ID\"}")

if echo "$TRIGGER_RESPONSE" | grep -q "404\|not found\|Not Found"; then
    echo -e "${YELLOW}⚠ Manual trigger endpoint not available${NC}"
    echo -e "${CYAN}The background job will run automatically every 1 minute in testing mode${NC}"
    echo -e "${CYAN}Waiting 90 seconds for next scheduled run...${NC}"

    # Show countdown
    for i in {90..1}; do
        echo -ne "\r  ${YELLOW}⏳ $i seconds remaining...${NC}"
        sleep 1
    done
    echo ""
else
    echo "$TRIGGER_RESPONSE" | jq '.' 2>/dev/null || echo "$TRIGGER_RESPONSE"
fi

# Test 4: Check if new leads were created
echo -e "\n${YELLOW}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}Test 4: Verify New Leads${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"

sleep 5  # Give it a moment to process

LEADS_RESPONSE_AFTER=$(api_call GET "/leads-tracking/forms/leads?assigned_to=$USER_ID&lead_type=CONVERSATIONAL")
LEAD_COUNT_AFTER=$(echo "$LEADS_RESPONSE_AFTER" | jq -r '.responseData.data | length' 2>/dev/null || echo "0")

echo -e "${CYAN}Leads Before: $LEAD_COUNT_BEFORE${NC}"
echo -e "${CYAN}Leads After:  $LEAD_COUNT_AFTER${NC}"

NEW_LEADS=$((LEAD_COUNT_AFTER - LEAD_COUNT_BEFORE))

if [ $NEW_LEADS -gt 0 ]; then
    echo -e "${GREEN}✓ Success! $NEW_LEADS new leads created${NC}"

    # Show sample of new leads
    echo -e "\n${CYAN}Sample of new leads:${NC}"
    echo "$LEADS_RESPONSE_AFTER" | jq -r '.responseData.data[0:3] | .[] | "  • @\(.username): \(.mention[0:100])"' 2>/dev/null
else
    echo -e "${YELLOW}⚠ No new leads yet. Check:${NC}"
    echo "  1. Form has auto_generate=true"
    echo "  2. Keywords are relevant"
    echo "  3. APIFY_API_TOKEN is configured"
    echo "  4. Background scheduler is running"
fi

# Test 5: Check form metadata
echo -e "\n${YELLOW}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}Test 5: Check Form Fetch Metadata${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"

FORM_DETAIL=$(api_call GET "/lead-tracking/lead-forms/$FORM_ID")
FETCH_SETTINGS=$(echo "$FORM_DETAIL" | jq -r '.responseData.settings.conversational_twitter_fetch // empty' 2>/dev/null)

if [ ! -z "$FETCH_SETTINGS" ]; then
    echo -e "${GREEN}✓ Fetch metadata found:${NC}"
    echo "$FORM_DETAIL" | jq '.responseData.settings.conversational_twitter_fetch' 2>/dev/null
else
    echo -e "${YELLOW}⚠ No fetch metadata yet (form hasn't been processed)${NC}"
fi

# Summary
echo -e "\n${BOLD}${GREEN}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                  Test Complete!                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${CYAN}Next Steps:${NC}"
echo "  1. Check the frontend dashboard at /leads-tracking/forms/leads?type=conversational"
echo "  2. Test different subscription plans by changing user plan"
echo "  3. Monitor logs for scheduled runs (every 1 minute in testing mode)"
echo "  4. Verify interval enforcement (no duplicate fetches)"

echo -e "\n${YELLOW}Testing Mode Configuration:${NC}"
echo "  • Scheduler runs: Every 1 minute (instead of 1 hour)"
echo "  • LEAD_ONLY/BUSINESS: 5 tweets every 2 minutes"
echo "  • PROFESSIONAL: 5 tweets every 4 minutes"
echo "  • STANDARD: 5 tweets every 6 minutes"
