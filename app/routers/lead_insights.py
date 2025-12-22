from fastapi import APIRouter, BackgroundTasks, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import enforce_feature_limit, get_db_dependency
from app.domain.enums.date_enum import DateFilterEnum
from app.domain.enums.filetype_enum import FileTypeEnum
from app.domain.enums.lead_enum import (
    LeadIndustryTypeEnum,
    LeadStatusEnum,
    LeadInterestLevelEnum,
    LeadSourceEnum,
)
from app.domain.schemas.leadbusinessinfo_schema import (
    LeadBusinessInfoCreate,
    LeadBusinessInfoUpdate,
)
from app.repository.LeadBusinessInfoRepository import LeadBusinessInfoRepository
from app.repository.LeadRepository import LeadRepository
from app.domain.schemas.lead_schema import (
    LeadCreate,
    LeadUpdate,
)
from app.domain.responses.uri_response import UriResponse
from typing import Optional, List, Union
from fastapi.encoders import jsonable_encoder
from app.services.ApolloService import ApolloService
from app.services.LeadBusinessInfoService import LeadBusinessInfoService
from app.services.LeadService import LeadService
from app.domain.requests.lead_requests import (
    GetLeadsByFiltersRequest,
    LeadAnalyticsRequest,
    LeadEnrichmentRequest,
)
from app.domain.enums.leadform_enum import LeadFormTypeEnum
from app.repository.LeadFormRepository import LeadFormRepository


router = APIRouter()


# Create a new lead
@router.post("/create")
async def create_lead(
    lead: LeadCreate, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = LeadRepository.create_lead(db, lead)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Create multiple leads with optional intent analysis
@router.post("/multipleCreate")
async def create_leads(
    leads: List[LeadCreate],
    lead_form_id: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    # If lead_form_id provided, run intent analysis to filter leads
    if lead_form_id:
        lead_form_response = await LeadFormRepository.get_by_id(db, lead_form_id)
        lead_form = lead_form_response.get("responseData", {})

        if lead_form:
            # Run intent analysis and filter leads
            original_count = len(leads)
            leads = await LeadService.analyze_and_filter_leads(
                leads=leads,
                lead_form=lead_form,
                enable_intent_analysis=True
            )
            filtered_count = len(leads)
            print(f"Intent analysis: {original_count} leads -> {filtered_count} qualified")

            if not leads:
                return UriResponse.custom_response(
                    f"No leads passed intent analysis thresholds (0 of {original_count} qualified)",
                    200,
                    True
                )

    data = await LeadRepository.multiple_create_leads(db, leads)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Get a lead by ID
@router.get("/getById")
async def get_lead(lead_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)):
    data = await LeadRepository.get_lead_by_id(db, lead_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Filter leads by assigned_to, status, interest level, source with pagination
@router.get("/getByFilters")
async def filter_leads(
    date_filter: Optional[DateFilterEnum] = None,
    filters: GetLeadsByFiltersRequest = Depends(),
    skip: int = 0,
    limit: int = 10,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await LeadRepository.get_leads_by_filters(
        db=db,
        filters=filters,
        date_filter=date_filter,
        skip=skip,
        limit=limit,
    )
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Update a lead
@router.post("/update")
async def update_lead(
    lead_id: str,
    updates: LeadUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await LeadRepository.update_lead(db, lead_id, updates)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/updateMany")
async def update_many_leads(
    lead_ids: List[str],
    updates: LeadUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await LeadRepository.update_many_leads(db, lead_ids, updates)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Update lead status
@router.post("/updateStatus")
async def update_lead_status(
    lead_id: str, status: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await LeadRepository.update_lead_status(db, lead_id, status)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Star a lead
@router.post("/star")
async def star_lead(
    lead_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await LeadRepository.star_lead(db, lead_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Unstar a lead
@router.post("/unstar")
async def unstar_lead(
    lead_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await LeadRepository.unstar_lead(db, lead_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.put("/emailed/update")
async def update_lead_emailed_status(
    lead_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    status: bool = True,
):
    data = await LeadRepository.update_emailed(db, lead_id, status)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.put("/called/update")
async def update_lead_called_status(
    lead_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    status: bool = True,
):
    data = await LeadRepository.update_called(db, lead_id, status)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Delete a lead
@router.delete("/delete")
async def delete_lead(
    lead_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await LeadService.delete_lead(db, lead_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.delete("/delete-many")
async def delete_many_leads(
    lead_ids: List[str] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await LeadRepository.delete_many_leads(db, lead_ids)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Search leads by text query
@router.get("/search")
async def search_leads(
    query: str,
    skip: int = 0,
    limit: int = 10,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await LeadRepository.search_leads(db, query, skip, limit)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/analytics", response_model=dict)
async def get_lead_analytics(
    request: LeadAnalyticsRequest = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Get analytics data for leads based on filtering options.
    """
    data = await LeadRepository.fetch_lead_analytics(db, request)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/business-info/create")
async def create_lead_business_info(
    lead_business_info: LeadBusinessInfoCreate,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await LeadBusinessInfoService.create_lead_business_info(
        db=db, background_tasks=background_tasks, lead_business_info=lead_business_info
    )
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/business-info/getById")
async def get_lead_business_info_by_id(
    lead_business_info_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await LeadBusinessInfoRepository.get_lead_business_info_by_id(
        db, lead_business_info_id
    )
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/business-info/getByFilters")
async def get_lead_business_info_by_filter(
    user_id: str,
    business_name: Optional[str] = Query(None),
    business_website: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 10,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await LeadBusinessInfoRepository.get_lead_business_info_by_filters(
        db, user_id, business_name, business_website, skip, limit
    )
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/business-info/update")
async def update_lead_business_info(
    lead_business_info_id: str,
    updates: LeadBusinessInfoUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await LeadBusinessInfoService.update_leads_business_info(
        db=db,
        lead_business_info_id=lead_business_info_id,
        updates=updates,
        background_tasks=background_tasks,
    )
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.delete("/business-info/delete")
async def delete_lead_business_info(
    lead_business_info_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await LeadBusinessInfoRepository.delete_leads_business_info(
        db, lead_business_info_id
    )
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/enrich")
async def enrich_lead(
    request: LeadEnrichmentRequest,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    _=Depends(enforce_feature_limit),
):
    result = await ApolloService.handle_enrichment_request(
        lead_ids=request.lead_ids,
        db=db,
        reveal_email=request.reveal_email,
        reveal_phone=request.reveal_phone,
        webhook_url=request.webhook_url,
    )
    return UriResponse.get_status_response(response=jsonable_encoder(result))


@router.post("/regenerate-lead-follow-up-message")
async def regenerate_lead_follow_up_message(
    lead_id: str,
    user_prompt: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await LeadService.regenerate_lead_follow_up_message(lead_id, user_prompt, db)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/export-lead")
async def export_lead_report(
    file_type: FileTypeEnum,
    assigned_to: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    date_filter: Optional[DateFilterEnum] = None,
    filters: GetLeadsByFiltersRequest = Depends(),
    skip: int = 0,
    limit: int = 10,
):
    filters.assigned_to = assigned_to
    await LeadService.export_leads_data(
        file_type=file_type,
        db=db,
        filters=filters,
        date_filter=date_filter,
        skip=skip,
        limit=limit,
    )
    return UriResponse.get_single_data_response(
        "Lead report", {"text": "File is being generated"}
    )


@router.delete("/delete-my-leads")
async def delete_my_leads(
    user_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await LeadRepository.delete_all_leads_for_user(db, user_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/trigger-leads-gen")
async def trigger_conversational_leads_gen(
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    background_tasks.add_task(
        LeadService.generate_conversational_leads_background_job, db
    )

    return UriResponse.custom_response("Leads gen triggered successfully.", 202, True)


# Generate job keywords from business context (PRD Section 5)
@router.post("/generate-job-keywords")
async def generate_job_keywords(
    user_id: str,
    context: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """
    Generate job role keywords for job board searching
    PRD: "The AI uses the prompt and user's onboarding information to pre-fill keyword logic"
    
    Args:
        user_id: User ID to fetch onboarding data if context not provided
        context: Optional business description (if not provided, fetches from LeadBusinessInfo)
        
    Returns:
        {
            "job_keywords": ["DevOps Engineer", "Cloud Engineer", ...],
            "solution_context": "business description used",
            "source": "provided" | "onboarding_data"
        }
    """
    from app.services.JobKeywordGenerationService import JobKeywordGenerationService
    
    try:
        business_context = context
        source = "provided"
        
        # If no context provided, fetch from user's onboarding data
        if not business_context or business_context.strip() == "":
            print(f"📥 No context provided, fetching onboarding data for user: {user_id}")
            
            # Fetch user's business info from LeadBusinessInfo
            business_info_response = await LeadBusinessInfoRepository.get_lead_business_info_by_filters(
                db, user_id=user_id, skip=0, limit=1
            )
            
            business_info_list = business_info_response.get("responseData", [])
            if business_info_list and len(business_info_list) > 0:
                business_context = business_info_list[0].get("business_summary")
                source = "onboarding_data"
                print(f"✅ Found onboarding data: {business_context[:100]}...")
            else:
                return UriResponse.custom_response(
                    "No business context provided and no onboarding data found. Please provide a business description.",
                    400,
                    False
                )
        
        print(f"🤖 Generating job keywords from context (source: {source})")
        
        # Generate job keywords using AI
        result = await JobKeywordGenerationService.generate_job_keywords(business_context)
        
        # Validate and clean keywords
        valid_keywords = JobKeywordGenerationService.validate_job_keywords(result.job_keywords)
        
        response_data = {
            "job_keywords": valid_keywords,
            "solution_context": business_context,
            "source": source,
            "reasoning": result.reasoning
        }
        
        print(f"✅ Generated {len(valid_keywords)} job keywords: {', '.join(valid_keywords)}")
        
        return UriResponse.custom_response(
            "Job keywords generated successfully",
            200,
            True,
            response_data
        )
        
    except Exception as e:
        print(f"❌ Error generating job keywords: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return UriResponse.custom_response(
            f"Error generating job keywords: {str(e)}",
            500,
            False
        )



@router.post("/find-decision-makers")
async def find_decision_makers(
    lead_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """
    Find decision-makers for a job board signal
    PRD Section 8: Decision-Maker Connection Feature
    """
    from app.repository.LeadRepository import LeadRepository
    from app.services.DecisionMakerMappingService import DecisionMakerMappingService
    from app.core.helpers.apollo_helper import ApolloHelper
    from app.services.uri_microservices.UriBackendService import UriBackendService
    
    lead_response = await LeadRepository.get_lead_by_id(db, lead_id)
    
    if lead_response["responseCode"] != 200:
        return UriResponse.custom_response("Lead not found", 404, False)
    
    lead = lead_response["responseData"]
    
    # PRD Section 16: Eligibility checks
    hiring_company = lead.get("hiring_company")
    company_confidence = lead.get("company_confidence", 0.0)
    problem_solution_match = lead.get("problem_solution_match", 0.0)
    job_title = lead.get("job_title_field")
    
    if not hiring_company:
        return UriResponse.custom_response(
            "Company name is missing",
            400,
            False,
            {"reason": "missing_company_name"}
        )
    
    if company_confidence < 0.5:
        return UriResponse.custom_response(
            "Company identity could not be verified",
            400,
            False,
            {"reason": "low_company_confidence"}
        )
    
    if problem_solution_match < 0.3:
        return UriResponse.custom_response(
            "Problem-solution match too low",
            400,
            False
        )
    
    # Map job title to decision-maker titles
    decision_maker_titles = await DecisionMakerMappingService.map_job_to_decision_makers(job_title)
    
    if not decision_maker_titles:
        return UriResponse.custom_response("No decision-makers found", 404, False)
    
    # Search Apollo for decision-makers at this company
    apollo_params = {
        "person_titles": decision_maker_titles,
        "q_organization_name": hiring_company,
        "page": 1,
        "per_page": 3
    }
    
    try:
        apollo_results = await UriBackendService.search_apollo_persons(apollo_params)
        
        if not apollo_results or apollo_results.get("responseCode") != 200:
            return UriResponse.custom_response("No contacts found", 404, False)
        
        contacts = apollo_results.get("responseData", {}).get("people", [])
        
        # Filter out recruiters/HR
        excluded = ["recruiter", "recruiting", "talent acquisition", "hr ", "human resources"]
        filtered = [c for c in contacts if not any(k in c.get("title", "").lower() for k in excluded)]
        
        return UriResponse.custom_response(
            "Decision-makers found",
            200,
            True,
            {
                "decision_makers": filtered[:3],
                "searched_titles": decision_maker_titles,
                "company": hiring_company
            }
        )
    except Exception as e:
        return UriResponse.custom_response(f"Error: {str(e)}", 500, False)

